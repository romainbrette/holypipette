'''
A general pressure controller class
'''
from time import time

from holypipette.controller.base import TaskController

all = ['PressureController',  'FakePressureController']


class PressureController(TaskController):
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


class FakePressureController(PressureController):
    def __init__(self):
        super(FakePressureController, self).__init__()
        self.pressure = 0

    def measure(self, port=0):
        '''
        Measures the instantaneous pressure, on designated port.
        '''
        return self.pressure

    def set_pressure(self, pressure, port=0):
        '''
        Sets the pressure, on designated port.
        '''
        self.debug('Pressure set to: {}'.format(pressure))
        self.pressure = pressure
