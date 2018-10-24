'''
Trying to identify and locate Paramecium in the image.
Using x40 images.
'''
import cv2
from matplotlib import pyplot as plt
from numpy import *
import numpy as np
#from vision.paramecium_tracking import *

I0 = cv2.imread('paramecium0.png',0)
I1 = cv2.imread('paramecium1.png',0)

pixel_per_um = 5. # x40

# Resize
def resize(frame, ratio):
    height, width = frame.shape[:2]
    return cv2.resize(frame, (int(width / ratio), int(height / ratio)))

# First filter both images
def smooth(frame, pixel_per_um = 5):
    blur_size = int(pixel_per_um*5)
    if blur_size % 2 == 0:
        blur_size+=1
    return cv2.GaussianBlur(frame, (blur_size, blur_size), 0)

width = I0.shape[1]
ratio = width / 256
ratio = 3.4
print(ratio)
pixel_per_um = pixel_per_um / ratio

I0_small = resize(I0, ratio)
I1_small = resize(I1, ratio)
I0_smooth = smooth(I0_small, pixel_per_um)
I1_smooth = smooth(I1_small, pixel_per_um)
print (I0_smooth.dtype)
# Background subtraction
I_sub = I1_smooth*1.-I0_smooth*0.
normalizedImg = zeros(I_sub.shape)
normalizedImg = cv2.normalize(I_sub, normalizedImg, 0, 255, cv2.NORM_MINMAX)
normalizedImg = uint8(normalizedImg)
sobelx = cv2.Sobel(normalizedImg, cv2.CV_64F, 1, 0)
sobely = cv2.Sobel(normalizedImg, cv2.CV_64F, 0, 1)
v = median(normalizedImg)
#edge_gradient = sqrt(sobelx**2 + sobely**2)
edge_gradient = np.abs(sobelx) + np.abs(sobely)
print(edge_gradient.max())
lower = np.percentile(edge_gradient.flatten(), 70)
upper = np.percentile(edge_gradient.flatten(), 98)
p = np.arange(0, 100, 5)
print(p)
print(np.percentile(edge_gradient.flatten(), p))
plt.hist(edge_gradient.flatten(), 50)
plt.show()
print(lower, v, upper)
# Canny edge detection
#canny = cv2.Canny(normalizedImg, normalizedImg.shape[0]/8, normalizedImg.shape[0]/8)
canny = cv2.Canny(normalizedImg, lower, upper)
# ret, thresh = cv2.threshold(canny, 127, 255, 0)

ret = cv2.findContours(canny, 1, 2)
contours, hierarchy = ret[-2], ret[-1] # for compatibility with opencv2 and 3

found = False
#for cnt in contours:
#    print cv2.arcLength(cnt, True)/pixel_per_um

hierarchy = hierarchy[0] # get the actual inner list of hierarchy descriptions

# For each contour, find the bounding rectangle and draw it
print('number of contours: ', len(contours))
for contour,h in zip(contours,hierarchy):
    # cv2.drawContours(I1_smooth, [contour], 0, (0, 255, 0), 1)
    length = cv2.arcLength(contour, True)/pixel_per_um
    if (length>100): # this is not the total length, because it could be partial
        ellipse = cv2.fitEllipse(contour)
        (x, y), (MA, ma), angle = ellipse
        print (MA/pixel_per_um, ma/pixel_per_um, angle)
        # cv2.drawContours(I1_smooth, [contour], 0, (0, 255, 0), 1)
        cv2.ellipse(I1, ((int(x*ratio), int(y*ratio)), (int(MA*ratio), int(ma*ratio)), angle), (255, 0, 0), 2)

    # try:
    #     M = cv2.moments(cnt)
    #     if (cv2.arcLength(cnt, True) > 35*pixel_per_um) & bool(M['m00']):
    #         (x, y), radius = cv2.minEnclosingCircle(cnt)
    #         cx = int(M['m10'] / M['m00'])
    #         cy = int(M['m01'] / M['m00'])
    #         u20 = int(M['m20']/M['m00'] - cx**2)
    #         u02 = int(M['m02'] / M['m00'] - cy ** 2)
    #         u11 = int(M['m11'] / M['m00'] - cx * cy)
    #         theta = atan2((u20-u02), 2*u11)
    #         radius = int(radius)
    #         dist = ((x - previous_x) ** 2 + (y - previous_y) ** 2) ** 0.5
    #         if (radius < 20*pixel_per_um) & (radius > 10*pixel_per_um) & (dist<distmin):
    #             distmin=dist
    #             xmin, ymin =x, y
    #             angle = theta
    #             found = True
    # except cv2.error:
    #     pass

#xmin*ratio,ymin*ratio

#x,y = where_is_paramecium(I0, pixel_per_um = 5.)

#print x,y

plt.figure()
plt.imshow(I1, cmap = 'gray')
plt.xticks([]), plt.yticks([])  # to hide tick values on X and Y axis
plt.show()
