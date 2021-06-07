'''
Tests the reliability of stage calibration.
Plots x_estimated vs. x_stage.
'''
from holypipette.devices import *
from holypipette.vision import *
import time
from numpy import zeros
from __future__ import print_function
from pylab import *
from numpy import *

camera = Lumenera()
controller = LuigsNeumann_SM10(stepmoves=False)
stage = ManipulatorUnit(controller, [7, 8])
axis = 0
wait_time = .5
step = 5.
nsteps = 10

# Take a photo of the pipette or coverslip
template = crop_center(camera.snap(), ratio=64)
time.sleep(wait_time)

image = camera.snap()
x0, y0, _ = templatematching(image, template)
u0 = stage.position()


distance = []

for _ in range(nsteps):
    stage.relative_move(step, axis)  # there could be a keyword blocking = True
    stage.wait_until_still(axis)
    time.sleep(wait_time)
    image = camera.snap()
    x, y, _ = templatematching(image, template)
    distance.append(((x-x0)**2 + (y-y0)**2)**.5)

distance = array(distance)
slope = distance[-1]/(nsteps*step)

print('Mean error: {} µm'.format(std(distance-slope*arange(nsteps)*step)))

plot(distance,'k')
plot(slope*arange(nsteps)*step,'r--')
show()
