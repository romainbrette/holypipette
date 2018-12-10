# coding=utf-8
'''
These are functions to locate paramecium in an image

TODO: look for the closest in ellipse property space
'''
from math import atan2
import cv2
import numpy as np
import matplotlib.pyplot as plt

from numpy import zeros,uint8,pi, uint16, around

__all__ = ["where_is_paramecium", "where_is_droplet", "where_is_paramecium2"]

def backproject(source, target, scale = 1):
    #Grayscale
     roihist = cv2.calcHist([source], [0], None, [256], [0, 256])
     cv2.normalize(roihist, roihist, 0, 255, cv2.NORM_MINMAX)
     dst = cv2.calcBackProject([target], [0], roihist, [0, 256], scale)
     return dst


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


def where_is_paramecium(frame, pixel_per_um=5., previous_x=None, previous_y=None,
                        previous_MA=None, previous_ma=None, previous_angle=None,
                        config=None):
    '''
    Locate paramecium in an image.

    Arguments
    ---------
    frame : the image
    pixel_per_um : number of pixels per µm
    previous_x : previous x position of the cell (in pixels on 1:1 camera frame)
    previous_y : previous y position of the cell in pixels on 1:1 camera frame)
    previous_MA : previous length of cell (in µm), i.e. major axis
    previous_ma : previous width of cell (in µm), i.e. minor axis
    previous_angle : previous angle of cell (in radians)
    config : `ParameciumConfig` object

    Returns
    -------
    x, y, MA, ma, angle : Position and size of fitted ellipse
    '''
    if config is None:
        # Avoid circular imports
        from holypipette.interface.paramecium import ParameciumConfig
        config = ParameciumConfig()

    # Resize
    height, width = frame.shape[:2]
    ratio = config.downsample
    resized = cv2.resize(frame, (int(width/ratio), int(height/ratio)))
    pixel_per_um = pixel_per_um/ratio

    # Filter
    blur_size = int(config.blur_size * pixel_per_um)
    if blur_size % 2 == 0:
        blur_size+=1
    img=cv2.GaussianBlur(resized, (blur_size, blur_size), 0)

    # Normalize image
    normalized_img = zeros(img.shape)
    normalized_img = cv2.normalize(img, normalized_img, 0, 255, cv2.NORM_MINMAX,
                                   dtype=cv2.CV_8UC1)
    # Get (simplified) intensity gradient, slightly redundant because Canny
    # algorithm will do the same thing, but having the distribution is useful to
    # use more robust quantiles instead of fixed values
    sobel_x = cv2.Sobel(normalized_img, cv2.CV_64F, 1, 0)
    sobel_y = cv2.Sobel(normalized_img, cv2.CV_64F, 0, 1)
    intensity_grad = np.abs(sobel_x) + np.abs(sobel_y)
    min_grad, max_grad = np.percentile(intensity_grad.flat, [config.min_gradient,
                                                             config.max_gradient])
    # Extract edges
    canny = cv2.Canny(normalized_img, min_grad, max_grad)

    # Find contours
    ret = cv2.findContours(canny, 1, 2)
    contours, hierarchies = ret[-2], ret[-1] # for compatibility with opencv2 and 3

    if previous_x is None:
        previous_x = width / 2
        previous_y = height / 2
    if previous_MA is None:
        previous_MA = (config.min_length + config.max_length)*0.5
        previous_ma = (config.min_width + config.max_width)*0.5
    previous_x = previous_x/ratio
    previous_y = previous_y/ratio
    ellipses = []
    for contour, hierarchy in zip(contours, hierarchies[0, :, :]):
        try:
            if (contour.shape[0]>5) and (cv2.arcLength(contour, True) > config.minimum_contour*pixel_per_um): # at least 5 points
                (x, y), (ma, MA), theta = cv2.fitEllipse(np.squeeze(contour))
                x, y = x*ratio, y*ratio
                MA, ma = MA/pixel_per_um, ma/pixel_per_um
                dist = ((x - previous_x) ** 2 + (y - previous_y) ** 2) ** 0.5
                if MA > config.min_length and ma > config.min_width and MA < config.max_length and ma < config.max_width and MA > 1.5*ma:
                    angle = (theta+90)*pi/180.
                    ellipses.append((x, y, MA, ma, angle, dist))
        except cv2.error:
            continue

    ellipses = np.array(ellipses)
    if len(ellipses):
        MA_diff = np.abs(previous_MA - ellipses[:, 2])
        ma_diff = np.abs(previous_ma - ellipses[:, 3])
        # TODO: It would be better to have not only the previous position, but
        # earlier positions as well
        total_dist = MA_diff + ma_diff + ellipses[:, 5]
        best = np.argmin(total_dist)

    if len(ellipses):
        return ellipses[best, :5]
    else:
        return None, None, None, None, None


