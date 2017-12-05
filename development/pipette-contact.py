'''
Detects contact of pipette with water
'''
from vision.paramecium_tracking import *
import cv2
from matplotlib import pyplot as plt
from numpy import *
import imageio
import collections

path='/Users/Romain/Desktop/'
cap = imageio.get_reader(path+'electrode-in-water.mp4')

cv2.namedWindow('camera')

i=0

pixel_per_um = 0.5

while 1:
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

    try:
        frame = cap.get_data(i)
        #frame = cap.get_next_data()
        i += 1
    except (IndexError, RuntimeError):
        i = 0

    height, width = frame.shape[:2]
    #cv2.circle(frame, (width/2+30, height/2+50), 30, (0, 0, 255), 2)

    x = width/2
    y = height/2+20
    size = int(30/pixel_per_um) # 30 um around tip
    framelet = frame[y:y+size,x:x+size,:]

    ret, thresh = cv2.threshold(framelet, 127, 255, cv2.THRESH_BINARY)
    black_area = sum(thresh == 0)

    if i == 1:
        init_area = black_area
    else:
        increase = black_area-init_area
        print increase
        if increase>25 / pixel_per_um**2: # 5 x 5 um
            print "contact"
            break

    cv2.imshow('camera', thresh)
