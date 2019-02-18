#Code to test the remote control of the peristaltic pump
import numpy as np
import cv2

from Arduino import Arduino
import time

board = Arduino('9600') #plugged in via USB, serial com at rate 9600
pwm_value = 153
pin_pwm = 3
pin_stop = 4
pin_cw = 5
board.pinMode(pin_stop, "OUTPUT")
board.pinMode(pin_cw, "OUTPUT")
board.pinMode(pin_pwm, "OUTPUT")
#TEST with the built in LED
board.pinMode(13, "OUTPUT")

font = cv2.FONT_HERSHEY_SIMPLEX
cap = cv2.VideoCapture(0)
stop = True
direction = True

# def pumpRun(state, direction):
#     if state == False:
#        if direction == True:
#            board.digitalWrite(pin_stop, "HIGH")
#            board.digitalWrite(pin_cw, "HIGH")
#        else:
#            board.digitalWrite(pin_stop, "HIGH")
#            board.digitalWrite(pin_cw, "LOW")
#     else:
#         board.digitalWrite(pin_stop, "LOW")
while(True):
    # Capture frame-by-frame
    ret, frame = cap.read()

    # Our operations on the frame come here
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Display the resulting frame
    #pumpRun(stop,direction)
    board.analogWrite(pin_pwm, pwm_value)
    if stop == False:
        board.digitalWrite(13, "HIGH")
        cv2.putText(gray, 'Run', (100, 100), font, 4, (255, 255, 255), 2, cv2.LINE_AA)
        board.digitalWrite(pin_stop, "HIGH")
        #board.digitalWrite(pin_start, "HIGH")
    else:
        cv2.putText(gray, 'Stop', (100, 100), font, 4, (255, 255, 255), 2, cv2.LINE_AA)
        board.digitalWrite(13, "LOW")
        board.digitalWrite(pin_stop, "LOW")
        #board.digitalWrite(pin_start, "LOW")
    if direction == False:
        cv2.putText(gray, 'CCW direction', (0, 300), font, 4, (255, 255, 255), 2, cv2.LINE_AA)
        board.digitalWrite(pin_cw, "LOW")
        #board.digitalWrite(pin_ccw, "HIGH")
    else:
        cv2.putText(gray, 'CW direction', (0, 300), font, 4, (255, 255, 255), 2, cv2.LINE_AA)
        board.digitalWrite(pin_cw, "HIGH")
        #board.digitalWrite(pin_ccw, "LOW")
    #print("Speed mode(%): ",(pwm_value/255)*100)

    cv2.imshow('frame', gray)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('1'):
        stop = False
    elif key == ord('2'):
        stop = True
    elif key == ord('3'):
        direction = True
    elif key == ord('4'):
        direction = False
    elif key == ord('5'):
        pwm_value = pwm_value - 51
    elif key == ord('6'):
        pwm_value = pwm_value + 51

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()