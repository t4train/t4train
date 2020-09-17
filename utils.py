"""
Utils.py

Functions that are used in ui.py that don't belong in the interface class.
New tag.

Reusable in other py files.
"""
from sys import platform
import numpy as np
import os


def does_support_signals():
    return not platform == "win32"


def delete_files_ending_in(file_types):
    """Deletes any files that have a extension in file_types (List)."""
    dir = os.getcwd()
    for item in os.listdir(dir):
        if item == "requirements.txt":
            continue

        for file_type in file_types:

            if item.endswith(file_type):
                os.remove(os.path.join(dir, item))
                break


def write_label(label, filename):
    """Sanitizes and writes label to filename."""
    label = label.lower().strip().replace(" ", "_")
    with open(filename, "w") as f:
        f.write(str(label))
        f.close()


def write_cmd_message(filename, message):
    with open(filename, "w") as f:
      f.write(message)


def read_pid_num(filename):
    ml_path = os.path.join(os.getcwd(), filename)
    f = open(ml_path, "r")
    pid = int(f.read())
    f.close()
    return pid


def get_training_data_files_and_labels(labels_raw_text):
    """Gets all training data file names and its sanitized labels."""
    training_data_files = []
    labels = []

    # get sanitized labels and all existing training data files
    for label in labels_raw_text:
        sanitized_label = label.lower().strip().replace(" ", "_")

        # user can train without collected training data for all labels
        if os.path.exists('training_data_{}.npy'.format(sanitized_label)):
            training_data_files.append(
                'training_data_{}.npy'.format(sanitized_label)
            )

        labels.append(sanitized_label)

    return [training_data_files, labels]


def write_training_labels(training_data_files, labels, filename):
    """Write npy file of labels (input for ML)."""
    # write as many labels as rounds collected for each training file
    for file, label in zip(training_data_files, labels):

        num_rounds = np.load(file).shape[0]

        training_labels = np.array([])

        if os.path.exists(filename):
            # read current training_labels file if exists
            training_labels = np.load(filename)

        # write labels for each round
        for i in range(0, num_rounds):
            training_labels = np.append(training_labels,
                                        [label],
                                        axis=0)

        # save ndarray of shape (rounds, 1) to npy file
        np.save(filename, training_labels)


def compile_all_training_data(training_data_files, filename):
    """Compiles all training data files into one file (input for ML)."""
    if len(training_data_files) > 0:
        all_training_data = np.load(training_data_files[0])

        np.save(filename, all_training_data)

        for i in range(1, len(training_data_files)):
            file = training_data_files[i]

            current_training_data = np.load(file)

            all_training_data = np.append(all_training_data,
                                          current_training_data,
                                          axis=0)

            np.save(filename, all_training_data)


def increment_algo_ind(curr_ind, algos):
    return (curr_ind + 1) % len(algos)


# ============= Common featurization functionality ========
from enum import Enum
class Featurization(Enum): # enum for featurization to use
    Raw = "Raw"
    Variance = "Variance"
    Derivative = "Derivative"
    RootMeanSquare = "RootMeanSquare"
    FFT = "FFT" # fast fourier transform
    Mean = "Mean"
    Sum = "Sum"
    Min = "Min"
    Max = "Max"
    Delta = "X/Y"

# input shape is (c, s), where c is the number of channels, s is the number of samples
def featurize(input_frame, featurization_type=Featurization.Raw, numbins=60, sample_rate=None):
    # for feats that don't use binning, just ravel the data without a bin check
    if featurization_type == Featurization.Raw:
        return np.reshape(input_frame, (-1, 1))
    if featurization_type == Featurization.Delta:
        reframe = np.reshape(input_frame - input_frame[0], (-1, 1))
        return reframe

    # For feats that do use binning, only flatten after cutting out the 
    # samples which do not make up a multiple of numbins
    if len(input_frame.shape) > 1:
        binnable_length = input_frame.shape[1] // numbins * numbins
        input_frame = input_frame[:, :binnable_length] # cut out non-multiple samples

    else:
        binnable_length = input_frame.shape[0] // numbins * numbins # case of only one channel
        input_frame = input_frame[:binnable_length] # cut out non-multiple samples
    
    if featurization_type == Featurization.Variance:
        reframe = np.reshape(input_frame, (numbins,-1))
        reframe = np.reshape(np.var(reframe, axis = 1), (-1, 1))
        return reframe
    elif featurization_type == Featurization.Sum:
        reframe = np.reshape(input_frame, (numbins, -1))
        reframe = np.reshape(np.sum(reframe, axis = 1), (-1, 1))
        return reframe
    elif featurization_type == Featurization.Derivative: # could also use np.gradient for second order central differences
        # shift copy of matrix to the left and subtract, then take average of the n subtractions
        reframe = np.reshape(input_frame, (numbins,-1))
        reframe = np.mean(reframe[:, 0:-1] - reframe[:, 1:], axis = 1)
        reframe = -1 * np.reshape(reframe, (-1, 1))
        return reframe
    elif featurization_type == Featurization.RootMeanSquare:
        reframe = np.reshape(input_frame, (numbins,-1))
        reframe = np.sqrt((1/numbins)*(reframe**2))
        return np.reshape(reframe, (-1, 1))
    elif featurization_type == Featurization.Mean:
        reframe = np.reshape(input_frame, (numbins,-1))
        return np.reshape(np.mean(reframe, axis = 1), (-1, 1))
    elif featurization_type == Featurization.Min:
        reframe = np.reshape(input_frame, (numbins,-1))
        reframe = np.reshape(np.min(reframe, axis=1), (-1, 1))
        return reframe
    elif featurization_type == Featurization.Max:
        reframe = np.reshape(input_frame, (numbins,-1))
        reframe = np.reshape(np.max(reframe, axis=1), (-1, 1))
        return reframe
    elif featurization_type == Featurization.FFT:
        # input_frame should only be for one channel
        reframe = np.ravel(input_frame)
        rfft_out = np.reshape(np.abs(np.fft.rfft(reframe, norm=None)), (1, -1))

        # calculating how data can be binned + dropped index
        binnable_length = (rfft_out[:, 1:].shape[1] // numbins * numbins) + 1

        # drop the 0th index representing 0 * fs
        rfft_out = np.sum(np.reshape(rfft_out[:, 1:binnable_length], (numbins, -1)), axis=1)
        rfft_out = np.reshape(rfft_out, (-1, 1))
        return rfft_out

