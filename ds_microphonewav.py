#!/usr/bin/env python3
# ============================================================================
""" 
Microphone file to gather audio data if microphone captures audio in .wav files.

Reads .wav files of audio stream from the folder on line 72 (unless changed, default
    will be T4Train/src/wavs/)

Microphone WAV config.ini setup:
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

Note:
    Lines 178 and 181 are for testing the file by saving stream audio as .wav file, so
    comment out when not testing

Note: Recommended to collect at at least 3-4 times for each label and to start
    making sound before and continue a little after you collect for training
"""
# ============================================================================

from datetime import timedelta
from timeloop import Timeloop
import glob
import numpy as np
import os
import signal
import sys
import time
import utils
import pyaudio
import wave
from scipy.io import wavfile
import configparser

# ============================================================================

# write PID to file
pidnum = os.getpid()
f = open("ds_pidnum.txt", "w")
f.write(str(pidnum))
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
audio_folder = "wavs/"  #folder within src w/ the wav files

# ============================================================================

print("Starting Microphone WAV")

# open an audio stream
p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)


def get_oldest_wav(path):
    """ gets oldest wav file from path"""

    # checking if the wav file exists
    if not os.path.exists(path):
        print("There is no folder named " + audio_folder + ".")
        return None

    # getting all wav files from wav folder
    list_of_files = glob.glob(path + "*.wav")
    if len(list_of_files) == 0:
        print("No wavs were found.")
        return None

    # getting the earlier file
    oldest_file = min(list_of_files, key=os.path.getctime)
    return oldest_file


def save_wav(data, path):
    """ save data as wav file """
    wf = wave.open(path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(data)
    wf.close()


def save_wav_in_file(data):
    """ save wav in wav folder """

    # naming the file
    curr_time=time.strftime("%Y_%m_%d-%H_%M")
    curr_time_file = curr_time + ".wav"

    # makes directory if directory does not already exist
    if not os.path.exists(audio_folder):
        os.makedirs(audio_folder)

    # saving the wavs
    path = os.path.join(os.getcwd(), audio_folder)
    save_wav(data, os.path.join(path, curr_time_file))
    return


def get_wav_from_file():
    """ gets earliest wav in wavs folder, returns data and 
    removes file"""

    # gets path for earliest file & reads data into np array
    folder_path = os.path.join(os.getcwd(), audio_folder)
    wav_path = get_oldest_wav(folder_path)

    fs, data = wavfile.read(wav_path)  # fs == sampling rate
    data = data.T

    # remove the file
    os.remove(wav_path)
    return data


def shape_data(data):
    """ Returns: CHANNELS x (CHUNK + 2) np array of data
        last 2 cols: col 1 is the channel index, col 2 is 0 or 1
                for finished or unfinished chunk of data
    """
    global CHANNELS

    # finding the number of channels from # of rows
    CHANNELS = data.shape[0]

    # initialize column endings matrix
    col_endings = np.zeros((CHANNELS, 2))
    for i in range(CHANNELS):
        col_endings[i, 0] = i
    col_endings[-1, -1] = 1  # last col of last row is 1 for finished frame

    tmpframe = np.hstack((data, col_endings))  # add row endings to tmpframe for ui

    return tmpframe


def microphone_data():
    """" Reads wavs from audio folder into data and saves
        chunk of data with column endings for UI and ML """
    global is_collecting_dataset, training_data_frame_counter, \
        frame, training_data

    try:
        # data = stream.read(CHUNK)  # comment out if microphone sends wavs

        # save the data as a wav in wav folder
        # save_wav_in_file(data)  # comment out if microphone sends wavs

        # read data from wav folder (wavs)
        tmpframe = get_wav_from_file()
        tmpframe = shape_data(tmpframe)

        # saves tmpframe to display points for ui
        np.save('tmpframe', tmpframe)

    except Exception as e:
        print("Could not get data.")
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
            training_data[0] = training_data[0]

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
        print("Microphone WAV Closing")

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


print("Microphone WAV Closing")

# closing the audio stream
stream.stop_stream()
stream.close()
p.terminate()