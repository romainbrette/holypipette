'''
Records camera from screen capture.

Problems:
- the clock may change, this causes a localization issue.
- I can only get up to 10 Hz. Not sufficient to get precise timing of frames. Although perhaps I could downsample.

In the end, this is no better than a screen capture program.

See this:
https://stackoverflow.com/questions/3586046/fastest-way-to-take-a-screenshot-with-python-on-windows/3586280#3586280
https://stackoverflow.com/questions/1080719/screenshot-an-application-regardless-of-whats-in-front-of-it

On Mac: Screenshot: 0.47 s ! 0.42 with pyautogui; same with PIL
On PC: 0.05 s or so.
'''
import imageio
import time
import numpy as np
import pyautogui

# # Timing measurement
# t=time.time()
# for _ in range(10):
#     image = pyautogui.screenshot()
#     imageio.imsave("tif/test.tif", image)
# print(time.time()-t)
# exit(0)

countdown = 5 # in seconds
decimate = 10
duration = 10 # in seconds
fps = 10. # in Hz, should be just slightly higher than the actual FPS of the video

## Count down
for i in range(countdown,0,-1):
    print(i)
    time.sleep(1)

## Find the active zone
print('Localizing the camera display.')

# Find pixels that change
previous_image = imageio.imread('<screen>') #[::decimate, ::decimate]
time.sleep(.1)
image = imageio.imread('<screen>') #[::decimate, ::decimate]
zone = (image != previous_image)

# Find columns and rows
columns = zone.sum(axis=0).nonzero()[0]
x1, x2 = columns[0], columns[-1]+1
rows = zone.sum(axis=1).nonzero()[0]
y1, y2 = rows[0], rows[-1]+1

## Recording
t0 = t = time.time()
i = 0
while t<t0+duration:
    image = pyautogui.screenshot(region=(x1,y1,x2,y2))
    ## Saving
    imageio.imsave("tif/test{}.tif".format(i), image)

    new_t = time.time()
    if new_t-t < 1/fps:
        time.sleep(1/fps - (new_t-t))
    else:
        print("lost frame",i,"by ",new_t-t - 1/fps,"second")
    t = time.time()
    i += 1
