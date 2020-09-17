import pyaudio
import numpy as np
import wave
import matplotlib.pyplot as plt


CHUNK = 1024 # how many samples at a time you want to read per frame (?), play around w/ it
FORMAT = pyaudio.paInt16  # quality of microphone
CHANNELS = 2  # L R, currently only supports 2 channels
RATE = 48000  # sampling rate
RECORD_SECONDS = 1
WAVE_OUTPUT_FILENAME = "output.wav"
LEFT = 0
RIGHT = 1

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("* recording")

tmpframe = np.empty((1, 1))
print("tmpframe begin: " + str(tmpframe))
frames = []  # for generating a wav file

# recording the data
for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    frames.append(data)
    matrix_data = np.reshape(np.frombuffer(data, dtype=np.int16), (1, -1))
    print("data shape: " + str(matrix_data.shape))
    tmpframe = np.hstack((tmpframe, matrix_data))

tmpframe = np.delete(tmpframe, 0)  # deletes garbage at beginning
tmpframe = np.reshape(np.append(tmpframe, np.array([LEFT, RIGHT])), (1, -1))  # appends 0, 1 distinguishers

# data = [CH1, CH2, CH1, CH2], so can reshape into # of channels as columns to separate channels
# reshaping data
print("~~~~~~~~~~~~~~~~~~~~~~~~~~TMPFRAME~~~~~~~~~~~~~~~~~~~~~~")  # debugging prints
print("tmpframe:" + str(tmpframe[:, 0:100]))
left_channel = np.reshape(tmpframe[:, LEFT::CHANNELS], (1, -1))
right_channel = np.reshape(tmpframe[:, RIGHT::CHANNELS], (1, -1))
print("left_channel:" + str(left_channel[0:5, :]))
print("left channel shape: " + str(left_channel.shape))
print("right_channel:" + str(right_channel[0:5, :]))
print("right channel shape: " + str(right_channel.shape))
tmpframe = np.vstack((left_channel, right_channel))
print("tmpframe:" + str(tmpframe[0:10, :]))
print("dataframe shape: " + str(tmpframe.shape))
print("~~~~~~~~~~~~~~~~~~~~~~~~~~TMPFRAME OVER~~~~~~~~~~~~~~~~~~~~~~")
print("* done recording")
print(tmpframe)


stream.stop_stream()
stream.close()
p.terminate()

# outputs the recording to a wav file
wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()

plt.plot(tmpframe[LEFT, :], 'b-', tmpframe[RIGHT, :], 'r-')  # left is blue, right is red
plt.legend(["left", "right"])
plt.show()