### This file is for debugging the output of the of the teensy/arduino only. It does not do anything w.r.t. T4Train.



import serial
import sys
import numpy as np
import glob
#import matplotlib.pyplot as plt

import time
def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.usb*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
#     for port in ports:
#         try:
            
#             s = serial.Serial(port)
#             s.close()
#             result.append(port)
#         except (OSError, serial.SerialException):
#             pass
    return ports



class FPSTracker:
    def __init__(self, alpha=0.1):
        ''' smaller alpha = stronger smoothing '''
        self.alpha = alpha
        self.prev = None
        self.delta = None

    def tick(self):
        ''' Tick the tracker; call this at a fixed period.

        Calling this method is optional.
        Calling this decays the FPS value if updates stop. '''

        now = time.time()
        if self.prev is not None and self.delta is not None:
            if now - self.prev < self.delta:
                # update happened recently, ignore this tick
                return
            newdelta = now - self.prev
            self.delta += self.alpha * (newdelta - self.delta)

    def update(self):
        ''' Update the tracker. Call this on every event. '''

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


# s = serial.Serial(serial_ports()[0])
s = serial.Serial('/dev/ttyS0') 

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
        b = s.read(1) # read byte from serial
        if not b:
            raise EOFError()
        res += b
        if res.endswith(b'\xde\xad\xbe\xef'): # when the frame is complete
            break
    return res

fps = FPSTracker()

numBytes = 3004 # number of bytes to read at a time from stream

while 1:
    discarded = resync()
    arr = np.frombuffer(readall(s, numBytes), dtype='uint16')
    print('\t'.join(map(str, arr)))
    sys.stdout.flush()
    fps.update()
    sys.stderr.write("FPS: %.2f, arrlen=%d, discard=%d           \r" % (fps.fps(), len(arr), len(discarded)))
    sys.stderr.flush()

