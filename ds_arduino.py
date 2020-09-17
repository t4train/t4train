#!/usr/bin/env python3
# ============================================================================
""" 
<1 sentence overview of what this file does>

<A brief description of how the data is processed by this file and 
what parts of config.ini might need to be adjusted.>

Setup: <relevant parts of config.ini might need to be adjusted>
"""
# ============================================================================


# System
import os
import sys
import time
import signal
import configparser
from datetime import timedelta

# Data processing
import numpy as np

# Ports
import glob
import serial

# for windows
from timeloop import Timeloop

# Self-define functions
import utils

#================================================================
# read in configurations
config=configparser.ConfigParser()
config.read('config.ini')
       
INSTANCES   =  int(config['GLOBAL'    ]['INSTANCES'   ])  # number of instances recorded when spacebar is hit
FRAME_LENGTH=  int(config['GLOBAL'    ]['FRAME_LENGTH'])  # fixed size, need to adjust

T_RECORD    =float(config['DS_arduino']['T_RECORD'    ])  # record for seconds per instances
T_OVERLAP   =float(config['DS_arduino']['T_OVERLAP'   ])  # overlap seconds                   
#================================================================

# Global variables
is_collecting_dataset      =False   # enabled when spacebar hit

# Static variables
t_start_collect            =0       # act as static for func
training_data_frame_counter=0       # counter for spacebar hits, act as static for func
tmpframe                   =[]      # place to store current data
previousframe              =[]      # place to store previous data
training_data              =[[]]    # Store training data 


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

def get_serial():
    # Get serial port name based on different OS

    # Mac
    if sys.platform.startswith('darwin'):
        ports = serial_ports()
        if len(ports) == 0: 
            print("ds_arduino.py: No open serial ports detected! Quit.")
            sys.exit()
        else:
            preferred_port = None
            s = None
            for port in ports: 
                if "usbmodem" in port or "teensy" in port:
                    preferred_port = port
                
            if preferred_port: 
                # if we have a port with a familiar arduino or teensy name, pick it
                print("Connecting to preferred port: {}".format(preferred_port))
                s = serial.Serial(preferred_port,
                                  9600,
                                  timeout=None, 
                                  bytesize=serial.EIGHTBITS,
                                  xonxoff=False,
                                  rtscts=False,
                                  dsrdtr=False)
            else:
                # otherwise, just go with the first port
                print("Connecting to first available port: {}".format(ports[0]))
                s = serial.Serial(serial_ports()[0],
                                  9600,
                                  timeout=None,
                                  bytesize=serial.EIGHTBITS,
                                  xonxoff=False,
                                  rtscts=False,
                                  dsrdtr=False)

    # ubuntu or VM on Windows
    if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # /dev/ttyACM0 if real machine or /dev/ttyS0
        s = serial.Serial('/dev/ttyACM0', 9600)

    # Windows
    if sys.platform.startswith('win'):
        s = serial.Serial('COM4')

    return s

def arduino_data(s):
    global is_collecting_dataset,       \
           tmpframe,                    \
           T_RECORD,                    \
           T_OVERLAP,                   \
           training_data_frame_counter, \
           t_start_collect,             \
           previousframe,               \
           FRAME_LENGTH,                \
           training_data
    # while True:
    # s.xonxoff=1
    # s.stopbits = 2
    try:
        now=time.time()
        # print("now:", now)

        # Read from Arduino
        b       =s.readline()
        string_n=b.decode()         # decode byte string into Unicode  
        string  =string_n.rstrip()  # remove \n and \r
        flt     =float(string)      # convert string to float
        # print(flt)
        tmpframe.append(flt)

        # 
        if (now-t_start_collect)>T_OVERLAP:
            # overlap frames
            frame        =tmpframe+previousframe
            previousframe=tmpframe
            tmpframe     =frame

            # Store data
            tmpframe=np.asarray(tmpframe)
            tmpframe=tmpframe[:FRAME_LENGTH] # if needed
            tmpframe=np.expand_dims(tmpframe, axis=0)
            print('len:', tmpframe.shape)
            np.save('tmpframe', tmpframe)

            if is_collecting_dataset:
                if training_data_frame_counter<INSTANCES:
                    training_data_frame_counter+=1
                    training_data[0].append(tmpframe)
                else:

                    print('Done collecting training data, saving NOW')
                    training_data_frame_counter=0

                    # get label
                    f            =open("current_label.txt", "r")
                    current_label=f.read().strip()
                    f.close()

                    # create file name based on label
                    training_data_file_name='training_data_{}.npy'.format(current_label)

                    print('Saving Training Data...')

                    # check if file already exist, if yes, then append
                    if os.path.exists(os.path.join(os.getcwd(), training_data_file_name)):
                        existing_training_data=np.load(training_data_file_name)
                        np.save(training_data_file_name,
                                np.append(existing_training_data, training_data, axis=0))
                    # else create a new file
                    else:
                        np.save(training_data_file_name, training_data)
                
                    training_data = [[]]
                    is_collecting_dataset = False

                    print('Training Data SAVED!!!')

            tmpframe=[]
            t_start_collect=time.time()

    except Exception as e:
        print('ds_arduino:', e)
        s.close()
        sys.exit()

    end=time.time()
    return

def read_message():
    # Read command
    try:
        f = open("ds_cmd.txt", "r")
        cmd = f.read()
        f.close()
    except Exception as e:
        return

    # Check command
    if cmd == 'SPACEBAR':
        global is_collecting_dataset, t_start_collect
        is_collecting_dataset = True
        t_start_collect=time.time()
    elif cmd == 'BYE':
        s.close()
        f.close()
        sys.exit()

    # Clear command
    f = open("ard_cmd.txt", "w")
    f.write("")
    f.close()

# MAC/LINUX
def receive_interrupt(signum, stack):
    read_message()

if __name__ == '__main__':
    print('ds_arduino.py: Started')

    # write PID to file
    pidnum = os.getpid()
    f = open("ds_pidnum.txt", "w")
    f.write(str(pidnum))
    f.close()

    # print("All ports:")
    # print(serial_ports())
    
    s=get_serial()

    # Hook up crtl+c to self-define function
    if utils.does_support_signals():
        signal.signal(signal.SIGINT, receive_interrupt)

    # Collect data forever
    while True:
        arduino_data(s)

    s.close()
    sys.exit()
