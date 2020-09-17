#!/usr/bin/env python3
# ============================================================================
""" 
The teensy data handler receives data via serial from a teensy, reshapes the
data by channels, and hands a complete data frame to T4Train. This data
handler compared to the Arduino data handler, is optimized to maximize the
data throughput for the Teensy 3.6 and Teensy 4.0. 


Setup: In config.ini, set the proper `DS_FILE_NUM` index that corresponds 
to this file, based on the filenames listed in `DS_FILENAMES`. The
`FRAME_LENGTH' needs to match ``samplelength'' in this file and the 
`CHANNELS' needs to match ``numchannels''.

Performance Notes: There are many ``magic numbers'' in this file. These
numbers maximized the performance of the Teensy while retaining reliability. 
A baud rate greater than 2000000 decreases reliability and a sample length
greater than 1500 causes timing issues on the Teensy. This file is largely
not ``plug-and-play'' for performance. 

"""
# ============================================================================


# System
import os
import sys
import time
import signal
import configparser
from datetime import timedelta
import glob

# Data processing
import numpy as np
from scipy import signal

# serial
import serial

# for windows
from timeloop import Timeloop

# Self-define functions
import utils

# write PID to file
pidnum = os.getpid()
f = open("ds_pidnum.txt", "w")
f.write(str(pidnum))
f.close()


def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(6)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.usb*')
    else:
        raise EnvironmentError('Unsupported platform')

    return ports


if __name__ == '__main__':
    print(serial_ports())


class FPSTracker:
    def __init__(self, alpha=0.1):
        """ smaller alpha = stronger smoothing """
        self.alpha = alpha
        self.prev = None
        self.delta = None

    def tick(self):
        """ Tick the tracker; call this at a fixed period.
        Calling this method is optional.
        Calling this decays the FPS value if updates stop. """

        now = time.time()
        if self.prev is not None and self.delta is not None:
            if now - self.prev < self.delta:
                # update happened recently, ignore this tick
                return
            newdelta = now - self.prev
            self.delta += self.alpha * (newdelta - self.delta)

    def update(self):
        """Update the tracker. Call this on every event."""

        now = time.time()
        if self.prev is None:
            self.prev = now
            return

        if self.delta is None:
            self.delta = now - self.prev
            self.prev = now
            return

        newdelta = now - self.prev
        self.delta += self.alpha * (newdelta - self.delta)
        self.prev = now

    def fps(self):
        if self.delta is None:
            return 0.0
        return 1.0 / self.delta


# read a certain number of bytes from a data stream
def readall(s, n):
    res = bytearray()
    while len(res) < n:
        chunk = s.read(n - len(res))
        if not chunk:
            raise EOFError()
        res += chunk
    return res


def resync():
    res = bytearray()
    while 1:
        b = s.read(1)  # Should make s a parameter to stay consistent with readall function
        if not b:
            raise EOFError()
        res += b
        if res.endswith(b'\xde\xad\xbe\xef'):
            break
    return res


def getframe(instances):
    # fps = FPSTracker()
    counter = 0
    tmpframe = []
    frame = []
    frame_complete = 0
    now = time.time()
    while np.shape(frame)[0] < instances:
        discarded = resync()
        arr = np.frombuffer(readall(f, framelength), dtype='uint16')
        if arr[-1] == 0:
            tmpframe.append(arr)
        if arr[-1] == 1:
            tmpframe.append(arr)
            frame_complete = 1
        if frame_complete == 1 and np.shape(tmpframe)[0] == 3:
            tmpframe = np.asarray(tmpframe)
            tmpframe = tmpframe[tmpframe[:, -2].argsort()]
            frame.append(tmpframe)
            frame_complete = 0
            tmpframe = []
    end = time.time()
    return frame


is_collecting_dataset = False

dataset = []


