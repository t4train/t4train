#!/usr/bin/env python3
# ============================================================================
"""
The mobile BLE handler receives sensor data from iOS devices via bluetooth LE 
in the format sent from the `Mobile Handler` iOS app available
on the T4Train Github Repository. 

iOS devices running the Mobile data handler simply set the communication mode 
to BLE and activate sensors like accelerometer and gyroscope. The iOS app 
determines the rate at which sensor data is sent (a maximum of 100 hz for 
each sensor). Channel data (e.g. x, y, and z for accelerometer) is 
concatenated in each buffered UDP packet to be read by this handler. When 
`FRAME_LENGTH` many samples are sent from each sensor, a frame of data is
written to a tmpframe.npy file to be previewed by the T4Train user interface. 
When the user commands this file to begin collecting training data 
(by pressing space when the UI is running), `INSTANCES`-many frames are 
received and written to a training_data_{training label selected in UI}.npy 
file that will be trained on when the user enters the `t` for train command.

Note: the update frequency and number of active channels / sensors on the 
mobile app should not change during the lifetime of a T4Train session.

Setup: in config.ini, set the proper `DS_FILE_NUM` index that corresponds 
to this file, based on the filenames listed in `DS_FILENAMES`. Check the 
IP of the device that will run this script, and enter it into the iOS mobile
handler app. In the app, activate sensors you're interested in training on, 
and check the UI for graphed signal data refreshing at the rate of fresh 
data frames.
"""
# ============================================================================

import queue
import uuid
from datetime import timedelta
from scipy import signal
from timeloop import Timeloop
import glob
import numpy as np
import os
import serial
import signal
import sys
import time
import utils
import configparser

import Adafruit_BluefruitLE
from Adafruit_BluefruitLE.services import UART
from Adafruit_BluefruitLE.services.servicebase import *

#================================================================
# write PID to file
pidnum = os.getpid()
f = open("ds_pidnum.txt", "w")
f.write(str(pidnum))
f.close()

#================================================================
# read in configurations
config=configparser.ConfigParser()
config.read('config.ini')

INSTANCES   =int(config['GLOBAL'    ]['INSTANCES'   ])  # number of instances recorded when spacebar is hit
FRAME_LENGTH=int(config['GLOBAL'    ]['FRAME_LENGTH'])  # fixed size, need to adjust

#================================================================

is_collecting_dataset = False

frame=[]
frame_complete = 0
save_frames = 0
training_data = [[]]
training_data_frame_counter = 0
try_reconnecting = True # used to mark if we should try to reconnect
command_check_interval = 0.05 # sleep 0.x seconds before checking for spacebar

# Holds the BLE provider for the current platform.
ble = None

# Define service and characteristic UUIDs used in T4T mobile handler.
PHONE_SERVICE_UUID = uuid.UUID('AAAAAAA0-B5A3-F393-E0A9-E50E24DCCA9E')
TX_CHAR_UUID      = uuid.UUID('AAAAAAA1-B5A3-F393-E0A9-E50E24DCCA9E')
RX_CHAR_UUID      = uuid.UUID('AAAAAAA2-B5A3-F393-E0A9-E50E24DCCA9E')
phone = None


class T4TMobile(ServiceBase):
	"""Bluetooth LE phone service object."""

	# Configure expected services and characteristics for the phone service.
	ADVERTISED = [PHONE_SERVICE_UUID]
	SERVICES = [PHONE_SERVICE_UUID]
	CHARACTERISTICS = [TX_CHAR_UUID, RX_CHAR_UUID]

	def __init__(self, device):
		"""Initialize phone from provided bluez device."""
		# Find the phone service and characteristics associated with the device.
		self._device = device.find_service(PHONE_SERVICE_UUID)
		if self._device is None:
			raise RuntimeError('Failed to find expected phone service!')
		self._tx = self._device.find_characteristic(TX_CHAR_UUID)
		self._rx = self._device.find_characteristic(RX_CHAR_UUID)
		if self._tx is None or self._rx is None:
			raise RuntimeError('Failed to find expected phone RX and TX characteristics!')
		# Use a queue to pass data received from the RX property change back to
		# the main thread in a thread-safe way.
		self._queue = queue.Queue()
		# Subscribe to RX characteristic changes to receive data.
		self._rx.start_notify(self._rx_received)

	def _rx_received(self, data):
		# Callback that's called when data is received on the RX characteristic.
		# Just throw the new data in the queue so the read function can access it.
		self._queue.put(data)

	def write(self, data):
		"""Write a string of data to the phone device."""
		self._tx.write_value(data)

	def clear(self): 
		"""remove all entries from queue"""
		with self._queue.mutex:
			#print("clearing bluetooth data queue")
			self._queue.queue.clear()

	def read(self, samples_required=None, timeout_sec=None):
		"""Block until data is available to read from the peripheral.  Will return a
		string of data that has been received.  Timeout_sec specifies how many
		seconds to wait for data to be available and will block forever if None
		(the default).  If the timeout is exceeded and no data is found then
		None is returned.
		"""
		try:
			if samples_required is not None:
				samples = []
				while len(samples) < samples_required:
					samples.append(self._queue.get(timeout=timeout_sec))
				return samples
			else: 
				return self._queue.get(timeout=timeout_sec)
		except queue.Empty:
			# Timeout exceeded, return None to signify no data received.
			return None
				
