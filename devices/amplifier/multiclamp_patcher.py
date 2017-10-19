'''
Multiclamp patcher.

This is a class to control the amplifier for patch clamp approach.
'''
from multiclamp import *

__all__ = ['MulticlampPatcher']

class MulticlampPatcher(object):
    def __init__(self, amplifier):
        self.amp = amplifier # should be a MultiClampChannel object

    def start(self, pulse_amplitude=1e-2, pulse_frequency=1e-2): # Not clear what the units are for frequency
        '''
        Initialize the patch clamp procedure (in bath)
        '''
        # Set in voltage clamp
        self.amp.voltage_clamp()

        # Disable resistance metering (because of pulses)
        self.amp.switch_resistance_meter(False)

        # Disable pulses
        self.amp.switch_pulses(False)

        # Compensate pipette
        self.amp.auto_slow_compensation()
        self.amp.auto_fast_compensation()

        # Set pulse frequency and amplitude
        self.amp.set_pulses_amplitude(pulse_amplitude)
        self.amp.set_pulses_frequency(pulse_frequency)

        # Set zap duration
        self.amp.set_zap_duration(1)  # ms

        # Automatic offset
        self.amp.auto_pipette_offset()

        # Set holding potential
        self.amp.set_holding(0.)
        self.amp.switch_holding(True)

        # Enable resistance metering
        self.amp.switch_resistance_meter(True)

    def resistance(self):
        # Get resistance (assuming resistance metering is on)
        return self.amp.get_meter_value()

    def stop(self):
        # Disable resistance metering
        self.amp.switch_resistance_meter(False)
        # Disable holding
        self.amp.switch_holding(False)
        # Cancel current
        self.amp.null_current()