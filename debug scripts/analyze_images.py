'''
A script to test image processing to locate pipettes
'''
import cv2
from matplotlib import pyplot as plt
from numpy import *
from holypipette.vision import *

# Load all images

img = []

for i in range(11):
    imgi = []
    for k in range(17):
        imgi.append(cv2.imread('./screenshots/stack{}.{}.jpg'.format(i,k),0))
    img.append(imgi)

print img[0][0].shape

# Make the templates
stack = []
direction = pipette_cardinal(img[0][8])
print direction
for k in range(17):
    stack.append(crop_cardinal(crop_center(img[0][k]), direction))

def calculate_matching_precision():
    # First template matching to estimate pipette position on screen
    x0, y0, _ = templatematching(img[0][8], stack[8])

    # Calculate best match
    for i in range(1,2):
        xl, yl, zl = [], [], []
        for j in range(16):
            print i,j
            valmax = -1
            for k, template in enumerate(stack):  # we look for the best matching template
                xt, yt, val = templatematching(img[i][j], template)
                xt -= x0
                yt -= y0
                if val > valmax:
                    valmax = val
                    x, y, z = xt, yt, k  # note the sign for z
            print x,y,z-j
            xl.append(x*1.)
            yl.append(y*1.)
            zl.append(z*1.-j)
        xl,yl,zl=array(xl),array(yl),array(zl)
        print xl,yl,zl
        print mean(xl),mean(yl),mean(zl)
        print std(xl),std(yl),std(zl)

stack = img[0]

for j in range(1,len(stack)-1):
    D = 2.*stack[j]-stack[j-1]*1.-stack[j+1]*1. # z-laplacian
    #print D.max()

    normalizedImg = zeros((800, 800))
    normalizedImg = cv2.normalize(abs(D),  normalizedImg, 0, 255, cv2.NORM_MINMAX)

    # Find the centroid (doesn't give the tip)
    xy = mgrid[0:normalizedImg.shape[0],0:normalizedImg.shape[1]]
    yc = sum(xy[0]*normalizedImg)/sum(normalizedImg)
    xc = sum(xy[1]*normalizedImg)/sum(normalizedImg)

    print xc,yc

#plt.imshow(stack[8], cmap = 'gray')
plt.imshow(normalizedImg, cmap = 'gray')
plt.xticks([]), plt.yticks([])  # to hide tick values on X and Y axis
plt.show()
