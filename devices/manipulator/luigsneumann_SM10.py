"""
Manipulator class for the Luigs and Neumann SM-10 manipulator controller.

Adapted from Michael Graupner's LandNSM5 class.

TODO: group commands
"""
from ..serialdevice import SerialDevice
from manipulator import Manipulator
import serial
import binascii
import time
import struct
import numpy as np

__all__ = ['LuigsNeumann_SM10']


def group_address(axes):
    '''
    Returns the address for a group of axes (list)
    '''
    all_axes = np.sum(2 ** (np.array(axes) - 1))
    # The group address is fixed at 9 bytes
    address = binascii.unhexlify('%.18x' % all_axes)
    return struct.unpack('9B', address)


class LuigsNeumann_SM10(SerialDevice,Manipulator):
    def __init__(self, name = None):
        # Note that the port name is arbitrary, it should be set or found out
        SerialDevice.__init__(self, name)
        Manipulator.__init__(self)

        # Open the serial port; 1 second time out
        self.port.baudrate = 115200
        self.port.bytesize = serial.EIGHTBITS
        self.port.parity=serial.PARITY_NONE
        self.port.stopbits=serial.STOPBITS_ONE
        self.port.timeout=1. #None # blocking

        self.port.open()

    def send_command(self, ID, data, nbytes_answer):
        '''
        Send a command to the controller
        '''
        high, low = self.CRC_16(data, len(data))

        # Create hex-string to be sent
        # <syn><ID><byte number>
        send = '16' + ID + '%0.2X' % len(data)

        # <data>
        # Loop over length of data to be sent
        for i in range(len(data)):
            send += '%0.2X' % data[i]
        # <CRC>
        send += '%0.2X%0.2X' % (high, low)
        # Convert hex string to bytes
        sendbytes = binascii.unhexlify(send)
        self.port.write(sendbytes)

        if nbytes_answer >= 0:
            # Expected response: <ACK><ID><byte number><data><CRC>
            # We just check the first two bytes
            expected = binascii.unhexlify('06' + ID)

            answer = self.port.read(nbytes_answer + 6)
            if answer[:len(expected)] != expected:
                msg = "Expected answer '%s', got '%s' " \
                      "instead" % (binascii.hexlify(expected),
                                   binascii.hexlify(answer[:len(expected)]))
                raise serial.SerialException(msg)
            # We should also check the CRC + the number of bytes
            # Do several reads; 3 bytes, n bytes, CRC
            return answer[4:4 + nbytes_answer]
        else:
            return None

    def position(self, axis):
        '''
        Current position along an axis.

        Parameters
        ----------
        axis : axis number (starting at 1)

        Returns
        -------
        The current position of the device axis in um.
        '''
        res = self.send_command('0101', [axis], 4)
        return struct.unpack('f', res)[0]

    def position2(self, axis):
        '''
        Current position along an axis, using the second counter.

        Parameters
        ----------
        axis : axis number (starting at 1)

        Returns
        -------
        The current position of the device axis in um.
        '''
        res = self.send_command('0131', [axis], 4)
        return struct.unpack('f', res)[0]

    def slow_speed(self, axis):
        '''
        Queries the slow speed setting for a given axis
        '''
        res = self.send_command('0190', [axis], 1)
        return struct.unpack('b', res)[0]

    def fast_speed(self, axis):
        '''
        Queries the fast speed setting for a given axis
        '''
        res = self.send_command('0143', [axis], 1)
        return struct.unpack('b', res)[0]

    def set_slow_speed(self, axis, speed):
        '''
        Sets the slow speed setting for a given axis
        '''
        self.send_command('018F', [axis, speed], 0)

    def set_fast_speed(self, axis, speed):
        '''
        Sets the fast speed setting for a given axis
        '''
        self.send_command('0144', [axis, speed], 0)

    def absolute_move(self, x, axis, fast=True):
        '''
        Moves the device axis to position x.

        Parameters
        ----------
        axis: axis number (starting at 1)
        x : target position in um.
        speed : optional speed in um/s.
        fast : True if fast move, False if slow move.
        '''
        self.absolute_move_group([x], [axis], fast=fast)

    def relative_move(self, x, axis, fast=True):
        '''
        Moves the device axis by relative amount x in um.

        Parameters
        ----------
        axis: axis number
        x : position shift in um.
        fast : True if fast move, False if slow move.
        '''
        self.relative_move_group([x], [axis], fast=fast)

    def position_group(self, axes):
        '''
        Current position along a group of axes.

        Parameters
        ----------
        axes : list of axis numbers

        Returns
        -------
        The current position of the device axis in um (vector).
        '''
        # First fill in zeros to make 4 axes
        axes4 = [0, 0, 0, 0]
        axes4[:len(axes)] = axes
        ret = struct.unpack('4b4f', self.send_command('A101', [0xA0] + axes4, 20))
        assert all(r == a for r, a in zip(ret[:3], axes))
        return np.array([ret[4:7]])

    def absolute_move_group(self, x, axes, fast=True):
        '''
        Moves the device group of axes to position x.

        Parameters
        ----------
        axes : list of axis numbers
        x : target position in um (vector or list)
        fast : True if fast move, False if slow move.
        '''
        ID = 'A048' if fast else 'A049'

        axes4 = [0, 0, 0, 0]
        axes4[:len(axes)] = axes
        pos4 = [0, 0, 0, 0]
        pos4[:len(x)] = x

        pos = [b for p in pos4 for b in bytearray(struct.pack('f', p))]

        # Send move command
        self.send_command(ID, [0xA0] + axes4 + pos, -1)

    def relative_move_group(self, x, axes, fast=True):
        '''
        Moves the device group of axes by relative amount x in um.

        Parameters
        ----------
        axes : list of axis numbers
        x : position shift in um (vector or list).
        fast : True if fast move, False if slow move.
        '''
        ID = 'A04A' if fast else 'A04B'

        axes4 = [0, 0, 0, 0]
        axes4[:len(axes)] = axes
        pos4 = [0, 0, 0, 0]
        pos4[:len(x)] = x

        pos = [b for p in pos4 for b in bytearray(struct.pack('f', p))]

        # Send move command
        self.send_command(ID, [0xA0] + axes4 + pos, -1)

    def single_step_trackball(self, axis, steps):
        '''
        Makes a number of single steps with the trackball command

        Parameters
        ----------
        axis : axis number
        steps : number of steps
        '''
        ID = '01E8'
        if steps < 0:
            steps += 256
        self.send_command(ID, [axis, steps], 0)

    def set_single_step_factor_trackball(self, axis, factor):
        '''
        Sets the single step factor with the trackball command

        Parameters
        ----------
        axis : axis number
        factor : single step factor (what is it ??)
        '''
        ID = '019F'
        if factor < 0:
            factor += 256
        data = (axis, factor)
        self.send_command(ID, data, 0)

    def single_step(self, axis, steps):
        '''
        Moves the given axis by a signed number of steps using the StepIncrement or StepDecrement command.
        Using a steps argument different from 1 (or -1) simply sends multiple
        StepIncrement/StepDecrement commands.
        Uses distance and velocity set by `set_single_step_distance` resp.
        `set_single_step_velocity`.
        '''
        if steps > 0:
            ID = '0140'
        else:
            ID = '0141'
        for _ in range(int(abs(steps))):
            self.send_command(ID, [axis], 0)
            time.sleep(0.02)

    def set_single_step_distance(self, axis, distance):
        '''
        Distance (in um) for `single_step`.
        '''
        if distance > 255:
            print('Step distance too long, setting distance at 255um')
            distance = 255
        ID = '044F'
        data = [axis] + list(bytearray(struct.pack('f', distance)))
        self.send_command(ID, data, 0)

    def set_single_step_velocity(self, axis, velocity):
        '''
        Velocity (units??) for `single_step`.
        '''
        ID = '0158'
        data = (axis, velocity)
        self.send_command(ID, data, 0)

    def stop(self, axis):
        """
        Stops current movements on one axis.
        """
        # Note that the "collection command" STOP (A0FF) only stops
        # a move started with "Procedure + ucVelocity"
        ID = '00FF'
        self.send_command(ID, [axis], 0)

    def zero(self, axes):
        """
        Sets the current position of the axes as the zero position.
        """
        # # collection command does not seem to work...
        # ID = 'A0F0'
        # address = group_address(axes)
        # self.send_command(ID, address, -1)
        ID = '00F0'
        for axis in axes:
            self.send_command(ID, [axis], 0)

    def zero2(self, axes):
        """
        Sets the current position of the axes as the zero position on
        the second counter.
        """
        # # collection command does not seem to work...
        # ID = 'A0F0'
        # address = group_address(axes)
        # self.send_command(ID, address, -1)
        ID = '0132'
        for axis in axes:
            self.send_command(ID, [axis, 02], 0)

    def go_to_zero(self, axes):
        """
        Moves axes to zero position.
        """
        ID = '0024'
        for axis in axes:
            self.send_command(ID, [axis], 0)

    def set_ramp_length(self, axis, length):
        """
        Sets the ramp length for the chosen axis

        Parameters
        ----------
        axis: axis number
        length: length between 0 and 16
        """
        self.send_command('003A', [axis, length], 0)

    def wait_until_still(self, axes = None):
        """
        Waits for the motors to stop.
        On SM10, commands of motors seem to block.
        """
        axes4 = [0, 0, 0, 0]
        axes4[:len(axes)] = axes
        data = [0xA0] + axes + [0]
        time.sleep(0.1)  # right after a motor command the motors are not moving yet
        ret = struct.unpack('20B', self.send_command('A120', data, 20))
        moving = [ret[6 + i*4] for i in range(len(axes))]
        is_moving = any(moving)
        while is_moving:
            time.sleep(0.05)
            ret = struct.unpack('20B', self.send_command('A120', data, 20))
            moving = [ret[6 + i * 4] for i in range(len(axes))]
            is_moving = any(moving)


if __name__ == '__main__':
    # Calculate the example group addresses from the documentation
    print(''.join(['%x' % a for a in group_address([1])]))
    print(''.join(['%x' % a for a in group_address([3, 6, 9, 12, 15, 18])]))
    print(''.join(['%x' % a for a in group_address([4, 5, 6, 7, 8, 9, 10, 11, 12])]))
    sm10 = LuigsNeumann_SM10('COM3')

    sm10.absolute_move(1000, 7)
    sm10.wait_until_still([7])
    sm10.set_single_step_factor_trackball(7, 2)
    sm10.set_single_step_factor_trackball(8, 2)
    # sm10.single_step(7, 1)
    # print sm10.position(7)
    # sm10.single_step(7, 1)
    # print sm10.position(7)
    # time.sleep(1)
    print sm10.position(8)
    sm10.single_step(8, 1)
    time.sleep(1)
    print sm10.position(8)
    sm10.single_step(8, -2)
    time.sleep(1)
    print sm10.position(8)