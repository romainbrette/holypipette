'''
Tests the reliability of pattern matching.
Apparently precision is a pixel in x,y.

TODO: same thing, but with a photo stack
'''
from holypipette.devices import *
from holypipette.vision import *
import time
from numpy import zeros

if True:
    camera = Lumenera()
else:
    camera = Hamamatsu()

first_image = camera.snap()
time.sleep(2)

template = crop_center(camera.snap())
pipette_position = pipette_cardinal(template)
template = crop_cardinal(template, pipette_position)
print pipette_position

# Error margins for position estimation
xmargin = template.shape[1] / 4
ymargin = template.shape[0] / 4
print xmargin,ymargin

time.sleep(0.1)

image = camera.snap()
x0,y0,c = templatematching(image, template)
print x0,y0,c

image = image[y0-ymargin:y0+template.shape[0]+ymargin, x0-xmargin:x0+template.shape[1]+xmargin]
t1 = time.time()
for _ in range(11):
    x, y, c = templatematching(image, template)
print x+x0-xmargin,y+y0-ymargin,c
t2 = time.time()
print t2-t1

xlist, ylist = zeros(10),zeros(10)
for i in range(10):
    image = camera.snap()
    x,y,c = templatematching(image, template)
    xlist[i]=x
    ylist[i]=y
    print x,y,c
    time.sleep(0.1)

print xlist.std(), ylist.std()
