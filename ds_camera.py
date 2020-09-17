#!/usr/bin/env python3
# ============================================================================
""" 

The camera data handler opens a camera device recognized by OpenCV, uses
MediaPipe to perform hand keypoint detection, and streams keypoints to
T4Train.


Setup: In config.ini, set the proper `DS_FILE_NUM` index that corresponds 
to this file, based on the filenames listed in `DS_FILENAMES`. MediaPipe also 
supports tensorflow-gpu: devices that have a CUDA-enabled GPU can accelerate
keypoint detection. This data handler assumes the appropriate camera is the
first camera device. In the ``camera prep'' section, cv2.VideoCapture()
selects the camera, which by default is camera 0. 

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

# opencv
import cv2
from hand_tracking.src.hand_tracker import HandTracker

# tensorflow
from tensorflow.python.client import device_lib

# for windows
from timeloop import Timeloop

# Self-define functions
import utils


#================================================================
# read in configurations
config=configparser.ConfigParser()
config.read('config.ini')

INSTANCES   =  int(config['GLOBAL'    ]['INSTANCES'   ])  # number of instances recorded when spacebar is hit         
# FRAME_LENGTH=  int(config['GLOBAL'    ]['FRAME_LENGTH'])  # fixed size, need to adjust

#================================================================


is_collecting_dataset      =False
dataset                    =[]
tmpframe                   =[]
tmpframe_RGB               =[]
# tmpframe                   ={}
# frame                      =[]
frame_complete             =0
# save_frames                =0
training_data              =[[]]
training_data_frame_counter=0
# samplelength               =1500
# headerlength               =4
# framelength                =int(samplelength*2+headerlength)


#==================================================================
# Camera prep
WINDOW             ="Hand Tracking"
PALM_MODEL_PATH    ="hand_tracking/models/palm_detection_without_custom_op.tflite"
LANDMARK_MODEL_PATH="hand_tracking/models/hand_landmark.tflite"
ANCHORS_PATH       ="hand_tracking/models/anchors.csv"

POINT_COLOR     =(  0, 255,   0)
CONNECTION_COLOR=(255,   0,   0)
THICKNESS       =2

# cv2.namedWindow(WINDOW)
capture=cv2.VideoCapture(0)
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
#==================================================================

def camera_data():
    global tmpframe, tmpframe_RGB, \
           frame_complete, is_collecting_dataset, \
           training_data_frame_counter, save_frames, frame, training_data
    # while True:
    try:
        now=time.time()

        if capture.isOpened():
            hasFrame, frame=capture.read()
        else:
            hasFrame=False

        #        8   12  16  20
        #        |   |   |   |
        #        7   11  15  19
        #    4   |   |   |   |
        #    |   6   10  14  18
        #    3   |   |   |   |
        #    |   5---9---13--17
        #    2    \         /
        #     \    \       /
        #      1    \     /
        #       \    \   /
        #        ------0-

        connections=[( 0,  1), ( 1,  2), ( 2,  3), ( 3,  4),
                     ( 5,  6), ( 6,  7), ( 7,  8),
                     ( 9, 10), (10, 11), (11, 12),
                     (13, 14), (14, 15), (15, 16),
                     (17, 18), (18, 19), (19, 20),
                     (0, 5), (5, 9), (9, 13), (13, 17), (0, 17)]

        detector=HandTracker(PALM_MODEL_PATH,
                             LANDMARK_MODEL_PATH,
                             ANCHORS_PATH,
                             box_shift=0.2,
                             box_enlarge=1.3)

        while hasFrame:
            image=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            t_start=time.time()
            points, _ =detector(image)
            if points is not None:
                # print(points, "\n")
                # print(np.shape(points))
                for point in points:
                    x, y=point
                    cv2.circle(frame, (int(x), int(y)), THICKNESS * 2, POINT_COLOR, THICKNESS)

                for connection in connections:
                    x0, y0=points[connection[0]]
                    x1, y1=points[connection[1]]
                    cv2.line(frame, (int(x0), int(y0)), (int(x1), int(y1)), CONNECTION_COLOR, THICKNESS)
                
                # # YSI: don't know where to shove this into featurize so we're making this default for now :) 
                # delta = points - points[0]
                # points = delta.copy()
                
                # Store the frame
                # DVS: Tried to use dictionary, but is way too slow
                # tempframe[0]: keypoints locations
                # tempframe[1]: RGB frame with keypoints labeled
                tmpframe.append(points)
                tmpframe_RGB.append(frame)

                frame_complete=1
                # print('HI', np.shape(tmpframe)[0])

            totaltime=time.time()-t_start
            # print(1/totaltime)
            
            # comment these out to remove display
            # cv2.imshow(WINDOW, frame)
            # key = cv2.waitKey(1)
            cv2.imwrite('camera.png', frame)

            # if key == 27:
            #     break

            # capture.release()
            # cv2.destroyAllWindows()
        
            # recorded 1 frame
            # if frame_complete==1 and np.shape(tmpframe)[0]==2:
            if frame_complete==1:      
                # print(type(tmpframe))
                # print(type(tmpframe[0]))
                # print(type(tmpframe[1]))
                # print(tmpframe[0].size)
                # print(tmpframe[1].size)

                tmpframe    =np.asarray(tmpframe).T     # shape: (1, 2, 21)
                tmpframe_RGB=np.asarray(tmpframe_RGB)   # shape: (1, 720, 1280, 3)

                # print(tmpframe_RGB.shape)
                # print(tmpframe[0][20])
                # print(tmpframe[0].size)
                # print(tmpframe[1].size)
                # sys.exit()

                # save live data
                np.save('tmpframe'    , tmpframe)
                np.save('tmpframe_RGB', tmpframe_RGB)

                # collecting frames but not reached the number of smaples yet
                if is_collecting_dataset and training_data_frame_counter<INSTANCES:
                    training_data[0].append(tmpframe)
                    training_data_frame_counter+=1

                # collected enough data for one spacebar -> save it 
                if training_data_frame_counter==INSTANCES:
                    print('Done collecting training data, saving NOW')
                    training_data_frame_counter=0

                    # get label
                    f=open("current_label.txt", "r")
                    current_label=f.read().strip()
                    f.close()


                    # create filename
                    training_data_file_name='training_data_{}.npy'.format(current_label)

                    print('Saving Training Data...')

                    # append data to existing file or store to new file
                    if os.path.exists(os.path.join(os.getcwd(), training_data_file_name)):
                        existing_training_data=np.load(training_data_file_name, allow_pickle=True)

                        np.save(training_data_file_name,
                                np.append(existing_training_data, training_data, axis=0))

                    else:
                        np.save(training_data_file_name, training_data)

                    training_data=[[]]
                    is_collecting_dataset=False

                    print('Training Data SAVED!!!')


                # if save_frames==1 and np.shape(frame)[0]<INSTANCES:
                #     frame.append(tmpframe)

                # elif np.shape(frame)[0]==INSTANCES:
                #     dataset.append(frame)
                #     save_frames=0
                #     frame=[]

                tmpframe=[]
                tmpframe_RGB=[]

            end=time.time()
            hasFrame, frame = capture.read()
    except Exception as e:
        print(e)
        return

# MAC/LINUX
def receive_interrupt(signum, stack):
    read_message()

def read_message():
    try:
        f = open("ds_cmd.txt", "r")
        cmd = f.read()
        f.close()
    except Exception as e:
        return

    if cmd == 'SPACEBAR':
        global is_collecting_dataset
        is_collecting_dataset = True
    elif cmd == 'BYE':
        # s.close()
        f.close()
        os._exit(0)

    f = open("ds_cmd.txt", "w")
    f.write("")
    f.close()

if __name__ == '__main__':
    print('ds_camera.py: Started')

    # write PID to file
    pidnum = os.getpid()
    f = open("ds_pidnum.txt", "w")
    f.write(str(pidnum))
    f.close()

    # Get GPU device name
    device_lib.list_local_devices()

    # if OS supports signals
    if utils.does_support_signals():
        signal.signal(signal.SIGINT, receive_interrupt)

        # Collect data forever
        while True:
            camera_data()

    # No signals to use
    else:
        timeloop = Timeloop()

        # add timeloop job to handle camera commands
        @timeloop.job(interval=timedelta(seconds=0.3))
        def read_message_wrapper():
            read_message()

        # add timeloop job to collect and write camera data
        @timeloop.job(interval=timedelta(seconds=0.2))
        def camera_data_wrapper():
            camera_data()

        timeloop.start(block=True)

    sys.exit()




