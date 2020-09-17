#!/usr/bin/env python3
# ============================================================================
""" 
Microphone file for gathering audio data from computer microphone
Microphone config.ini setup:
[GLOBAL]
INSTANCES : 20 (recommended at least, increase for more data)
CHANNELS : 2 or 1 (2 for stereo, 1 for mono)
FRAME_LENGTH : 3000 (recommended chunk size)
CURR_ALGO_INDEX : 3 (random forest is recommended)

[DS]
DS_FILE_NUM : 3
SAMPLE_RATE : 48000 (corresponds to a 48 kHz microphone)

[ML]
NUM_BINS : 300 (can change)

* Requires: 1 <= NUM_BINS <= FRAME_LENGTH / 2 (for fft) or FRAMELENGTH (for raw)

Note: Recommended to collect at at least 3-4 times for each label and to start
    making sound before and continue a little after you collect for training
"""
# ============================================================================

from datetime import timedelta
from timeloop import Timeloop
import numpy as np
import os
import signal
import sys
import utils
import pyaudio
import configparser

# ============================================================================

# write PID to file
pidnum = os.getpid()
f = open("ds_pidnum.txt", "w")
f.write(str(pidnum))
f.close()

f = open("ds_cmd.txt", "w")
f.write("")
f.close()

# ============================================================================
# read in configurations
config = configparser.ConfigParser()
config.read('config.ini')

# global variables
CHUNK = int(config['GLOBAL']['FRAME_LENGTH']) # how many samples at a time you want to read
FORMAT = pyaudio.paInt16  # quality of microphone
CHANNELS = int(config['GLOBAL']['CHANNELS'])
RATE = int(config['DS']['SAMPLE_RATE'])  # sampling rate
instances = int(config['GLOBAL']['INSTANCES'])  # number of instances recorded when spacebar is hit
chunks_per_second = int(RATE / CHUNK)  # how many chunks per second
training_data = [[]]
training_data_frame_counter = 0
is_collecting_dataset = False

# ============================================================================

print("Starting Microphone")

# open an audio stream
p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)


def read_data():
    """
    Reads data from audio stream & returns 1 x (CHANNELS * CHUNK) np array
    """
    # recording the data
    data = stream.read(CHUNK)
    data = np.reshape(np.frombuffer(data, dtype=np.int16), (1, -1))
    return data


def shape_data(data):
    """ Returns: CHANNELS x (CHUNK + 2) np array of data
        last 2 cols: col 1 is the channel index, col 2 is 0 or 1
                for finished or unfinished chunk of data
    """
    global CHANNELS

    # finding the number of channels w/ number of samples / CHUNK
    CHANNELS = int(data.shape[1] / CHUNK)

    # data = [CH1, CH2, CH1, CH2], so separating interwoven channel data
    channel_data = np.reshape(data[:, 0::CHANNELS], (1, -1))  # the first channel
    # appends channel index (0 for first channel) and unfinished 0 (second col)
    channel_data = np.hstack((channel_data, np.array([[0, 0]])))
    tmpframe = channel_data

    # separates other channels
    for i in range(1, CHANNELS):
        channel_data = np.reshape(data[:, i::CHANNELS], (1, -1))
        channel_data = np.hstack((channel_data, np.array([[i, 0]])))  # appends channel index & 0 for unfinished
        tmpframe = np.vstack((tmpframe, channel_data))

    # changes last channel's last col to 1 for finished data tmpframe
    tmpframe[-1, -1] = 1

    return tmpframe


def microphone_data():
    """" Collects data from microphone audio stream and saves
            chunk of data with column endings for UI and ML """
    global is_collecting_dataset, training_data_frame_counter, \
        training_data
    try:
        data = read_data()
        tmpframe = shape_data(data)

        # saves tmpframe to display points for ui
        np.save('tmpframe', tmpframe)

    except Exception as e:
        print("Couldn't read audio stream")
        print(e)
        return

    try:
        # appends chunks to training data
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

            # appends training data to existing data or saves as new data
            if os.path.exists(os.path.join(os.getcwd(), training_data_file_name)):
                existing_training_data = np.load(training_data_file_name)

                np.save(training_data_file_name,
                        np.append(existing_training_data, training_data, axis=0))
            else:
                np.save(training_data_file_name, training_data)
            training_data = [[]]
            is_collecting_dataset = False

            print('Training Data SAVED!!!')

    except Exception as e:
        print(e)
        return


# MAC/LINUX
def receive_interrupt(signum, stack):
    read_message()


def read_message():
    global is_collecting_dataset
    try:
        f = open("ds_cmd.txt", "r")
        cmd = f.read()
        f.close()
    except Exception as e:
        return
    if cmd == 'SPACEBAR':
        is_collecting_dataset = True
        print("Spacebar Closing")
    elif cmd == 'BYE':
        print("Microphone Closing")

        # closing the system
        f = open("ds_cmd.txt", "w")
        f.write("")
        f.close()

        # closing the audio stream
        stream.stop_stream()
        stream.close()
        p.terminate()
        os._exit(0)
    f = open("ds_cmd.txt", "w")
    f.write("")
    f.close()


if utils.does_support_signals():
    signal.signal(signal.SIGINT, receive_interrupt)

    while True:
        microphone_data()

timeloop = Timeloop()


# add timeloop job to handle commands
@timeloop.job(interval=timedelta(seconds=0.3))
def read_message_wrapper():
    read_message()


# add timeloop job to collect and write microphone data
@timeloop.job(interval=timedelta(seconds=(1/chunks_per_second)))
def microphone_data_wrapper():
    microphone_data()


if not utils.does_support_signals():
    timeloop.start(block=True)


print("Microphone Closing")

# closing the audio stream
stream.stop_stream()
stream.close()
p.terminate()

