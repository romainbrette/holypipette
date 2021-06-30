from .base import TaskController
from time import sleep
from scipy.optimize import golden, minimize_scalar
from numpy import array,arange
import numpy as np
import warnings
import os
from holypipette.utils.filelock import FileLock

#### Copied and simplified from clampy
def load_data(filename):
    '''
    Loads a text data file, with the following conventions:
    - header gives variable names (separated by spaces)
    - one column = one variable
    Returns a dictionary of signals
    '''
    _, ext = os.path.splitext(filename)

    f = open(filename, 'r')
    variables = f.readline().split()
    f.close()

    # Load signals
    signals = {}
    M = np.loadtxt(filename, skiprows=1, unpack=True)
    if len(M.shape) == 1:
        M = M.reshape((1,len(M)))
    for name, value in zip(variables, M):
        signals[name] = value

    return signals


class ParameciumDeviceController(TaskController):
    def __init__(self, calibrated_unit, microscope,
                 calibrated_stage, camera, config):
        super(ParameciumDeviceController, self).__init__()
        self.config = config
        self.calibrated_unit = calibrated_unit
        self.calibrated_stage = calibrated_stage
        self.microscope = microscope
        self.camera = camera

    def partial_withdraw(self):
        self.calibrated_unit.relative_move(self.config.withdraw_distance * self.calibrated_unit.up_direction[0], 0)

    def move_pipette_in(self):
        '''
        It is assumed that the pipette is at working level.
        '''
        # move out
        self.calibrated_unit.relative_move(self.config.short_withdraw_distance*self.calibrated_unit.up_direction[0],0)
        self.calibrated_unit.wait_until_still()
        # move down
        movement = np.array([0, 0, -(self.config.working_level-self.config.impalement_level)*self.microscope.up_direction])
        self.calibrated_unit.reference_relative_move(movement)
        self.calibrated_unit.wait_until_still()
        # move in
        self.calibrated_unit.relative_move(-self.config.short_withdraw_distance*self.calibrated_unit.up_direction[0],0)

    def electrophysiological_parameters(self):
        '''
        Reads from the oscilloscope and returns V0, R and Re
        '''
        # Load data
        filename = self.config.oscilloscope_filename
        while not os.path.exists(filename):
            sleep(0.01)  # wait for new data
        lock = FileLock(filename + ".lock")
        with lock:
            data = load_data(filename)
            os.remove(filename)

        V1, V2, I, t = data['V1'], data['V2'], data['Ic2'], data['t']
        dt = t[1]-t[0]

        # Calculate stimulus characteristics
        threshold = 1e-12
        I0 = np.mean(I[np.abs(I)>threshold])
        T0 = (np.abs(I)>threshold).nonzero()[0][0]*dt
        T1 = (np.abs(I)>threshold).sum()*dt

        # Calculate offset and resistance
        V0 = np.mean(V1[:int(T0 / dt)])  # calculated on initial pause
        Vpeak = np.mean(V1[int((T0 + 2 * T1 / 3.) / dt):int((T0 + T1) / dt)])  # calculated on last third of the pulse
        R1 = (Vpeak - V0) / I0

        # Calculate electrode resistance
        V02 = np.mean(V2[:int(T0 / dt)])  # calculated on initial pause
        Vpeak = np.mean(V2[int((T0 + 2 * T1 / 3.) / dt):int((T0 + T1) / dt)])  # calculated on last third of the pulse
        R2 = ((Vpeak - V02) / I0)

        if R2>R1:
            R, Re = R1, R2-R1
        else:
            R, Re = R2, R1-R2

        return V0, R, Re

    def move_pipette_until_drop(self):
        '''
        Moves pipette down until Vm drops
        '''
        previous_V0, previous_R, previous_Re = self.electrophysiological_parameters()

        nsteps = int((self.config.working_level-self.config.impalement_level)/self.config.impalement_step)
        step_movement = np.array([0, 0, -self.config.impalement_step * self.microscope.up_direction])
        success = False
        for _ in range(nsteps):
            # Move down one step
            self.calibrated_unit.reference_relative_move(step_movement)
            self.calibrated_unit.wait_until_still()
            # Check oscilloscope
            V0, R, Re = self.electrophysiological_parameters()
            self.info('V = {} mV'.format(V0*1000))
            if V0-previous_V0<-.1: # 10 mV drop
                success = True
                break
            previous_V0, previous_R, previous_Re = V0, R, Re
            self.sleep(self.config.pause_between_steps)

        if success:
            self.info('Successful impalement')
        else:
            self.info('Impalement failed')

    def autocenter(self):
        '''
        Finds the center of the device.
        '''
        # Assume we are in the lighted region
        I0 = self.camera.snap().mean()
        self.calibrated_stage.save_state()

        ## Move the stage left and right

        # Move until luminance drops by 50%
        n = 0
        I = I0
        while (I>.5*I0) and (n<30):
            self.calibrated_stage.relative_move(500., axis=0)
            self.calibrated_stage.wait_until_still()
            I = self.camera.snap().mean()
            n += 1
        x0 = self.calibrated_stage.position(axis=0)
        self.calibrated_stage.recover_state()
        if n==30: # fail
            self.info('Autocenter failed')
            return

        n = 0
        I = I0
        while (I > .5 * I0) and (n < 30):
            self.calibrated_stage.relative_move(-500., axis=0)
            self.calibrated_stage.wait_until_still()
            I = self.camera.snap().mean()
            n += 1
        x1 = self.calibrated_stage.position(axis=0)
        self.calibrated_stage.recover_state()
        if n == 30:  # fail
            self.info('Autocenter failed')
            return

        # Place at midpoint
        x = .5*(x0+x1)
        self.calibrated_stage.absolute_move(x,axis=0)
        self.calibrated_stage.wait_until_still()

        ## Move the stage up and down
        n = 0
        I = I0
        while (I>.5*I0) and (n<30):
            self.calibrated_stage.relative_move(500., axis=1)
            self.calibrated_stage.wait_until_still()
            I = self.camera.snap().mean()
            n += 1
        y0 = self.calibrated_stage.position(axis=1)
        self.calibrated_stage.recover_state()
        if n==30: # fail
            self.info('Autocenter failed')
            return

        n = 0
        I = I0
        while (I > .5 * I0) and (n < 30):
            self.calibrated_stage.relative_move(-500., axis=1)
            self.calibrated_stage.wait_until_still()
            I = self.camera.snap().mean()
            n += 1
        y1 = self.calibrated_stage.position(axis=1)
        self.calibrated_stage.recover_state()
        if n == 30:  # fail
            self.info('Autocenter failed')
            return

        # Place at midpoint
        y = .5*(y0+y1)
        self.calibrated_stage.absolute_move(y,axis=1)
        self.calibrated_stage.wait_until_still()
        self.info('Autocenter succeeded')
