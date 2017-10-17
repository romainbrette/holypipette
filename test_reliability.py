'''
Tests the reliability of pattern matching.

Apparently precision is a pixel in x,y.
'''
from devices import *
from vision import *
from gui import *
import cv2
import time
from numpy import array,zeros

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

time.sleep(0.1)

xlist, ylist = zeros(10),zeros(10)
for i in range(10):
    image = camera.snap()
    x,y,c = templatematching(image, template)
    xlist[i]=x
    ylist[i]=y
    print x,y,c
    time.sleep(0.1)

print xlist.std(), ylist.std()
