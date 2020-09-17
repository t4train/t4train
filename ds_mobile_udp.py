#!/usr/bin/env python3
# ============================================================================
""" 
The mobile UDP handler receives sensor data from iOS devices via UDP over a 
shared network in the format sent from the `Mobile Handler` iOS app available
on the T4Train Github Repository. 

iOS devices running the Mobile data handler simply set the communication mode 
to UDP and activate sensors like accelerometer and gyroscope. The iOS app 
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
import socket
import time 

#================================================================
# udp setup
UDP_IP = "127.0.0.1"
UDP_PORT = 6789

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
sock.bind(("", UDP_PORT))
sock.settimeout(3)

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

# remaining gloabls
is_collecting_dataset = False
frame=[]
frame_complete = 0
save_frames = 0
training_data = [[]]
training_data_frame_counter = 0
try_reconnecting = True # used to mark if we should try to reconnect
command_check_interval = 0.05 # sleep 0.x seconds before checking for spacebar

def exit_with_message(msg):
	print(msg)
	os._exit(0)

def mobile_data():
	global frame_complete, is_collecting_dataset, \
			training_data_frame_counter, frame, training_data, try_reconnecting
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
			# wait on `framelength`-many reads
			samples = list()
			for i in range(0, FRAME_LENGTH):
				# buffer size is 2048 bytes max
				data = None
				while data == None:
					data, addr = sock.recvfrom(2048)
					if data == None: 
						print("UPD timed out...")
					elif data[0] != 38 or data[-1] != 58: # must begin with ampersand and end with colon
						print(data[-1])
						print("CORRUPTED UDP PACKET: {}".format(data))
						data = None
				samples.append(data)
			
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

			total_subchannels_added = 0 # to remember that we processed x and y, for example --> total = 2
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
		print("EXCEPTION: {} - check disabled sensors / ip correctness".format(e))
		return
		
# MAC/LINUX
def receive_interrupt(signum, stack):
	read_message()
	# must immediately call mobile_data to ensure successful append to data
	mobile_data() 

def read_message():
	cmd = None
	try:
		with open("ds_cmd.txt", "r+") as f:
			cmd = f.read()			
			if cmd == 'SPACEBAR':
				global is_collecting_dataset
				is_collecting_dataset = True
			elif cmd == 'BYE':
				f.write("")
				f.close()
				os._exit(0)
			f.write("")
			f.close()
	except Exception as e:
		print("Exception reading command", e)

if utils.does_support_signals():
	signal.signal(signal.SIGINT, receive_interrupt)

	while True:
		mobile_data() # collect a instances many framelengths

timeloop = Timeloop()

# add timeloop job to handle teensy commands
@timeloop.job(interval=timedelta(seconds=0.3))
def read_message_wrapper():
	read_message()

# add timeloop job to collect and write teensy data
@timeloop.job(interval=timedelta(seconds=0.2))
def mobile_data_wrapper():
	print("mobile data called")
	mobile_data()

if not utils.does_support_signals():
	timeloop.start(block=True)
