'''
Make overlay images to indicate ROI and image center.
Black on white.
'''
import imageio
from skimage.draw import line, rectangle_perimeter, rectangle
import numpy as np

# Script arguments
magnification = 40.
binning = 1
ROI_1 = 250. # size in um
ROI_2 = 150.
name = 'overlay_x40'

# General parameters
plus_size = 5 # in um

# Camera specifications
#width, height = 2752, 2192  # 490 * 390 um at x40
width, height = 100,100
pixel_per_um_x1 = 5.63/40 # Number of pixels per um for x1 magnification

# Calculations
pixel_per_um = pixel_per_um_x1*magnification/binning
width, height = int(width/binning), int(height/binning)

# Should be a multiple of 4
width, height = int(width/4)*4, int(height/4)*4

# White background
img = 255*np.ones((height, width), dtype=np.uint8)

# Center cross, 2 pixel width
xc = int(width / 2)
yc = int(height / 2)
length = int(pixel_per_um * 8)
gap = int(pixel_per_um * 3)
# Vertical
rr, cc = rectangle((yc-length, xc-1), (yc-gap, xc))
img[rr,cc] = 0
rr, cc = rectangle((yc+length, xc-1), (yc+gap, xc))
img[rr,cc] = 0
# Horizontal
rr, cc = rectangle((yc-1, xc-length), (yc, xc-gap))
img[rr,cc] = 0
rr, cc = rectangle((yc-1, xc+length), (yc, xc+gap))
img[rr,cc] = 0

# ROI
for ROI in (ROI_1, ROI_2):
    break
    ROI_width = int(ROI * pixel_per_um)
    ROI_height = int(ROI * pixel_per_um)
    x1 = int(width / 2 - ROI_width / 2)
    y1 = int(height / 2 - ROI_height / 2)
    x2 = int(width / 2 + ROI_width / 2)
    y2 = int(height / 2 + ROI_height / 2)
    rr, cc = rectangle_perimeter((y1, x1), (y2,x2))
    img[rr,cc] = 0

# Save
imageio.imsave(name+'.bmp', img)