def exit_with_message(msg):
	print(msg)
	os._exit(0)		

def mobile_data():
	global phone
	if phone is None:
		return 
	global frame_complete, is_collecting_dataset, \
			training_data_frame_counter, frame, training_data, try_reconnecting, INSTANCES, FRAME_LENGTH

	try:
		# note: the mobile device is expected to send data for each active sensor in batches, so that there are just as many accelerometer updates as gyro updates
		# since the number of channels expected starts out unknown to this script, we must bump up the number of samples in need of collection to num_labels * framelength
		if is_collecting_dataset:
			print("Collecting {} training samples of size {}".format(INSTANCES, FRAME_LENGTH))

		tmpframe = []
		unique_labels = set()
		channels_per_sensor = dict()
		flattened_sample_dict = dict() # values reset before each instance
		num_labels_locked = False # we want to make sure the number of labels we get in this data collection 
							      # does not suddenly have more labels than we're ok with
		
		# only do `INSTANCES` many reads if we are not in the dataset collection mode
		instances_to_compute = INSTANCES if is_collecting_dataset else 1
		for instance_idx in range(0, instances_to_compute):
			now = time.time()

			# read fresh BLE data
			phone.clear()
			samples = phone.read(samples_required=FRAME_LENGTH, timeout_sec=10)
			if samples is None:
				print("Timed out: going to try reconnecting")
				try_reconnecting = True
				return

			# process our samples of sensor data
			for sample in samples:
				sample = str(sample)
				sensor_split = sample.split("&") # example - &acc:1,2,3:&gyro:1,2,3:
				for sensor_string in sensor_split[1:]: # skip first entry to avoid reading into the ampersand
					label_split = sensor_string.split(":")
					label = label_split[0]
					data_list = label_split[1].split(",") # split comma-separated numbers
					if not label in unique_labels: 
						if num_labels_locked:
							exit_with_message("Error: number of sensors broadcasting cannot change during collection (for label: {} among {})".format(label, unique_labels))
						unique_labels.add(label)
						flattened_sample_dict[label] = []
						channels_per_sensor[label] = len(data_list) # for xyz on accelerometer, for example
					flattened_sample_dict[label] += data_list
					
				# once we read one message, we should know the number of sensors/labels.
				# disallow new labels. if a sensor stops broadcasting, an error will arise later
				num_labels_locked = True

			total_subchannels_added = 0 # i.e. to remember that we processed x, y... channels
			keys = list(flattened_sample_dict.keys())
			for key in keys:
				channel_count = channels_per_sensor[key]
				for c in range(0, channel_count):
					is_final = 1 if (c == channel_count - 1) and key == keys[-1] else 0
					# will encounter an error here if one of the sensors stopped sending its data in the middle of 
					# the stream, because its row of data for at least one of its channels will not be long enough
					tmpframe.append(flattened_sample_dict[key][c::channel_count] + [total_subchannels_added, is_final]) # example: x data with 0,0 at end signifying channel 0, and incomplete frame
					total_subchannels_added += 1
			
			print("Sample collection rate: {} Hz".format(FRAME_LENGTH/(time.time() - now)))
			# always write tmpframe to file to keep inference up to date
			tmpframe = np.asarray(tmpframe)
			np.save('tmpframe', tmpframe[:, -(FRAME_LENGTH + 2):]) # write last framelength chunk (+2 to account for channel indices)
			
			# only save to training file if in training state
			if is_collecting_dataset:
				training_data[0].append(tmpframe)
				for key in flattened_sample_dict.keys():
					flattened_sample_dict[key] = []

			# empty out tmpframe for next loop 
			tmpframe = []
		
		# now that we have sent `instances` many frames, wrap it up 
		if is_collecting_dataset:
			is_collecting_dataset = False
			f = open("current_label.txt", "r")
			current_label = f.read().strip()
			f.close()
			
			training_data_file_name = 'training_data_{}.npy'.format(current_label)
			print('Saving training data to {}'.format(training_data_file_name))
			if os.path.exists(os.path.join(os.getcwd(), training_data_file_name)):
				existing_training_data = np.load(training_data_file_name)
				np.save(training_data_file_name,
						np.append(existing_training_data,
						training_data,
						axis=0))
			else:
				np.save(training_data_file_name, training_data)

			# cleanup global variables
			training_data = [[]]


	except Exception as e:
		print("EXCEPTION: {}".format(e))
		return
	

