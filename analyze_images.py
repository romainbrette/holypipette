'''
A script to test the difference image idea to locate pipettes
'''
import cv2
from matplotlib import pyplot as plt
from numpy import *

img = []

for k in range(11):
    img.append(cv2.imread('./screenshots/series{}.jpg'.format(k),0))

D = img[1]*1.-img[0]*1.
print D.max()

#normalizedImg = zeros((800, 800))
#normalizedImg = cv2.normalize(D,  normalizedImg, 0, 255, cv2.NORM_MINMAX)

plt.imshow(D, cmap = 'gray')
plt.xticks([]), plt.yticks([])  # to hide tick values on X and Y axis
plt.show()
