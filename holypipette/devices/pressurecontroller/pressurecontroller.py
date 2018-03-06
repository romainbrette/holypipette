'''
A general pressure controller class
'''
from time import time

all = ['PressureController']

class PressureController(object):
    def __init__(self):
        pass

    def measure(self, port = 0):
        '''
        Measures the instantaneous pressure, on designated port.
        '''
        pass

    def set_pressure(self, pressure, port = 0):
        '''
        Sets the pressure, on designated port.
        '''
        pass

    def ramp(self,amplitude = -230., duration = 1.5, port = 0):
        '''
        Makes a ramp of pressure
        '''
        t0 = time()
        t = t0
        while t-t0<duration:
            self.set_pressure(amplitude*(t-t0)/duration,port)
            t = time()
        self.set_pressure(0., port)
