from __future__ import print_function
import numpy as np
from PyQt5 import QtCore, QtWidgets
import warnings
try:
    import cv2
except:
    warnings.warn('OpenCV not available')
from numpy import *
from holypipette.interface import TaskInterface, command, blocking_command
from holypipette.vision import *



class CameraInterface(TaskInterface):
    updated_exposure = QtCore.pyqtSignal('QString', 'QString')

    def __init__(self, camera, with_tracking=False):
        super(CameraInterface, self).__init__()
        self.camera = camera
        self.with_tracking = with_tracking
        if with_tracking:
            self.multitracker = cv2.MultiTracker_create()
            self.movingList = []
        else:
            self.multitracker = None
            self.movingList = []

    def connect(self, main_gui):
        self.updated_exposure.connect(main_gui.set_status_message)
        self.signal_updated_exposure()
        if self.with_tracking:
            main_gui.image_edit_funcs.append(self.show_tracked_objects)
            #main_gui.image_edit_funcs.append(self.show_tracked_paramecium)
            #main_gui.image_edit_funcs.append(self.pipette_contact_detection)

    def signal_updated_exposure(self):
        # Should be called by subclasses that actually support setting the exposure
        exposure = self.camera.get_exposure()
        if exposure > 0:
            self.updated_exposure.emit('Camera', 'Exposure: %.1fms' % exposure)

    @blocking_command(category='Camera',
                      description='Auto exposure',
                      task_description='Adjusting exposure')
    def auto_exposure(self,args):
        self.camera.auto_exposure()
        self.signal_updated_exposure()

    @command(category='Camera',
             description='Increase exposure time by {:.1f}ms',
             default_arg=2.5)
    def increase_exposure(self, increase):
        self.camera.change_exposure(increase)
        self.signal_updated_exposure()

    @command(category='Camera',
             description='Decrease exposure time by {:.1f}ms',
             default_arg=2.5)
    def decrease_exposure(self, decrease):
        self.camera.change_exposure(-decrease)
        self.signal_updated_exposure()

    @command(category='Camera',
             description='Save the current image to a file')
    def save_image(self):
        try:
            from PIL import Image
        except ImportError:
            self.error('Saving images needs the PIL or Pillow module')
            return
        frame = self.camera.snap()
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(caption='Save image',
                                                         filter='Images (*.png, *.tiff)',
                                                         options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if len(fname):
            img = Image.fromarray(frame)
            try:
                img.save(fname)
            except (KeyError, IOError):
                self.exception('Saving image as "%s" failed.' % fname)


    def show_tracked_objects(self, img):
        from holypipette.gui.movingList import moveList
        del moveList[:]
        ok, boxes = self.multitracker.update(img)
        for newbox in boxes:
            p1 = (int(newbox[0]), int(newbox[1]))
            p2 = (int(newbox[0] + newbox[2]), int(newbox[1] + newbox[3]))
            cv2.rectangle(img, p1, p2, (255, 255, 255), 2)
            x = int(newbox[0] + 0.5 * newbox[2])
            y = int(newbox[1] + 0.5 * newbox[3])
            xs = x - self.camera.width / 2
            ys = y - self.camera.height / 2
            moveList.append(np.array([xs, ys]))

        return img

    def show_tracked_paramecium(self, img):
        pixel_per_um = 1.5
        from holypipette.gui import movingList
        x,y,norm = where_is_paramecium2(img, pixel_per_um = pixel_per_um, background = None, debug = True,
                                  previous_x = None, previous_y = None, max_dist = 1e6)
        if x is not None:
            if movingList.tracking == False:
                pass
            # Calculate variance of position
            if len(movingList.position_history) == movingList.position_history.maxlen:
                xpos, ypos = zip(*movingList.position_history)
                movement = (var(xpos) + var(ypos)) ** .5
                if movement < 1:  # 1 pixel
                    print
                    "Paramecium has stopped!"
                    movingList.paramecium_stop = True
                else:
                    movingList.position_history.clear()
            if (movingList.tracking == True)and(movingList.paramecium_stop == False):
                xs = x - self.camera.width / 2
                ys = y - self.camera.height / 2
                movingList.position_history.append((xs, ys))
        return img

    def pipette_contact_detection(self, img):
        from holypipette.gui import movingList
        height, width = img.shape[:2]
        pixel_per_um = 1.5
        x = width / 2
        y = height / 2
        size = int(15 / pixel_per_um)  # 30 um around tip
        framelet = img[y -size:y + size, x-size:x + size]

        #framelet = cv2.cvtColor(framelet, cv2.COLOR_BGR2GRAY)
        otsu, _ = cv2.threshold(framelet, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        ret, thresh = cv2.threshold(framelet, otsu, 255, cv2.THRESH_BINARY_INV)
        _, contours, _ = cv2.findContours(thresh, 1, 2)
        cnt = contours[0]
        x, y, w, h = cv2.boundingRect(cnt)
        if (w >= 1.8 * size) and (movingList.contact == False):
            movingList.contact = True
            print("Contact")
        return img

    @command(category='Camera',
             description='Select an object for automatic tracking')
    def track_object(self, position=None):
        # the position argument is only used when the action is triggered by a
        # mouse click -- we just ignore it
        img = self.camera.snap()
        cv2.namedWindow('target cell selection', cv2.WINDOW_AUTOSIZE)
        while True:
            cv2.imshow('target cell selection', img)
            bbox1 = cv2.selectROI('target cell selection', img)
            self.multitracker.add(cv2.TrackerKCF_create(), img, bbox1)
            cv2.destroyWindow('target cell selection')
            break
