'''
Elveflow OB1 microfluidic flow control system

Running this program calibrates the pressure controller.
'''
from __future__ import print_function
from __future__ import absolute_import
import os
import sys
from ctypes import *
import warnings
from .pressurecontroller import *

# We add both versions to the path, adding a non-existing directory does not do any harm...
sys.path.append(os.path.expanduser(r'~\Elveflow SDK V3_01_11\python_64').encode('utf-8'))
sys.path.append(os.path.expanduser(r'~\Elveflow SDK V3_01_04\python_64').encode('utf-8'))

try:
    from Elveflow64 import *
except ImportError:
    warnings.warn('Cannot use Elveflow OB1')

__all__ = ['OB1']

def _check_error(task, error):
    if error != 0:
        raise RuntimeError('{} failed with error code {}'.format(task, error))

class OB1(PressureController):
    def __init__(self, calibrate=False):
        super(OB1, self).__init__()
        self.instr_ID = c_int32()
        print('Instrument name and regulator types hardcoded in the python script'.encode('utf-8'))
        # see User guide to determine regulator type NI MAX to determine the instrument name
        error = OB1_Initialization('01C1690E'.encode('ascii'), 4, 0, 0, 0, byref(self.instr_ID))
        # all functions will return error code to help you to debug your code, for further information see user guide
        _check_error('Initialization', error)

        # add one analog flow sensor
        error = OB1_Add_Sens(self.instr_ID, 1, 8, 0, 1) # should be 8 not 5, but doesn't work
        _check_error('Adding analog flow sensor', error)

        calib_path = os.path.expanduser(r'~\ob1_calibration.txt')
        self.calib = (c_double * 1000)()
        if calibrate:
            print ('Starting calibration')
            OB1_Calib(self.instr_ID.value, self.calib, 1000)
            error = Elveflow_Calibration_Save(calib_path.encode('ascii'), byref(self.calib), 1000)
            print ('Calibration finished')
            print ('Calibration saved in file %s' % calib_path.encode('ascii'))
        else:
            if not os.path.isfile(calib_path):
                raise IOError('Calibration file "{}" does not exist'.format(calib_path))
            error = Elveflow_Calibration_Load(calib_path.encode('ascii'), byref(self.calib), 1000)
            _check_error('Loading calibration file', error)

    def measure(self, port=0):
        '''
        Measures the instantaneous pressure, on designated port.
        '''
        set_channel = c_int32(port)  # convert to c_int32
        get_pressure = c_double()
        error =  OB1_Get_Sens_Data(self.instr_ID.value, set_channel, 1, byref(get_pressure))  # Acquire_data =1 -> Read all the analog value
        _check_error('Getting data from flow sensor', error)
        return get_pressure.value

    def set_pressure(self, pressure, port=0):
        '''
        Sets the pressure, on designated port.
        '''
        set_channel = c_int32(port)  # convert to c_int32
        set_pressure = c_double(pressure)  # convert to c_double
        error = OB1_Set_Press(self.instr_ID.value, set_channel, set_pressure, byref(self.calib), 1000)
        _check_error('Setting pressure', error)
        super(OB1, self).set_pressure(pressure, port=port)

if __name__ == '__main__':
    ob1 = OB1(calibrate = True)
