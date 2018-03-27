"""
Package defining `TaskController` classes. These classes are the interfaces
between the GUI and the classes that perform the actual tasks such as patching,
controlling the camera, etc. The key role of the `TaskController` classes is
to define the commands that it supports (e.g. patching, moving the manipulators,
etc.) and what should be done if such command is received.
"""
from base import *
from camera import *
from pipettes import *
from patch import *
