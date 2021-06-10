'''
Tests motor commands.
Issues a variety of commands and check whether the pipette moves.

TO BE WRITTEN
'''
from __future__ import print_function
from holypipette.devices import *
from holypipette.vision import *
import time
from numpy import zeros
from pylab import *
from numpy import *
import cv2
from setup_script import *

#camera = Lumenera()
camera.set_exposure(5.)
#controller = LuigsNeumann_SM10(stepmoves=True)
#stage = ManipulatorUnit(controller, [7, 8])
axis = 1
wait_time = .5
step = 1.
nsteps = 10

# Discard first image
first_image = camera.snap()
time.sleep(2)

# Take a photo of the pipette or coverslip
template = crop_center(camera.snap(), ratio=32)
cv2.imwrite('template.jpg', template)
time.sleep(wait_time)

image = camera.snap()
x0, y0, _ = templatematching(image, template)
print(x0,y0)
u0 = stage.position()

distance = [0.]

for i in range(nsteps):
    print('move',i+1)
    stage.relative_move(step, axis)  # there could be a keyword blocking = True
    stage.wait_until_still(axis)
    time.sleep(wait_time)
    image = camera.snap()
    x, y, _ = templatematching(image, template)
    distance.append(((x-x0)**2 + (y-y0)**2)**.5)
    cv2.imwrite('test{}.jpg'.format(i), image)

stage.absolute_move(u0)

distance = array(distance)
slope = distance[-1]/(nsteps*step)

print('Mean error: {} pixel'.format(std(distance-slope*arange(nsteps+1)*step)))

plot(distance,'k')
plot(slope*arange(nsteps+1)*step,'r--')
show()
