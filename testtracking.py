'''
Test Paramecium tracking
'''
from devices import *
from vision import *
from gui import *
import cv2
import time
from numpy import array
from math import atan2

def moveto(x, y):
    xs = x-camera.width/2
    ys = y-camera.height/2
    #print xs, ys
    calibrated_stage.reference_move(calibrated_stage.reference_position()-array([xs, ys, 0]))

def where_is_paramecium(frame): # Locate paramecium
    height, width = frame.shape[:2]
    ratio = width/256
    resized = cv2.resize(frame, (width/ratio, height/ratio))
    gauss = cv2.GaussianBlur(resized, (9, 9), 0)
    canny = cv2.Canny(gauss, gauss.shape[0]/8, gauss.shape[0]/8)
    ret, thresh = cv2.threshold(canny, 127, 255, 0)
    ret = cv2.findContours(thresh, 1, 2)
    contours, hierarchy = ret[-2], ret[-1] # for compatibility with opencv2 and 3
    distmin = 1e6
    for cnt in contours:
        try:
            M = cv2.moments(cnt)
            if (cv2.arcLength(cnt, True) > 90) & bool(M['m00']):
                (x, y), radius = cv2.minEnclosingCircle(cnt)
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
                u20 = int(M['m20']/M['m00'] - cx**2)
                u02 = int(M['m02'] / M['m00'] - cy ** 2)
                u11 = int(M['m11'] / M['m00'] - cx * cy)
                theta = atan2((u20-u02), 2*u11)/2
                radius = int(radius)
                dist = ((x - width/2) ** 2 + (y - height/2) ** 2) ** 0.5
                if (radius < 55) & (radius > 25) & (dist<distmin):
                    distmin=dist
                    xmin, ymin =x, y
                    angle = theta # not used here
        except cv2.error:
            pass
    if distmin<1e5:
        return xmin*ratio,ymin*ratio
    else:
        return None,None

if False:
    camera = Lumenera()
    controller = LuigsNeumann_SM10(stepmoves=False)
    stage = ManipulatorUnit(controller,[7,8])
    microscope = Microscope(controller,9)
else:
    camera = Hamamatsu()
    controller = LuigsNeumann_SM5(name='COM3', stepmoves=False)
    stage = ManipulatorUnit(controller,[7,8])
    microscope = Leica()

video = LiveFeed(camera)
calibrated_stage = CalibratedStage(stage, None, microscope, camera=camera)

try:

    # Calibration
    cv2.waitKey(0)
    u0_stage = stage.position()
    z0 = microscope.position()

    t1 = time.time()
    calibrated_stage.calibrate()
    t2 = time.time()
    print "Calibration took",t2-t1,"s"
    print calibrated_stage.M, calibrated_stage.r0

    # Tracking
    cv2.waitKey(0)

    while 1:
        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

        frame = camera.snap()
        x,y = where_is_paramecium(frame)
        print x,y
        if x is not None:
            moveto(x,y)

finally:
    microscope.absolute_move(z0)
    stage.absolute_move(u0_stage)
    video.stop()
