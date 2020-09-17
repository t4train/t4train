#!/usr/bin/env python3
# ============================================================================
""" 
Detailed but concise file description here
"""
# ============================================================================

import os
import sys
import time
import signal
import configparser
from timeloop import Timeloop
from datetime import timedelta

# Data processing
import numpy as np
import json

### SKLEARN Stuff
from sklearn.ensemble import VotingClassifier, VotingRegressor
from sklearn import preprocessing
from sklearn.metrics import confusion_matrix as sk_confusion

### Classifiers
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC

### Regressors
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor

### Kfold
from sklearn.model_selection import KFold

# Self-define functions
import utils

# Get PID
pidnum=os.getpid()

# Store PID
f=open("ml_pidnum.txt", "w")
f.write(str(pidnum))
f.close()

#================================================================
# read in configurations
config = configparser.ConfigParser()
config.read('config.ini')

INSTANCES = int(config['GLOBAL']['INSTANCES'])  # number of instances recorded when spacebar is hit
FRAME_LENGTH = int(config['GLOBAL']['FRAME_LENGTH'])  # fixed size, need to adjust

NUM_BINS = int(config['ML']['NUM_BINS'])  # feturization bins
SAMPLE_RATE = int(config['DS']['SAMPLE_RATE'])

DS_HANDLERS = config['DS']['DS_HANDLERS'][1:-1].split(',')
DS_FILE_NUM = int(config['DS']['DS_FILE_NUM'])

curr_algo_index = int(config['GLOBAL']['CURR_ALGO_INDEX'])

# Get data collection method
ds_handler = DS_HANDLERS[DS_FILE_NUM]

# ================================================================

is_training = False
is_inferencing = False
model = None
algos = ['voting', 'mlp', 'svm', 'rf']

# algorithm and mode to run
algo = algos[curr_algo_index]
mode = 'classifier'

#================================================================

# set featurization type
feat = utils.Featurization.Variance
if "Microphone" in ds_handler:
    feat = utils.Featurization.FFT
if "Camera" in ds_handler:
    feat = utils.Featurization.Raw
feat_from_last_train = feat

def save_model(curr_time):
    """Saves model when user presses 'S'."""
    np.save('saved_files/{}/model'.format(curr_time), model)


def init_machine_learning(algo='voting', mode='classifier'):
    """Initializes machine learning algorithm."""

    # Based on algo variable, determines respective classifer and regressor

    if algo == 'voting':
        mlpclf = MLPClassifier()
        mlpreg = MLPRegressor()
        svmclf = SVC(kernel='rbf')
        svmreg = SVR(kernel='rbf')
        rfclf = RandomForestClassifier(n_jobs=-1, n_estimators=500)
        rfreg = RandomForestRegressor(n_jobs=-1,n_estimators=500)
        clf = VotingClassifier(estimators=[('mlp', mlpclf),
                                           ('svm', svmclf),
                                           ('rf', rfclf)],
                               voting='hard')
        reg = VotingRegressor([('mlp', mlpreg),
                               ('svm', svmreg),
                               ('rf', rfreg)])
    elif algo == 'mlp':
        clf = MLPClassifier()
        reg = MLPRegressor()
    elif algo == 'svm':
        clf = SVC(kernel='poly')
        reg = SVR(kernel='poly')
    elif algo == 'rf':
        clf = RandomForestClassifier(n_jobs=-1, n_estimators=500)
        reg = RandomForestRegressor(n_jobs=-1, n_estimators=500)
    else:
        clf = RandomForestClassifier(n_jobs=-1, n_estimators=500)
        reg = RandomForestRegressor(n_jobs=-1, n_estimators=500)

    # based on mode specified, returns classifier or regressor

    if mode == 'classifier':
        return clf
    if mode == 'regressor':
        return reg


def confusion_matrix():
    clf_conf = init_machine_learning(algos[curr_algo_index], mode)
    print("init ml for confusion")
    # load training data
    try:
        training_data = np.load('training_data.npy').astype('float')
        training_labels = np.load('training_labels.npy')
    except Exception as e:
        print(e)
        return
    X_train = []
    Y_train = []
    # featurizes the data
    for i in range(0, np.shape(training_data)[0]):
        for j in range(0, np.shape(training_data)[1]):
            tmptrain = training_data[i, j, :, :-2]
            tmptrain = np.ravel(tmptrain)
            tmptrain = utils.featurize(tmptrain, featurization_type=feat, numbins=NUM_BINS, sample_rate=SAMPLE_RATE)
            X_train.append(tmptrain)
            Y_train.append(training_labels[i])

    X = np.array(X_train)[:, :, 0]
    y = np.array(Y_train)

    le = preprocessing.LabelEncoder()
    le.fit(y)
    y = le.transform(y)
    numclasses = len(le.classes_)
    kf = KFold(n_splits=10, shuffle=True)
    kf.get_n_splits(X)
    acc=[]
    cnf=[]
    # test train split
    for train_index, test_index in kf.split(X):
        X_train, X_test = X[train_index], X[test_index]
        y_train, y_test = y[train_index], y[test_index]
        clf_conf.fit(X_train,y_train.ravel()) # trains the model
        tmpacc = clf_conf.score(X_test,y_test) # gets the accuracy of the classifier
        y_pred = clf_conf.predict(X_test) # classification
        cnf.append(sk_confusion(y_test,y_pred)) # creates confusion matrix
        acc.append(tmpacc)

    finalacc, finalcnf = [], []
    finalacc.append(np.mean(acc))
    totalcnf = np.sum(cnf,axis=0)

    newcnf = np.copy(totalcnf)
    for i in range(0,numclasses):
        newcnf[i,:] = newcnf[i,:]*100 / np.sum(totalcnf[i,:]) # converts to percentages
    finalcnf.append(newcnf)
    finalcnf = np.mean(finalcnf,axis=0)
    np.savetxt('confusion_matrix.csv', finalcnf, delimiter=',')

