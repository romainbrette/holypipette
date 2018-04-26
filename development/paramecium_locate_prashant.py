'''
Paramecium tracking based on Prashant's code
'''
import skimage
from skimage.io import imread
from skimage.filters import threshold_sauvola
from skimage.measure import label
from skimage.color import rgb2gray
from matplotlib import pyplot as plt
from scipy import ndimage
import imageio
import cv2

pixel_per_um = 0.2

interpolation_order = 0
scale_factor = 1
sauvola_window = 23 # no idea how to set this
#region_area_threshold = 50
region_area_threshold = 800*pixel_per_um**2
region_area_max = 5000*pixel_per_um**2

path='/Users/Romain/Desktop/'
cap = imageio.get_reader(path+'droplet2.mp4')
frame = rgb2gray(cap.get_data(0))

#frame = imread('paramecium2.bmp', as_grey=True)
frame = ndimage.zoom(frame, scale_factor, order=interpolation_order)

binarized = frame >= threshold_sauvola(frame, window_size=sauvola_window)
segment_labels = label(binarized, connectivity=2, background=True)

region_props = skimage.measure.regionprops(segment_labels, binarized)

# Look for the closest region to the center
print frame.shape, binarized.shape, segment_labels.shape
yc, xc = frame.shape
yc, xc = yc*.5, xc*.5

x, y = None, None
dmin = 1e10
for region in region_props:
    if (region.area <= region_area_threshold) | (region.area >= region_area_max):
        continue
    y0, x0 = region.centroid
    x0-= xc
    y0-= yc
    d = x0**2+y0**2 # distance to center
    r = region.equivalent_diameter
    if d<dmin:
        dmin = d
        x, y = x0, y0
        orientation = region.orientation
    print x0,y0,orientation,r/pixel_per_um, region.area
    cv2.circle(frame, (int(x0+xc), int(y0+yc)), int(r), (0, 255, 0), 2)

print "Closest to the center:",x,y,orientation


plt.figure()
plt.imshow(frame, cmap = 'gray')

#plt.figure()
#plt.imshow(binarized, cmap = 'gray')


plt.show()
