from __future__ import print_function
import os, sys, ctypes, atexit, time, threading
import numpy as np

dll_path = r'C:\Users\inters\PycharmProjects\holypipette\holypipette\devices\manipulator'
UMP_LIB = ctypes.WinDLL(os.path.join(dll_path, 'ump.dll'))

LIBUMP_MAX_MANIPULATORS = 254
LIBUMP_MAX_LOG_LINE_LENGTH = 256
LIBUMP_DEF_TIMEOUT = 20
LIBUMP_DEF_BCAST_ADDRESS = "169.254.255.255"
LIBUMP_DEF_GROUP = 0
LIBUMP_MAX_MESSAGE_SIZE = 1502
LIBUMP_TIMEOUT = -3


def axis_to_devid(axis):
    dev = (axis/3) + 1
    axis = (axis%3) - 1
    return (dev,axis)

class sockaddr_in(ctypes.Structure):
    _fields_ = [
        ("family", ctypes.c_short),
        ("port", ctypes.c_ushort),
        ("in_addr", ctypes.c_byte * 4),
        ("zero", ctypes.c_byte * 8),
    ]

log_func_ptr = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_char), ctypes.POINTER(ctypes.c_char))

class ump_positions(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("z", ctypes.c_int),
        ("w", ctypes.c_int),
        ("updated", ctypes.c_ulong),
    ]

UMP_LIB.ump_get_version.restype = ctypes.c_char_p
UMP_VERSION = UMP_LIB.ump_get_version()

class ump_state(ctypes.Structure):
    _fields_ = [
        ("last_received_time", ctypes.c_ulong),
        ("socket", ctypes.c_longlong),
        ("own_id", ctypes.c_int),
        ("message_id", ctypes.c_int),
        ("last_device_sent", ctypes.c_int),
        ("last_device_received", ctypes.c_int),
        ("retransmit_count", ctypes.c_int),
        ("refresh_time_limit", ctypes.c_int),
        ("last_error", ctypes.c_int),
        ("last_os_errno", ctypes.c_int),
        ("timeout", ctypes.c_int),
        ("udp_port", ctypes.c_int),
        ("last_status", ctypes.c_int * LIBUMP_MAX_MANIPULATORS),
        ("drive_status", ctypes.c_int * LIBUMP_MAX_MANIPULATORS),
        ("drive_status_id", ctypes.c_ushort * LIBUMP_MAX_MANIPULATORS),
        ("addresses", sockaddr_in * LIBUMP_MAX_MANIPULATORS),
        ("cu_address", sockaddr_in),
        ("last_positions", ump_positions * LIBUMP_MAX_MANIPULATORS),
        ("laddr", sockaddr_in),
        ("raddr", sockaddr_in),
        ("errorstr_buffer", ctypes.c_char * LIBUMP_MAX_LOG_LINE_LENGTH),
        ("verbose", ctypes.c_int),
        ("log_func_ptr", log_func_ptr),
        ("log_print_arg", ctypes.c_void_p),
    ]

class UMPError(Exception):
    def __init__(self, msg, errno, oserrno):
        Exception.__init__(self, msg)
        self.errno = errno
        self.oserrno = oserrno


