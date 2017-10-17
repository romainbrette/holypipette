'''
Tests the reliability of pattern matching
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

template = camera.snap()
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
