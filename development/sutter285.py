# Sutter : A python class for using the Sutter MP-285 positioner
# Adapted from Jonny Saunders
# Docs
# https://www.sutter.com/SOFTWARE/USBv3.pdf
# Check also https://github.com/dtnzj/Sutter-Driver/blob/master/sutter.py
# Manual: https://www.sutter.com/manuals/MP-285_OpMan_ROE_BasicOp.pdf
# ACQ4: https://github.com/acq4/acq4/tree/develop/acq4/devices/SutterMP285

import serial
import struct
import time
from datetime import datetime
import sys
import numpy as np
import os
import csv
from threading import Thread


class Sutter(object):
    connected   = None
    manipulator = None
    position    = None
    stepmult    = 16
    ser         = None
    log         = None
    verbose     = None
    threaded    = None
    log_fields  = ['event', 'position', 'timestamp']

    def __init__(self,port="/dev/tty.usbserial", timeout=5, logfile = None, verbose = False, threaded=False):
        self.verbose = verbose
        self.threaded = threaded
        try:
            # establish serial connection
            self.ser = serial.Serial(port=port,baudrate=128000, # normally 128000
                bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE, timeout=timeout)
            self.connected = 1

            if self.verbose:
                print(self.ser)

        except serial.SerialException:
            print('No connection to Sutter MP-285 could be established!')
            sys.exit(1)

        self.get_position()

    def __del__(self):
        self.ser.close()
        print('Connection to Sutter MP-285 closed')

    def get_position(self):
        self.ser.write(b'C') # not sure it's the right way; probably ok
        #msg = self.ser.readline()
        msg = self.ser.read(14)
        print(msg)

        # msg will be Dxxxxyyyyzzzz\r, where D is the device
        # so want 1:13 for position
        self.position = np.array(struct.unpack('lll', msg[1:13])) / self.stepmult

        if self.verbose:
            print("{} - Current position: X = {}, Y = {}, Z = {}".format(self.timestamp(), self.position[0],
                                                                         self.position[1], self.position[2]))

        # log
        with open(self.log, 'ab') as logf:
            writer = csv.writer(logf)
            writer.writerow(['get_pos', self.position, self.timestamp()])

    def set_position(self, pos):
        # pos is an x, y, z tuple in microns.
        # multiply by step multiplier to convert to stepper units, then pack into bytes
        pos_stepper = struct.pack('lll', int(pos[0] * self.stepmult),
                                         int(pos[1] * self.stepmult),
                                         int(pos[2] * self.stepmult))
        self.ser.write('M'+pos_stepper)

        if self.verbose:
            print('{} - Moving to X = {}, Y = {}, Z = {}'.format(self.timestamp(), pos[0],
                                                                 pos[1], pos[2]))

        # log move
        with open(self.log, 'ab') as logf:
            writer = csv.writer(logf)
            writer.writerow(['set_pos', np.array(pos), self.timestamp()])

        # flush any latent carriage returns
        # (can be put in a new thread to avoid blocking)
        if self.threaded:
            # object will block for duration of timeout otherwise,
            # just writing this without testing, don't blame me if it don't work.
            Thread(target=self.ser.readline).start()
        else:
            moved = self.ser.readline()


    def get_active_manipulator(self):
        self.ser.write("K")
        msg = self.ser.readline()

        # manipulator number is first hex byte
        self.manipulator = ord(msg[0])

    def set_active_manipulator(self, manipulator):
        pass
        # not implementing now fkn sue me
        #manip_hex = struct.pack('1h', int(manipulator))


    def read_serial(self):
        # continue to read until carriage return
        # deprecated, but keeping around just in case someone else needs to extend
        message = []
        while True:
            input = self.ser.read()
            if input == '\r':
                break
            else:
                message.append(input.encode('hex'))
        return message


    def timestamp(self):
        return datetime.now().strftime("%m-%d-%H:%M:%S.%f")[:-3]



if __name__ == '__main__':
    m = Sutter(verbose=True)