class UMP(object):
    _single = None
    @classmethod
    def get_ump(cls):
        if cls._single is None:
            cls._single = UMP()
        return cls._single

    def __init__(self, start_poller=True):
        self.lock = threading.RLock()
        if self._single is not None:
            raise Exception("Won't create another UMP object. Use get_ump() instead.")
        self._timeout = 200
        self.lib = UMP_LIB
        self.lib.ump_errorstr.restype = ctypes.c_char_p
        self.handle = None
        self.open()
        self._positions = np.frombuffer(self.handle.contents.last_positions,
                                        dtype=[('x', 'int32'), ('y', 'int32'), ('z', 'int32'), ('w', 'int32'),
                                               ('t', 'uint32')], count=LIBUMP_MAX_MANIPULATORS)
        self._status = np.frombuffer(self.handle.contents.last_status, dtype='int32', count=LIBUMP_MAX_MANIPULATORS)

        self._ump_has_axis_count = hasattr(self.lib, 'ump_get_axis_count_ext')
        self._axis_counts = {}

        self.poller = PollThread(self)
        if start_poller:
            self.poller.start()

        pos = self.position(axis=1)
        print("Testing 1: ", pos)

    def list_devices(self, max_id=16):
        devs = []
        with self.lock:
            old_timeout = self._timeout
            self.set_timeout(10)
            try:
                for i in range(min(max_id, LIBUMP_MAX_MANIPULATORS)):
                    try:
                        p = self.position(i)
                        devs.append(i)
                    except UMPError as ex:
                        if ex.errno in (-5, -6):  # device does not exist
                            continue
                        else:
                            raise
            finally:
                self.set_timeout(old_timeout)
        return devs

    def axis_count(self, dev):
        if not self._ump_has_axis_count:
            return 4
        c = self._axis_counts.get(dev, None)
        if c is None:
            c = self.call('get_axis_count_ext', dev)
            self._axis_counts[dev] = c
        return c

    def call(self, fn, *args):
        with self.lock:
            if self.handle is None:
                raise TypeError("UMP is not open.")
            rval = getattr(self.lib, 'ump_' + fn)(self.handle, *args)

            if rval < 0:
                err = self.lib.ump_last_error(self.handle)
                errstr = self.lib.ump_errorstr(err)
                if err == -1:
                    oserr = self.lib.ump_last_os_errno(self.handle)
                    raise UMPError("UMP OS Error %d: %s" % (oserr, os.strerror(oserr)), None, oserr)
                else:
                    raise UMPError("UMP Error %d: %s  From %s%r" % (err, errstr, fn, args), err, None)
            return rval

    def set_timeout(self, timeout):
        self._timeout = timeout
        self.call('set_timeout', timeout)

    def open(self, address=None):
        if address is None:
            address = LIBUMP_DEF_BCAST_ADDRESS
        if self.handle is not None:
            raise TypeError("UMP is already open.")
        addr = ctypes.create_string_buffer(address)
        ptr = self.lib.ump_open(addr, ctypes.c_uint(self._timeout), ctypes.c_int(LIBUMP_DEF_GROUP))
        if ptr <= 0:
            raise RuntimeError("Error connecting to UMP:", self.lib.ump_errorstr(ptr))
        self.handle = ctypes.pointer(ump_state.from_address(ptr))
        atexit.register(self.close)

    def close(self):
        with self.lock:
            self.lib.ump_close(self.handle)
            self.handle = None

    def position(self, axis, timeout=None):
        if timeout is None:
            timeout = self._timeout
        (dev, axis) = axis_to_devid(axis)
        xyzwe = ctypes.c_int(), ctypes.c_int(), ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        timeout = ctypes.c_int(timeout)
        r = self.call('get_positions_ext', ctypes.c_int(dev), timeout, *[ctypes.byref(x) for x in xyzwe])
        n_axes = self.axis_count(dev)
        return xyzwe[axis].value

    def absolute_move(self, x, axis, speed, simultaneous=True):
        (dev, axis) = axis_to_devid(axis)
        pos = self.position(dev=dev)
        pos[axis] = x
        pos = list(pos) + [0] * (4 - len(pos))
        mode = int(bool(simultaneous))  # all axes move simultaneously
        args = [ctypes.c_int(int(x)) for x in [dev] + pos + [speed, mode]]
        with self.lock:
            self.call('goto_position_ext', *args)
            self.handle.contents.last_status[dev] = 1  # mark this manipulator as busy

    def relative_move(self, x, axis, speed, simultaneous=True):
        (dev, axis) = axis_to_devid(axis)
        pos = self.position(dev=dev)
        pos[axis] = pos[axis] + x
        pos = list(pos) + [0] * (4 - len(pos))
        mode = int(bool(simultaneous))  # all axes move simultaneously
        args = [ctypes.c_int(int(x)) for x in [dev] + pos + [speed, mode]]
        with self.lock:
            self.call('goto_position_ext', *args)
            self.handle.contents.last_status[dev] = 1  # mark this manipulator as busy

    def wait_until_still(self):
        devids = self.list_devices()
        for dev in devids:
            status = self.call('get_status_ext', ctypes.c_int(dev))
            if self.lib.ump_is_busy_status(status) == 1:
                break
        while(bool(self.lib.ump_is_busy_status(status))):
            time.sleep(0.05)
            for dev in devids:
                status = self.call('get_status_ext', ctypes.c_int(dev))
                if self.lib.ump_is_busy_status(status) == 1:
                    break
            if not bool(self.lib.ump_is_busy_status(status)):
                break

    def stop_all(self):
        self.call('stop_all')

    def stop(self, axis):
        (dev, axis) = axis_to_devid(axis)
        self.call('stop_ext', ctypes.c_int(dev))

    def select(self, dev):
        self.call('cu_select_manipulator', dev)

    def set_active(self, dev, active):
        self.call('cu_set_active', dev, int(active))

    def recv(self):
        count = self.call('receive', 0)
        if count == 0:
            errstr = self.lib.ump_errorstr(LIBUMP_TIMEOUT)
            raise UMPError(errstr, LIBUMP_TIMEOUT, None)
        return self.handle.contents.last_device_received

    def recv_all(self):
        devs = set()
        with self.lock:
            old_timeout = self._timeout
            self.set_timeout(0)
            try:
                while True:
                    try:
                        d = self.recv()
                    except UMPError as exc:
                        if exc.errno == -3:
                            # timeout; no packets remaining
                            break
                    if d is None or d > 0:
                        devs.add(d)

            finally:
                self.set_timeout(old_timeout)

        return list(devs)

class PollThread(threading.Thread):
    def __init__(self, ump, callback=None, interval=0.03):
        self.ump = ump
        self.callbacks = {}
        self.interval = interval
        self.lock = threading.RLock()
        self._stop = False
        threading.Thread.__init__(self)
        self.daemon = True

    def start(self):
        self._stop = False
        threading.Thread.start(self)

    def stop(self):
        self._stop = True

    def add_callback(self, dev_id, callback):
        with self.lock:
            self.callbacks.setdefault(dev_id, []).append(callback)

    def remove_callback(self, dev_id, callback):
        with self.lock:
            self.callbacks[dev_id].remove(callback)

    def run(self):
        ump = self.ump
        last_pos = {}

        while True:
            try:
                if self._stop:
                    break
                ump.call('receive', 20)
                with self.lock:
                    callbacks = self.callbacks.copy()

                for dev_id, dev_callbacks in callbacks.items():
                    if len(callbacks) == 0:
                        continue
                    new_pos = ump.get_pos(dev_id, 0)
                    old_pos = last_pos.get(dev_id)
                    if new_pos != old_pos:
                        for cb in dev_callbacks:
                            cb(dev_id, new_pos, old_pos)

                time.sleep(self.interval)  # rate-limit updates
            except:
                print('Error in sensapex poll thread:')
                sys.excepthook(*sys.exc_info())
                time.sleep(1)

if __name__ == '__main__':
     ump = UMP.get_ump()
#     pos = ump.get_pos(dev = 1)
#     print("Testing 1: ", pos)
#     pos[0] -= 10000  # add 10 um to x axis
#     ump.goto_pos(dev = 1, pos = pos, speed = 10)
#     time.sleep(5)
#     pos = ump.get_pos(dev = 1)
#     print("Testing 2: ", pos)
