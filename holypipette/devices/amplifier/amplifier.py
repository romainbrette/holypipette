from holypipette.controller.base import TaskController

all = ['Amplifier',  'FakeAmplifier']


class Amplifier(TaskController):
    """
    Base class for amplifiers.
    """

    def start_patch(self, pulse_amplitude=1e-2,
                    pulse_frequency=1e-2):  # Not clear what the units are for frequency
        '''
        Initialize the patch clamp procedure (in bath)
        '''
        pass

    def resistance(self):
        '''
        Returns resistance
        '''
        pass

    def stop_patch(self):
        '''
        Stops patch clamp procedure
        '''
        pass

    def voltage_clamp(self):
        '''
        Switch to voltage clamp mode
        '''
        pass

    def current_clamp(self):
        '''
        Switch to current clamp mode
        '''
        pass

    def set_holding(self, value):  # Voltage-clamp value
        '''
        Set voltage clamp value

        Parameters
        ----------
        value : float
            Voltage clamp value
        '''
        pass

    def zap(self):
        '''
        "Zap" the cell to break the membrane
        '''
        pass

    def set_zap_duration(self, duration):
        '''
        Set the duration for the `zap`.
        Parameters
        ----------
        duration : float
            Duration of the zap in seconds.
        '''
        pass

    def auto_pipette_offset(self):
        '''
        Trigger the feature to automatically zero the membrane current.
        '''
        pass

    def close(self):
        '''
        Shut down the connection to th eamplifier.
        '''
        pass

class FakeAmplifier(Amplifier):
    """
    "Fake" amplifier that only notes down changes/commands
    """

    def __init__(self):
        self._mode = 'voltage clamp'
        self._resistance = 10*1e6
        self._holding = -70  # holding potential for voltage clamp, holding current for current clamp
        self._patching = False
        self._zap_duration = 0.1

    def start_patch(self, pulse_amplitude=1e-2,
                    pulse_frequency=1e-2):  # Not clear what the units are for frequency
        '''
        Initialize the patch clamp procedure (in bath)
        '''
        self._patching = True
        self.debug('Starting patch')

    def resistance(self):
        '''
        Returns resistance
        '''
        return self._resistance

    def stop_patch(self):
        '''
        Stops patch clamp procedure
        '''
        self._patching = False
        self.debug('Stopping patch')

    def voltage_clamp(self):
        '''
        Switch to voltage clamp mode
        '''
        self.mode = 'voltage clamp'
        self.debug('Switching to voltage clamp mode')

    def current_clamp(self):
        '''
        Switch to current clamp mode
        '''
        self.mode = 'current clamp'
        self.debug('Switching to current clamp mode')

    def set_holding(self, value):
        '''
        Set holding voltage or current

        Parameters
        ----------
        value : float
            Holding voltage or current
        '''
        self._holding = value
        if self.mode == 'voltage clamp':
            holding_what = 'potential'
            unit = 'mV'
        else:
            holding_what = 'current'
            unit = 'pA'
        self.debug('Setting holding {} to {:.2f}{}'.format(holding_what,
                                                           value,
                                                           unit))

    def zap(self):
        '''
        "Zap" the cell to break the membrane
        '''
        self.debug('Zapping the cell')

    def set_zap_duration(self, duration):
        '''
        Set the duration for the `zap`.
        Parameters
        ----------
        duration : float
            Duration of the zap in seconds.
        '''
        self._zap_duration = duration
        self.debug('Setting zap duration to {:.0f}ms'.format(self._zap_duration*1000))

    def auto_pipette_offset(self):
        '''
        Trigger the feature to automatically zero the membrane current.
        '''
        self.debug('Triggering automatic pipette offset')

    def close(self):
        '''
        Shut down the connection to th eamplifier.
        '''
        self.debug('Shutting down the amplifier')


#TODO: How to best expose Multiclamp's acquire command?