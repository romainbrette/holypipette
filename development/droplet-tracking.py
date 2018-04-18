'''
Tracking Paramecium in a droplet (x4) (works)
and waiting for Paramecium near pipette (works)

TODO:
- check using a binary mask how intensity changes on a ring around the droplet edge
- track with pipette?
'''
from holypipette.vision import *
import cv2
from numpy import *
import imageio
import collections

path='/Users/Romain/Desktop/'
cap = imageio.get_reader(path+'droplet-nice.mp4')
#cap = imageio.get_reader(path+'electrode-in-water.mp4')
#cap = imageio.get_reader(path+'paramecium-capture.mp4')

cv2.namedWindow('camera')

frame = cap.get_data(0)
height, width = frame.shape[:2]
xd, yd, rd = where_is_droplet(frame, pixel_per_um=0.5, xc=width * 3 / 4, yc=height / 2)
i=1

position_history = collections.deque(maxlen = 50)

while 1:
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

    try:
        frame = cap.get_data(i)
        #frame = cap.get_next_data()
        i += 1
    except (IndexError, RuntimeError):
        i = 0

    #cv2.circle(frame, (width*3/4, height/2), 30, (0, 0, 255), 2)

    x,y,img = where_is_paramecium(frame, pixel_per_um = 0.5, background = None, debug = True,
                                  previous_x = xd, previous_y = yd, max_dist = rd-50/0.5)

    if xd is not None:
        cv2.circle(frame, (int(xd),int(yd)), int(rd), (0, 255, 0), 2)

    if x is not None:
        cv2.circle(frame, (int(x), int(y)), 30, (0, 255, 0), 2)
        # Calculate variance of position
        if len(position_history)==position_history.maxlen:
            xpos,ypos = zip(*position_history)
            movement = (var(xpos)+var(ypos))**.5
            if movement<1: # 1 pixel
                print "Paramecium has stopped!"
        position_history.append((x,y))

    cv2.imshow('camera', frame)
