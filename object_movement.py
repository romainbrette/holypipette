
from collections import deque
import numpy as np
import argparse
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

if not args.get("video", False):
	camera = cv2.VideoCapture('Testing1.mp4')

else:
	camera = cv2.VideoCapture(args["video"])
(grabbed, frame) = camera.read()

while(camera.isOpened()):
	(grabbed, frame) = camera.read()
	if args.get("video") and not grabbed:
		break
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	blur = cv2.GaussianBlur(gray, (71, 71), 0)
	ret3, th3 = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
	canny = cv2.Canny(th3, 10, 10)
	kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (1, 1))
	dilated = cv2.dilate(canny, kernel)
	_, cnts, _ = cv2.findContours(dilated.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	coins = frame.copy()

	#cv2.drawContours(coins, cnts, -1, (255, 0, 0), 3)
	cv2.imshow("Frame", coins)
	cv2.setMouseCallback('Frame', on_mouse)

	if startPoint == True:
		i = 0
		dist = distance(rect, cnts[0])
		for n in range(1, len(cnts) - 1):
			M = cv2.moments(cnts[n])
			if M["m00"] != 0:
				cX = int(M["m10"] / M["m00"])
				cY = int(M["m01"] / M["m00"])
			else:
				cX, cY = 0, 0
			rect1 = (cX, cY)
			if distance(rect1, rect) <= dist:
				dist = distance(rect1, rect)
				i = n
		cv2.drawContours(coins, cnts, i, (0, 255, 0), 3)
		cv2.imshow("Frame", coins)
		M = cv2.moments(cnts[i])
		if M["m00"] != 0:
			cX = int(M["m10"] / M["m00"])
			cY = int(M["m01"] / M["m00"])
		else:
			cX, cY = 0, 0
	 	startPoint = False
		loopPoint = True
	if loopPoint == True:
		i=0
		rect = (cX,cY)
		dist = distance(rect,cnts[0])
		for n in range(1, len(cnts) - 1):
			M = cv2.moments(cnts[n])
			if M["m00"] != 0:
				cX = int(M["m10"] / M["m00"])
				cY = int(M["m01"] / M["m00"])
			else:
				cX, cY = 0, 0
			rect1 = (cX,cY)
			if distance(rect1, rect) <= dist:
				dist = distance(rect1, rect)
				i = n
		cv2.drawContours(coins, cnts, i, (0, 255, 0), 3)
		cv2.imshow("Frame", coins)
		M = cv2.moments(cnts[i])
		print(M["m00"])
		if M["m00"] != 0:
			cX = int(M["m10"] / M["m00"])
			cY = int(M["m01"] / M["m00"])
		else:
			cX, cY = 0, 0

	if cv2.waitKey(150) & 0xFF == ord('q'):
		break

camera.release()
cv2.destroyAllWindows()