def read_message():
	try:
		f = open("ds_cmd.txt", "r")
		cmd = f.read()
		f.close()
		
		if cmd == 'SPACEBAR':
			global is_collecting_dataset
			is_collecting_dataset = True
		
		# warning: not working when sigint triggers a readmessage...
		with open("ds_cmd.txt", "w") as f:
			f.write("")
			
		if cmd == 'BYE':
			print("Exiting {}".format(_FILENAME_))
			os._exit(0)
			
	except Exception as e:
		return # when unable to open command file since not existent

# Main function implements the program logic so it can run in a background
# thread.  Most platforms require the main thread to handle GUI events and other
# asyncronous events like BLE actions.  All of the threading logic is taken care
# of automatically though and you just need to provide a main function that uses
# the BLE provider.
def ble_main(): 
	global phone, is_collecting_dataset, try_reconnecting, command_check_interval
	
	while try_reconnecting:
		try_reconnecting = False # only reset to true if we decide to retry connecting
		# Clear any cached data because both bluez and CoreBluetooth have issues with
		# caching data and it going stale.
		ble.clear_cached_data()

		# Get the first available BLE network adapter and make sure it's powered on.
		adapter = ble.get_default_adapter()
		adapter.power_on()

		# Disconnect any currently connected devices.  Good for cleaning up and
		# starting from a fresh state.
		print('Disconnecting any connected devices...')
		T4TMobile.disconnect_devices()

		# Scan for devices.
		print('Searching for T4T Mobile handler...')
		try:
			adapter.start_scan()
			# Search for the first device found (will time out after 60 seconds
			# but you can specify an optional timeout_sec parameter to change it).
			device = T4TMobile.find_device()
			if device is None:
				raise RuntimeError('Failed to find T4T Mobile handler!')
		finally:
			# Make sure scanning is stopped before exiting.
			adapter.stop_scan()

		print('Connecting to device...')
		device.connect()  # Will time out after 60 seconds, specify timeout_sec parameter
						  # to change the timeout.

		# Once connected do everything else in a try/finally to make sure the device
		# is disconnected when done.
		try:
			# Wait for service discovery to complete for the phone service.  Will
			# time out after 60 seconds (specify timeout_sec parameter to override).
			print('Discovering services...')
			T4TMobile.discover(device)

			# Once service discovery is complete create an instance of the service
			# and start interacting with it.
			phone = T4TMobile(device)

			# Write a string to the TX characteristic.
			phone.write(b'T4T hello\r\n')
			print("Sent hello to device. Waiting for start command.")
			
			while True:
				if read_kill_file():
					print("Exiting {}".format(_FILENAME_))
					os._exit(0)
				read_message() # updates is_collecting_dataset
				mobile_data()
				if try_reconnecting: # check in outer loop to exit to outer-most loop
					break
					
		except Exception as e:
			print("Exception in mobileviz ble main! {}".format(e))
	print("completed call to ble main")


def write_kill_file():
	with open("kill_cmd.txt", "w") as f:
		f.write("close")
		
def read_kill_file():
	try:
		with open("kill_cmd.txt", "r") as f:
			# file exists, return true
			os.remove("kill_cmd.txt")
			return True 
		return False
	except: 
		return False

# MAC/LINUX
# ble runloop cannot handle signal interrupts
def receive_interrupt(signum, stack):
	print("interrupt")


# if signals are supported, then fork a child process and use its pid
if utils.does_support_signals():
	fork_pid = os.fork()
	
	if fork_pid == 0: # case: child process, run BLE on thread here
		# Initialize the BLE system.  MUST be called before other BLE calls!
		ble = Adafruit_BluefruitLE.get_provider()
		ble.initialize()
		# Start the mainloop to process BLE events, and run the provided function in
		# a background thread.  When the provided main function stops running, returns
		# an integer status code, or throws an error the program will exit.
		print("Starting main runloop")
		ble.run_mainloop_with(ble_main)
	
	else: # parent case: receive signals and notify child through a secondary command file
		signal.signal(signal.SIGINT, receive_interrupt)
		
