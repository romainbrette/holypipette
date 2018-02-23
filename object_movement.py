
from collections import deque
import numpy as np
import argparse
#import imutils
import cv2
from matplotlib import pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video",
	help="path to the (optional) video file")
ap.add_argument("-b", "--buffer", type=int, default=32,
	help="max buffer size")
args = vars(ap.parse_args())

rect = (None,None)
startPoint = False
loopPoint = False
def on_mouse(event,x,y,flags,params):
    global rect,startPoint
    # get mouse click
    if event == cv2.EVENT_LBUTTONDOWN:
        if startPoint == False:
            rect = (x, y)
            startPoint = True

def distance(pt_1, pt_2):
    pt_1 = np.array((pt_1[0], pt_1[1]))
    pt_2 = np.array((pt_2[0], pt_2[1]))
    return np.linalg.norm(pt_1-pt_2)

def closest_node(node, nodes):
    global dist
    i = 0
    for n in range (0,len(nodes)-1):
        if distance(node, nodes[n]) <= dist:
            dist = distance(node, nodes[n])
            i = n
    return i

greenLower = (29, 86, 6)
greenUpper = (64, 255, 255)

pts = deque(maxlen=args["buffer"])
counter = 0
(dX, dY) = (0, 0)
direction = ""

if not args.get("video", False):
	camera = cv2.VideoCapture('Testing1.mp4')

else:
	camera = cv2.VideoCapture(args["video"])
waitTime = 50
(grabbed, frame) = camera.read()

while(camera.isOpened()):
	(grabbed, frame) = camera.read()
	if args.get("video") and not grabbed:
		break
	i=0
	dist =99999999999
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	blur = cv2.GaussianBlur(gray, (71, 71), 0)
	ret3, th3 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
	canny = cv2.Canny(th3, 10, 10)
	kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (1, 1))
	dilated = cv2.dilate(canny, kernel)
	_, cnts, _ = cv2.findContours(dilated.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	coins = frame.copy()

	cv2.drawContours(coins, cnts, -1, (255, 0, 0), 3)
	cv2.imshow("Frame", coins)
	cv2.setMouseCallback('Frame', on_mouse)

	if startPoint == True:
		t= closest_node(rect,cnts)
		cv2.drawContours(coins, cnts, closest_node(rect,cnts), (0, 255, 0), 3)
		cv2.imshow("Frame", coins)
		M = cv2.moments(cnts[closest_node(rect,cnts)])
		cX = int(M["m10"] / M["m00"])
		cY = int(M["m01"] / M["m00"])
	 	startPoint = False
		loopPoint = True
	if loopPoint == True:
		rect = (cX,cY)
		t = closest_node(rect, cnts)
		cv2.drawContours(coins, cnts, closest_node(rect, cnts), (0, 255, 0), 3)
		cv2.imshow("Frame", coins)
		M = cv2.moments(cnts[closest_node(rect, cnts)])
		cX = int(M["m10"] / M["m00"])
		cY = int(M["m01"] / M["m00"])
        print("TESTING")
        print(cnts[1])
	if cv2.waitKey(150) & 0xFF == ord('q'):
		break

camera.release()
cv2.destroyAllWindows()