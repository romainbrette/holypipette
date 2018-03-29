#Working for bright area (need a preprocess), optical flow could help to track in dark area in case of pixel brightness constancy
# (In the testing video, there are manything like fibres and debris --> cannot work with optical flow)
# Methods like model fitting and Houghs transform can help to detect the tip (Future work)
import cv2
import numpy as np
import sys
from matplotlib import pyplot as plt

clickList = []
trackingList = []
drawing = False
finish = False
update = False
wait_time = 0
xMin = 1000
yMin = 1000
xMax = 0
yMax = 0
kernel = np.ones((5, 5), np.uint8)
def callback(event,x,y,flags,params):
     global drawing, finish, click_list, wait_time,xMin,xMax,yMin,yMax,update
     if event == cv2.EVENT_LBUTTONDOWN:
        xMin = 1000
        yMin = 1000
        xMax = 0
        yMax = 0
        wait_time = 0
        drawing = True
        update = False
        clickList.append((x, y))

     elif event == cv2.EVENT_MOUSEMOVE:
        if drawing == True:
            clickList.append((x, y))
     elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        finish = True
        clickList.append((x, y))
     for i in range(len(clickList)):
        cv2.circle(frame, clickList[i], 1, (244, 4, 4), 2)
        print(clickList[0][0])
     cv2.imshow('img', frame)

def backproject(source, target, scale = 1):
    #Grayscale
     roihist = cv2.calcHist([source], [0], None, [256], [0, 256])
     cv2.normalize(roihist, roihist, 0, 255, cv2.NORM_MINMAX)
     dst = cv2.calcBackProject([target], [0], roihist, [0, 256], scale)
     return dst

def backproject1(source, target, levels = 2, scale = 1):
    #More info?
 	hsv = cv2.cvtColor(source,	cv2.COLOR_BGR2HSV)
 	hsvt = cv2.cvtColor(target,	cv2.COLOR_BGR2HSV)
 	roihist = cv2.calcHist([hsv],[0, 1], None, [levels, levels], [0, 180, 0, 256] )
 	cv2.normalize(roihist,roihist,0,255,cv2.NORM_MINMAX)
 	dst = cv2.calcBackProject([hsvt],[0,1],roihist,[0,180,0,256], scale)
 	return dst

cv2.namedWindow('img')
cv2.setMouseCallback('img', callback)
cap = cv2.VideoCapture("sarah_21022018_cgc1_before.webm")
#cap = cv2.VideoCapture(0)
while (cap.isOpened()):
    (grabbed, frame) = cap.read()
    img = frame
    if not grabbed:
        break
    if update == True:
        ok, bbox = tracker.update(img)

        if ok:
            p1 = (int(bbox[0]), int(bbox[1]))
            p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
            cv2.rectangle(img, p1, p2, (0, 0, 0), 2, 1)
            mask_use = np.zeros(frame.shape, np.uint8)
            mask_use[int(bbox[1]):int(bbox[1] + bbox[3]),int(bbox[0]):int(bbox[0] + bbox[2])] = frame[int(bbox[1]):int(bbox[1] + bbox[3]),int(bbox[0]):int(bbox[0] + bbox[2])]
            backproj = np.uint8(backproject(roi, mask_use,scale = 2))
            #backproj = np.uint8(backproject1(roi, mask_use, levels =2,scale=2))
            ret, thresh = cv2.threshold(backproj, 100, 255, cv2.THRESH_BINARY)
            closing = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            cv2.imshow("Back proj", backproj)
            cv2.imshow('img', img)


    if finish == True:
        update = True
        tracker = cv2.TrackerBoosting_create()
        finish = False
        trackingList = clickList
        #Optical flow????? possible for darker and messy background but problem with bright constancy
        roi = np.zeros((1, len(clickList), 3), np.uint8)
        print(roi.shape)
        print(frame.shape)
        for i in range(len(clickList)):
            roi[0, i] = frame[(clickList[i][1], clickList[i][0])]

        clickList = []
        wait_time =1
        for i in range(len(trackingList)):
            if trackingList[i][0] > xMax:
                xMax = trackingList[i][0]
            if trackingList[i][0] < xMin:
                xMin = trackingList[i][0]
            if trackingList[i][1] > yMax:
                yMax = trackingList[i][1]
            if trackingList[i][1] < yMin:
                yMin = trackingList[i][1]

        bbox =(xMin,yMin,(xMax-xMin),(yMax-yMin))
        trackingWindow = frame[int(bbox[1]):int(bbox[1] + bbox[3]), int(bbox[0]):int(bbox[0] + bbox[2])]
        cv2.rectangle(img,  (xMin, yMin), (xMax, yMax),(0, 0, 0), 1)
        cv2.imshow('img', img)
        ok = tracker.init(img, bbox)
    k = cv2.waitKey(wait_time)

    if k & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()