# searches for serial port
if sys.platform.startswith('darwin'):
    ports = serial_ports()
    if len(ports) == 0: 
        print("No open serial ports detected!")
        exit(1)
    else:
        preferred_port = None
        s = None
        for port in ports: 
            if "usbmodem" in port or "teensy" in port:
                preferred_port = port
            
        if preferred_port: 
            # if we have a port with a familiar arduino or teensy name, pick it
            print("Connecting to preferred port: {}".format(preferred_port))
            s = serial.Serial(preferred_port, 2000000, timeout=None, 
                                bytesize=serial.EIGHTBITS, xonxoff=False, rtscts=False, dsrdtr=False)
        else:
            # otherwise, just go with the first port
            print("Connecting to first available port: {}".format(ports[0]))
            s = serial.Serial(serial_ports()[0], 2000000, timeout=None, 
                                bytesize=serial.EIGHTBITS, xonxoff=False, rtscts=False, dsrdtr=False)

if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
    s = serial.Serial('/dev/ttyACM0')  ### /dev/ttyACM0 if real machine or /dev/ttyS0


if sys.platform.startswith('win'):
    s = serial.Serial('COM4')


instances = 10
tmpframe = []
frame = []
frame_complete = 0
save_frames = 0
training_data = [[]]
training_data_frame_counter = 0
samplelength = 1500
headerlength = 4
framelength = int(samplelength*2+headerlength)
numchannels = 3
print("Starting Teensy")


def teensy_data():
    """Getting data from teensy, saving # of instances of data as tmpframe"""
    global tmpframe, frame_complete, is_collecting_dataset, \
        training_data_frame_counter, save_frames, frame, training_data, instances
    try:
        now = time.time()
        discarded = resync()
        arr = np.frombuffer(readall(s, framelength), dtype='uint16')
        if arr[-1] == 0:
            tmpframe.append(arr)
        if arr[-1] == 1:
            tmpframe.append(arr)
            frame_complete = 1
        
        if frame_complete == 1 and np.shape(tmpframe)[0] == numchannels:
            tmpframe = np.asarray(tmpframe)

            tmpframe = tmpframe[tmpframe[:, -2].argsort()]
            np.save('tmpframe', tmpframe)

            if is_collecting_dataset and training_data_frame_counter < instances:
                training_data[0].append(tmpframe)
                training_data_frame_counter += 1

            if training_data_frame_counter == instances:
                print('Done collecting training data, saving NOW')
                training_data_frame_counter = 0

                # get label
                f = open("current_label.txt", "r")
                current_label = f.read().strip()
                f.close()

                training_data_file_name = 'training_data_{}.npy'.format(current_label)

                print('Saving Training Data...')

                if os.path.exists(os.path.join(os.getcwd(), training_data_file_name)):
                    existing_training_data = np.load(training_data_file_name)

                    np.save(training_data_file_name,
                            np.append(existing_training_data, training_data, axis=0))
                else:
                    np.save(training_data_file_name, training_data)
                training_data = [[]]
                is_collecting_dataset = False

                print('Training Data SAVED!!!')

            if save_frames == 1 and np.shape(frame)[0] < instances:
                frame.append(tmpframe)

            elif np.shape(frame)[0] == instances:
                dataset.append(frame)
                save_frames = 0
                frame = []
            tmpframe = []
        end = time.time()

    except Exception as e:
        print(e)
        return


# MAC/LINUX
def receive_interrupt(signum, stack):
    read_message()


def read_message():
    try:
        f = open("ds_cmd.txt", "w")
        cmd = f.read()
    except Exception as e:
        return
        
    if cmd == 'SPACEBAR':
        global is_collecting_dataset
        is_collecting_dataset = True
    elif cmd == 'BYE':
        print("Teensy closing")
        f.write("")
        f.close()
        os._exit(0)
        
    f.write("")
    f.close()


if utils.does_support_signals():
    signal.signal(signal.SIGINT, receive_interrupt)

    while True:
        teensy_data()


timeloop = Timeloop()

# add timeloop job to handle teensy commands
@timeloop.job(interval=timedelta(seconds=0.3))
def read_message_wrapper():
    read_message()


# add timeloop job to collect and write teensy data
@timeloop.job(interval=timedelta(seconds=0.2))
def teensy_data_wrapper():
    teensy_data()


if not utils.does_support_signals():
    timeloop.start(block=True)

