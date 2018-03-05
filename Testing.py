import cv2
import numpy as np
import csv
lk_params = dict(winSize=(15, 15),
                 maxLevel=20000,
                 criteria=(cv2.TERM_CRITERIA_EPS |
                           cv2.TERM_CRITERIA_COUNT, 10, 0.03))
click_list = []
global click_list
positions = []
for i in range(100000): positions.append((0, 0))
def callback(event, x, y, flags, param):
    if event == 1: click_list.append((x, y))
cv2.namedWindow('img')
cv2.setMouseCallback('img', callback)
cap = cv2.VideoCapture("Testing0503.mp4")
frame_number = 0
wait_time = 0
p0 = np.array([[[0, 0]]], np.float32)
while True:
    click_length = len(click_list)
    _, img = cap.read()
    try:
        old_gray = img_gray.copy()
    except:
        old_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    try:
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    except:
        break
    p1, error, _ = cv2.calcOpticalFlowPyrLK(old_gray, img_gray,
                                            p0, None, **lk_params)
    if error == [0][0]: wait_time = 0
    xy = int(p1[0][0][0]), int(p1[0][0][1])
    p0 = p1
    cv2.circle(img, xy, 5, (244, 4, 4), 1)
    cv2.circle(img, xy, 15, (244, 4, 4), 1)
    cv2.imshow('img', img)
    k = cv2.waitKey(wait_time)
    wait_time = 1
    if len(click_list) == click_length:
        positions[frame_number] = xy
    else:
        p0 = np.array([[click_list[-1]]], np.float32)
        xy = click_list[-1]
        positions[frame_number] = xy
    frame_number += 1

cv2.destroyAllWindows()

positions = positions[:frame_number]

with open(output_path, 'w') as csvfile:
    fieldnames = ['x_position', 'y_position']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for position in positions:
        x, y = position[0], position[1]
        writer.writerow({'x_position': x, 'y_position': y})
print 'finished writing data'

