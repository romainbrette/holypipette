'''
These are functions to locate paramecium in an image

TODO: look for the closest in ellipse property space
'''
from math import atan2
import cv2
from numpy import zeros,uint8,pi, uint16, around

__all__ = ["where_is_paramecium", "where_is_droplet"]

def where_is_droplet(frame, pixel_per_um = 5., ratio = None,
                     xc = None, yc = None):
    '''
    Locate a droplet in an image.

    Arguments
    ---------
    frame : the image
    pixel_per_um : number of pixels per um
    ratio : decimating ratio (to make the image smaller)
    xc, yc : coordinate of a point inside the droplet

    Returns
    -------
    x, y, r : position and radius on screen
    '''

    # Resize
    height, width = frame.shape[:2]
    if ratio is None:
        ratio = width/256
    resized = cv2.resize(frame, (width/ratio, height/ratio))
    pixel_per_um = pixel_per_um/ratio

    # Filter
    blur_size = int(pixel_per_um*10)
    if blur_size % 2 == 0:
        blur_size+=1
    filtered=cv2.GaussianBlur(resized, (blur_size, blur_size), 0)

    # Find circles
    circles = cv2.HoughCircles(filtered[:,:,0], cv2.HOUGH_GRADIENT, 1, int(400*pixel_per_um),\
                param1 = int(50/pixel_per_um), param2 = 30, minRadius = int(200*pixel_per_um), maxRadius = int(1000*pixel_per_um))

    # Center
    if xc is None:
        xc = width/2
        yc = height/2

    # Choose one that encloses the center
    x,y,r = None,None,None
    if circles is not None:
        circles = uint16(around(circles))
        for j in circles[0, :]:
            xj,yj,rj = j[0]*ratio,j[1]*ratio,j[2]*ratio
            if ((xj-xc)**2 + (yj-yc)**2)<rj**2:
                x,y,r = xj,yj,rj

    return x,y,r


def where_is_paramecium(frame, pixel_per_um = 5., return_angle = False, previous_x = None, previous_y = None,
                        ratio = None, background = None, debug = False, max_dist = 1e6): # Locate paramecium
    '''
    Locate paramecium in an image.

    Arguments
    ---------
    frame : the image
    pixel_per_um : number of pixels per um
    return_angle : if True, return the angle of the cell
    previous_x : previous x position of the cell
    previous_y : previous y position of the cell
    ratio : decimating ratio (to make the image smaller)
    background : background image to subtract
    max_dist : maximum distance from previous position

    Returns
    -------
    x, y (, angle) : position on screen and angle
    '''
    #pixel_per_um = 0.5
    # Resize
    height, width = frame.shape[:2]
    if ratio is None:
        ratio = width/256
    resized = cv2.resize(frame, (width/ratio, height/ratio))
    pixel_per_um = pixel_per_um/ratio

    # Filter
    blur_size = int(pixel_per_um*10)
    if blur_size % 2 == 0:
        blur_size+=1
    filtered=cv2.GaussianBlur(resized, (blur_size, blur_size), 0)

    # Filter background
    if background is not None:
        resized_background = cv2.resize(background, (width / ratio, height / ratio))
        filtered_background=cv2.GaussianBlur(resized_background, (blur_size, blur_size), 0)
    else:
        filtered_background = 0*filtered

    # Remove background
    img = filtered * 1. - filtered_background * 1.

    # Normalize image
    normalized_img = zeros(img.shape)
    normalized_img = cv2.normalize(img, normalized_img, 0, 255, cv2.NORM_MINMAX)
    normalized_img = uint8(normalized_img)

    # Extract edges
    canny = cv2.Canny(normalized_img, int(800*pixel_per_um), int(800*pixel_per_um)) # should depend on pixel_per_um
    #canny = cv2.Canny(normalized_img, 40, 40)  # should depend on pixel_per_um

    # Find contours
    ret = cv2.findContours(canny, 1, 2)
    contours, hierarchy = ret[-2], ret[-1] # for compatibility with opencv2 and 3

    distmin = max_dist*ratio
    #previous_x=None
    if previous_x is None:
        previous_x = width / 2
        previous_y = height / 2
    previous_x = previous_x/ratio
    previous_y = previous_y/ratio
    found = False
    for contour in contours:
        try:
            length = cv2.arcLength(contour, True) / pixel_per_um
            if (length>150) & (contour.shape[0]>10): # at least 10 points
                cv2.drawContours(normalized_img, [contour], 0, (0, 255, 0), 1)
                (x, y), (MA, ma), theta = cv2.fitEllipse(contour)
                MA,ma = MA/pixel_per_um, ma/pixel_per_um
                ma,MA = MA,ma
                dist = ((x - previous_x) ** 2 + (y - previous_y) ** 2) ** 0.5
                if (MA>70) & (MA<250) & (ma>15) & (ma<45) & (dist<distmin):
                    distmin=dist
                    xmin, ymin =x, y
                    angle = (theta+90)*pi/180.
                    found = True
        except cv2.error:
            pass
    if found:
        if debug:
            return xmin*ratio,ymin*ratio,normalized_img
        elif return_angle:
            return xmin * ratio, ymin * ratio, angle
        else:
            return xmin*ratio,ymin*ratio
    else:
        if debug:
            return None,None,normalized_img
        elif return_angle:
            return None,None,None
        else:
            return None, None
