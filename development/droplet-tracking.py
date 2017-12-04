'''
Tracking Paramecium in a droplet (x4) (doesn't work)
and waiting for Paramecium near pipette (works)
'''
from vision.paramecium_tracking import *
import cv2
from matplotlib import pyplot as plt
from numpy import *
import imageio

path='/Users/Romain/Desktop/'
cap = imageio.get_reader(path+'droplet-nice.mp4')
#cap = imageio.get_reader(path+'paramecium-capture.mp4')

cv2.namedWindow('camera')

i=0
#firstframes = []
mean_frame = zeros(cap.get_data(i).shape)

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
    #cv2.circle(frame, (width*3/4, height/2), 30, (0, 0, 255), 2)

    if i<=50: # Make a background image
        #firstframes.append(frame[:2])
        mean_frame+=frame
    if i==50:
        mean_frame=mean_frame/50

    if i>50:
        x,y,img = where_is_paramecium(frame, pixel_per_um = 0.5, background = None, debug = True,
                                      previous_x = None, previous_y = None)
                                      #previous_x = width*3/4, previous_y = height/2) # x4

        if x is not None:
            cv2.circle(frame, (int(x), int(y)), 30, (0, 255, 0), 2)

        cv2.imshow('camera', frame)
