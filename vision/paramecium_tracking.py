'''
These are functions to locate paramecium in an image
'''
from math import atan2
import cv2

__all__ = ["where_is_paramecium"]

def where_is_paramecium(frame): # Locate paramecium
    '''
    Locate paramecium in an image.

    Arguments
    ---------
    frame : the image

    Returns
    -------
    x, y : center position in screen
    '''
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