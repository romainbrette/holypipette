'''
This GUI only shows the camera image, without any additional controls (stage,
manipulators, pressure controller, etc.)
'''
import os
import sys

import numpy as np
from PyQt5 import QtWidgets
import qtawesome as qta

from holypipette.config import Config, Integer, Boolean
from holypipette.log_utils import console_logger
from holypipette.gui import CameraGui

from setup_script import *

console_logger()  # Log to the standard console as well

class TrackerConfig(Config):
    crop = Boolean(default=True, doc='Crop central part of video?')
    crop_x = Integer(1016, bounds=(0, None), doc='x of cropping area')
    crop_y = Integer(848, bounds=(0, None), doc='y of cropping area')
    crop_width = Integer(416, bounds=(0, None), doc='width of cropping area')
    crop_height = Integer(352, bounds=(0, None), doc='height of cropping area')

    categories = [('Image', ['crop', 'crop_x', 'crop_y', 'crop_width', 'crop_height'])]


class YoloTracker():
    def __init__(self, yolo_path, weights, device='', conf_thres=0.35, iou_thres=0.45, max_det=1000):
        self.config = TrackerConfig(name='Tracking')
        self.detections = None
        self.metadata = None
        # Ugly hack, but yolov5 is not packaged properly
        import sys
        sys.path.append(yolo_path)

        from models.common import DetectMultiBackend
        from utils.datasets import IMG_FORMATS, VID_FORMATS, LoadImages, LoadStreams
        from utils.general import (LOGGER, check_file, check_img_size, check_imshow, check_requirements, colorstr, cv2,
                                increment_path, non_max_suppression, print_args, scale_coords, strip_optimizer, xyxy2xywh)
        from utils.plots import Annotator, colors, save_one_box
        from utils.torch_utils import select_device, time_sync
        # Load model
        self.device = select_device(device)
        data = os.path.join(yolo_path, 'data/coco128.yaml')
        self.model = DetectMultiBackend(weights, device=self.device, dnn=False, data=data, fp16=False)
        self.stride, self.names, self.pt = self.model.stride, self.model.names, self.model.pt
        self.imgsz = None
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        self.max_det = max_det
        self.do_track = False
    

    def detect(self, image):
        from utils.general import check_img_size, non_max_suppression
        if self.config.crop and (image.shape[0] > self.config.crop_height or image.shape[1] > self.config.crop_width):
            start_row, end_row = self.config.crop_y, self.config.crop_y + self.config.crop_height
            start_col, end_col = self.config.crop_x, self.config.crop_x + self.config.crop_width
            # Crop area (x, y, w, h) in relative values
            crop_rect = np.array([start_col/image.shape[1], start_row/image.shape[0], (end_col-start_col)/image.shape[1], (end_row-start_row)/image.shape[0]])
            image = image[start_row:end_row, start_col:end_col, :]
        else:
            crop_rect = None
        
        # Convert
        image = image.transpose((2, 0, 1))
        image = np.ascontiguousarray(image)

        if self.imgsz is None:  # first run
            self.imgsz = check_img_size(image.shape[1:], s=self.stride)  # check image size
            self.model.warmup(imgsz=(1, 3, *self.imgsz))  # warmup

        import torch

        im = torch.from_numpy(image).to(self.device)
        im = im.half() if self.model.fp16 else im.float()  # uint8 to fp16/32
        im /= 255  # 0 - 255 to 0.0 - 1.0
        if len(im.shape) == 3:
            im = im[None]  # expand for batch dim
        pred = self.model(im, augment=False, visualize=False)
        # NMS
        pred = non_max_suppression(pred, self.conf_thres, self.iou_thres, max_det=self.max_det)
        # Return bounding boxes of predictions as relative to image size
        h, w = self.imgsz
        boxes = np.array([[p[0]/w, p[1]/h, (p[2] - p[0])/w, (p[3] - p[1])/h]
                           for p in pred[0].cpu()])

        if boxes.size:
            dist_to_center = np.sqrt((boxes[:, 0] + boxes[:, 2]/2 - 0.5)**2 + (boxes[:, 1] + boxes[:, 3]/2 - 0.5)**2)
            confidence = np.array(p[4] for p in pred[0])
            meta_data = {'dist_to_center': dist_to_center, 'confidence': confidence, 'crop_rect': crop_rect}
        else:
            meta_data = {'dist_to_center': np.array([]), 'confidence': np.array([]), 'crop_rect': crop_rect}
        return boxes, meta_data

    def receive_image(self, image):
        if not self.do_track:
            return image
        import time
        start = time.time()
        self.detections, self.metadata = self.detect(image)
        took = time.time() - start
        print('Detected {} Paramecia in {:.2f}s'.format(len(self.detections), took))

        return image

    def mark_cells(self, pixmap):
        if not self.do_track:
            return
        from PyQt5 import QtGui, QtCore

        painter = QtGui.QPainter(pixmap)
        if self.metadata.get('crop_rect', None) is not None:
            x, y, w, h = self.metadata['crop_rect']
            # show cropping area
            pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 50))
            pen.setWidth(3)
            painter.setPen(pen)
            box = QtCore.QRectF(round(pixmap.width()*x), round(pixmap.height()*y), round(pixmap.width()*w), round(pixmap.height()*h))
            painter.drawRect(box)

            # plot to cropped area
            painter.translate(round(pixmap.width()*x), round(pixmap.height()*y))
            painter.scale(round(pixmap.width()*w), round(pixmap.height()*h))
        else:
            painter.scale(pixmap.width(), pixmap.height())

        if not len(self.detections):
            return

        pen = QtGui.QPen(QtGui.QColor(0, 200, 0, 125))
        pen.setWidth(2)
        pen.setCosmetic(True)  # width independent of scaling
        pen_highlight = QtGui.QPen(QtGui.QColor(200, 0, 0, 125))
        pen_highlight.setWidth(2)
        pen_highlight.setCosmetic(True)  # width independent of scaling
        distances = self.metadata['dist_to_center']
        min_idx = np.argmin(distances)
        for idx, d in enumerate(self.detections):
            if idx == min_idx:
                painter.setPen(pen_highlight)
            else:
                painter.setPen(pen)
            box = QtCore.QRectF(*d)
            painter.drawRect(box)
        painter.end()

yolo_tracker = YoloTracker(yolo_path='/home/marcel/programming/Paramecium-deeplearning/yolov5', weights='/home/marcel/programming/Paramecium-deeplearning/best.pt') 

class TrackerGui(CameraGui):
    def __init__(self, camera, tracker):
        super(TrackerGui, self).__init__(camera,
                                         image_edit=tracker.receive_image,
                                         display_edit=tracker.mark_cells)
        self.add_config_gui(tracker.config)
        self.tracker = tracker
        self.track_button = QtWidgets.QToolButton(clicked=self.toggle_tracking)
        self.track_button.setIcon(qta.icon('fa.eye'))
        self.track_button.setCheckable(True)
        self.track_button.setToolTip('Toggle tracking')
        self.status_bar.addPermanentWidget(self.track_button)
    
    def toggle_tracking(self):
        self.tracker.do_track = self.track_button.isChecked()

app = QtWidgets.QApplication(sys.argv)
gui = TrackerGui(camera, yolo_tracker)
gui.initialize()
gui.show()
ret = app.exec_()

sys.exit(ret)
