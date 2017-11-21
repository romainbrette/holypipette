'''
These are functions to locate paramecium in an image
'''
from math import atan2
import cv2

__all__ = ["where_is_paramecium"]

def where_is_paramecium(frame, pixel_per_um = 5., return_angle = False, previous_x = None, previous_y = None): # Locate paramecium
    '''
    Locate paramecium in an image.

    Arguments
    ---------
    frame : the image
    pixel_per_um : number of pixels per um
    return_angle : if True, return the angle of the cell
    previous_x : previous x position of the cell
    previous_y : previous y position of the cell

    Returns
    -------
    x, y (, angle) : position on screen and angle
    '''
    height, width = frame.shape[:2]
    ratio = width/256
    resized = cv2.resize(frame, (width/ratio, height/ratio))
    gauss = cv2.GaussianBlur(resized, (9, 9), 0)
    canny = cv2.Canny(gauss, gauss.shape[0]/8, gauss.shape[0]/8)
    ret, thresh = cv2.threshold(canny, 127, 255, 0)
    ret = cv2.findContours(thresh, 1, 2)
    contours, hierarchy = ret[-2], ret[-1] # for compatibility with opencv2 and 3
    distmin = 200*pixel_per_um/ratio # 200 um max distance over 1 frame
    if previous_x is None:
        previous_x = width / 2
        previous_y = height / 2
    previous_x = previous_x/ratio
    previous_y = previous_y/ratio
    found = False
    for cnt in contours:
        try:
            M = cv2.moments(cnt)
            if (cv2.arcLength(cnt, True) > 35*pixel_per_um) & bool(M['m00']):
                (x, y), radius = cv2.minEnclosingCircle(cnt)
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
                u20 = int(M['m20']/M['m00'] - cx**2)
                u02 = int(M['m02'] / M['m00'] - cy ** 2)
                u11 = int(M['m11'] / M['m00'] - cx * cy)
                theta = atan2((u20-u02), 2*u11)
                radius = int(radius)
                dist = ((x - previous_x) ** 2 + (y - previous_y) ** 2) ** 0.5
                if (radius < 20*pixel_per_um) & (radius > 10*pixel_per_um) & (dist<distmin):
                    distmin=dist
                    xmin, ymin =x, y
                    angle = theta
                    found = True
        except cv2.error:
            pass
    if found:
        if return_angle:
            return xmin * ratio, ymin * ratio, angle
        else:
            return xmin*ratio,ymin*ratio
    else:
        if return_angle:
            return None,None,None
        else:
            return None, None