def where_is_paramecium2(frame, pixel_per_um = 5., return_angle = False, previous_x = None, previous_y = None,
                        ratio = None, background = None, debug = False, max_dist = 1e6): # Locate paramecium
    from holypipette.gui import movingList
    height, width = frame.shape[:2]
    if ratio is None:
        ratio = width / 256
    frame = cv2.resize(frame, (width / ratio, height / ratio))
    # Normalize image
    normalized_img = zeros(frame.shape)
    normalized_img = cv2.normalize(frame, normalized_img, 0, 255, cv2.NORM_MINMAX)
    normalized_img = uint8(normalized_img)

    pixel_per_um = pixel_per_um / ratio
    #frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame1 = cv2.adaptiveThreshold(frame, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    kernel = np.ones((2, 2), np.uint8)
    frame1 = cv2.morphologyEx(frame1, cv2.MORPH_GRADIENT, kernel)

    kernel = np.ones((3, 3), np.uint8)
    frame1 = cv2.morphologyEx(frame1, cv2.MORPH_CLOSE, kernel)
    frame1 = cv2.morphologyEx(frame1, cv2.MORPH_OPEN, kernel)

    _, cnts, _ = cv2.findContours(frame1,cv2.RETR_CCOMP, 2)

    mask_use = np.ones(frame1.shape, np.uint8) * 255
    for cnt in cnts:
        length = cv2.arcLength(cnt, True) / pixel_per_um
        if (length > 150) & (cnt.shape[0] > 10):
            x, y, w, h = cv2.boundingRect(cnt)
            cropped = np.zeros(frame.shape, np.uint8)
            cropped[0:h,0:w] = frame[y:y+h, x:x+w]
            roi = np.zeros((1, 2*(w+h), 3), np.uint8)
            for i in range (0,w):
                roi[0, i] = cropped[(0,i)]
            for i in range(w+1,2*w):
                roi[0, i] = cropped[(h-1,i-w-1)]
            for i in range(2*w+1, 2*w+h):
                roi[0, i] = cropped[(i-(2*w),0)]
            for i in range(2*w+h+1, 2*(w+h)):
                roi[0, i] = cropped[(i-(2*w+h),w-1)]

            backproj = np.uint8(backproject(roi, cropped, scale=2))
            mask_use[y:y + h, x:x + w] = backproj[0:h, 0:w]


    ret, mask_use = cv2.threshold(mask_use, 50, 255, cv2.THRESH_BINARY_INV)
    _, cnts, _ = cv2.findContours(mask_use, cv2.RETR_CCOMP, 2)

    for cnt in cnts:
        length = cv2.arcLength(cnt, True) / pixel_per_um
        if (length < 150) or (cnt.shape[0] < 10):
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            cv2.drawContours(mask_use, [box], 0, (0, 0, 0), cv2.FILLED)


    kernel = np.ones((5, 5), np.uint8)
    mask_use = cv2.morphologyEx(mask_use, cv2.MORPH_CLOSE, kernel)

    mask_use = cv2.resize(mask_use, (width, height))
    frame = cv2.resize(frame, (width, height))
    _, cnts, _ = cv2.findContours(mask_use, cv2.RETR_CCOMP, 2)
    cv2.drawContours(frame, cnts, -1, (255, 255, 255), 3)

    i = 0.2

    found = False
    for cnt in cnts:
        length = cv2.arcLength(cnt, True) / pixel_per_um
        if (length > 250) & (cnt.shape[0] > 10):
            if len(movingList.template) < 2:
                movingList.template.append(cnt)
            else:
                ret1 = cv2.matchShapes(movingList.template[0], cnt, 1, 0.0)
                ret2 = cv2.matchShapes(movingList.template[1], cnt, 1, 0.0)
                if (ret1 < i) or (ret2 <i):
                    movingList.template[1] = cnt
                    found = True
                    break

    cv2.drawContours(frame, [movingList.template[1]], 0, (0, 0, 0), 3)
    (xmin, ymin), (MA, ma), theta = cv2.fitEllipse(movingList.template[1])
    angle = (theta + 90) * pi / 180.

    if found:
        if debug:
            return xmin , ymin , normalized_img
        elif return_angle:
            return xmin , ymin , angle
        else:
            return xmin , ymin
    else:
        if debug:
            return None, None, normalized_img
        elif return_angle:
            return None, None, None
        else:
            return None, None