def feature_importances():
    # load training data
    try:
        training_data = np.load('training_data.npy').astype(np.float)
        training_labels = np.load('training_labels.npy')
    except Exception as e:
        print(e)
        return
    X_train = []
    Y_train = []
    # featurizes the data
    for i in range(0, np.shape(training_data)[0]):
        for j in range(0, np.shape(training_data)[1]):
            tmptrain = training_data[i, j, :, :-2] # cut out channel index flags
            tmptrain = utils.featurize(tmptrain, featurization_type=feat, numbins=NUM_BINS, sample_rate=SAMPLE_RATE)
            X_train.append(tmptrain)
            Y_train.append(training_labels[i])

    X_train = np.array(X_train)[:, :, 0]
    Y_train = np.array(Y_train)

    le = preprocessing.LabelEncoder()
    le.fit(Y_train)
    Y_train = le.transform(Y_train)

    model = init_machine_learning('rf', 'classifier') # initializes the machine learning model learning classifier to rf 
    model.fit(X_train, Y_train) # trains the model
    np.savetxt('feature_importances.csv', model.feature_importances_, delimiter=',')


def read_message():
    """Handles ML commands written by ui.py."""
    global is_training, le, model, is_training, is_inferencing, \
                    curr_algo_index, algo

    # tests to see if the file can be open  

    try:
        f = open("ml_cmd.txt", "r")
        cmd = f.read()
        f.close()
    except Exception as e:
        return
        
    try:
        with open("feat.txt", "r") as f:
            feat = utils.Featurization(f.read())
    except Exception as e: # if no file, assume raw by default
#        print("Error: unable to read featurization method ml.py")
        feat = utils.Featurization.Raw

    if cmd == 'TRAIN':
        is_training = True
        le = None
        model = None
    elif cmd == 'FEATURE_IMPORTANCE':
        feature_importances()
    elif 'TOGGLE_ALGO' in cmd:
        curr_algo_index = int(cmd[-1])
        algo = algos[curr_algo_index]
        model = None
        is_inferencing = False
        is_training = False
    elif cmd == 'CONFUSION':
        confusion_matrix()
    elif cmd == 'STOP PREDICTING':
        is_inferencing = False
    elif cmd == 'BYE':
        os._exit(0)
    elif 'SAVE' in cmd:
        curr_time = cmd.split()[1].strip()
        save_model(curr_time)
    try:
        f = open("ml_cmd.txt", "w")
        f.write("")
        f.close()
    except Exception as e:
        return


def receive_interrupt(signum, stack):
    """Catches signals from ui.py and handles ml commands."""
    read_message()


def ml_train():
    """Trains the ml algorithm."""
    global feat_from_last_train, feat

    try:
        training_data = np.load('training_data.npy').astype(np.float)
    except Exception as e:
        print(e)
        return None, None


    if "Camera" not in ds_handler:
        training_data = training_data[:, :, :, :-2] # cut out channel indices stored in last two cols of all rows
    training_labels = np.load('training_labels.npy')
    X_train = []
    Y_train = []

    # featurizes the data     
    for i in range(0, np.shape(training_data)[0]):
        for j in range(0, np.shape(training_data)[1]):
            tmptrain = training_data[i, j, :, :-2] # cut out columns with channel indices
            tmptrain = utils.featurize(tmptrain, featurization_type=feat, numbins=NUM_BINS, sample_rate=SAMPLE_RATE)
            X_train.append(tmptrain)
            Y_train.append(training_labels[i])
    
    X_train = np.array(X_train)[:, :, 0]
    Y_train = np.array(Y_train)

    le = preprocessing.LabelEncoder()
    le.fit(Y_train)
    Y_train = le.transform(Y_train)
    # initializes machine learning classifier/regressor  

    model = init_machine_learning(algos[curr_algo_index], mode)
    model.fit(X_train, Y_train) # trains the model
    feat_from_last_train = feat
    return [le, model]


def ml_main():
    """Handles training and predicting of ml algorithm."""
    global is_training, is_inferencing, le, model, feat_from_last_train

    if is_training:
        le, model = ml_train()
        is_training = False
        is_inferencing = True

    if is_inferencing:
        try:
            X_test = np.load('tmpframe.npy').astype(np.float)
            assert(X_test.size != 0)
            assert(le is not None)
            assert(model is not None)
        except Exception as e:
            return
        
        X_test = X_test[:,:-2] # cut out columns with channel indices
        X_test = utils.featurize(X_test, featurization_type=feat_from_last_train, numbins=NUM_BINS, sample_rate=SAMPLE_RATE)
        # write prediction to file
        prediction = le.inverse_transform(model.predict(X_test.T))
        np.save('prediction', np.array(prediction))


timeloop_ml = Timeloop()


# adds timeloop job for checking for ml commans
@timeloop_ml.job(interval=timedelta(seconds=0.3))
def read_message_wrapper():
    read_message()


# adds timeloop job for training and predicting
@timeloop_ml.job(interval=timedelta(seconds=0.2))
def ml_main_wrapper():
    ml_main()


if utils.does_support_signals():
    signal.signal(signal.SIGINT, receive_interrupt)

    while True:
        ml_main()


if not utils.does_support_signals():
    # starts the timeloop jobs if OS does not support signals
    timeloop_ml.start(block=True)

sys.exit()
