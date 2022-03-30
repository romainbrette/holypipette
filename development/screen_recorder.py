'''
Records camera from screen capture.

Install pywin32 via conda

At 1342x1006 I get 16 Hz.

It is critical to reduce the window size as much as possible
'''
import imageio
import time
import numpy as np
import win32gui
import win32ui
from ctypes import windll

decimate = 10
duration = 10 # in seconds
fps = 30. # in Hz, expected frame rate

# Select the window
hwnd = win32gui.FindWindow(None, 'DinoCapture 2.0')
left, top, right, bot = win32gui.GetClientRect(hwnd)
#left, top, right, bot = win32gui.GetWindowRect(hwnd)
w = right - left
h = bot - top

hwndDC = win32gui.GetWindowDC(hwnd)
mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
saveDC = mfcDC.CreateCompatibleDC()

saveBitMap = win32ui.CreateBitmap()
saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

saveDC.SelectObject(saveBitMap)

def screenshot():
    result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)
    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    im = np.frombuffer(bmpstr, dtype=np.uint8).reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))
    return im[:,:,2::-1]

## Find the active zone
print('Localizing the camera display.')

# Find pixels that change
previous_image = screenshot() #[::decimate, ::decimate]
time.sleep(.1)
image = screenshot() #[::decimate, ::decimate]
zone = (image != previous_image)

# Find columns and rows
columns = zone.sum(axis=0).nonzero()[0]
x1, x2 = columns[0], columns[-1]+1
rows = zone.sum(axis=1).nonzero()[0]
y1, y2 = rows[0], rows[-1]+1

print('Window size: {}x{}'.format(x2-x1, y2-y1))

## Recording
t0 = t = previous_t = time.time()
i = 0
previous_image_down = image[y1:y2:decimate,x1:x2:decimate,:]
while t<t0+duration:
    t = time.time()
    if t-previous_t > 1/fps:
        print("lost frame",i,"by ",t-previous_t - 1/fps,"second")
    previous_t = t

    image = screenshot()[y1:y2,x1:x2,:]
    image_down = image[::decimate,::decimate,:]

    if (image_down == previous_image_down).all():
        print("Identical frame")
    else:
        ## Saving
        #imageio.imsave("tif/test{}.tif".format(i), image)
        i += 1

    previous_image_down = image_down*1

print(i, 'frames')

win32gui.DeleteObject(saveBitMap.GetHandle())
saveDC.DeleteDC()
mfcDC.DeleteDC()
win32gui.ReleaseDC(hwnd, hwndDC)
