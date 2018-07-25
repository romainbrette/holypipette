Pressure control
================

Holy Pipette can control a pressure controller.
Classes inherit the ``PressureController`` class, which implements
three methods. Currently only Elveflow's ``OB1`` controller is implemented.

Example::

    controller = OB1()
    controller.set_pressure(25, port = 0)
    pressure = controller.measure(port = 0)
    controller.ramp(amplitude = -100., duration = 1., port = 0)

Pressure is mBar.

Fake pressure controller
------------------------
For development purposes, a ``FakePressureController`` is implemented.
It behaves as a pressure controller, except it is not connected to an actual device.
