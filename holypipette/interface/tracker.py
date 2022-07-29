"""
Module defining the code to track paramecia via a Yolov5 network.
"""
import os
import numpy as np

from holypipette.config import Config, Number, Integer, Boolean, Filename


class TrackerConfig(Config):
    crop = Boolean(default=True, doc='Crop video?')
    crop_x = Integer(1016, bounds=(0, None), doc='x of cropping area')
    crop_y = Integer(848, bounds=(0, None), doc='y of cropping area')
    crop_width = Integer(416, bounds=(0, None), doc='width of cropping area')
    crop_height = Integer(352, bounds=(0, None), doc='height of cropping area')
    only_show_cropped = Boolean(default=False, doc='Only show cropped video?')

    move_stage = Boolean(default=False, doc='Move stage to track?')
    max_displacement = Integer(default=10, bounds=(0, None), doc='Max displacement in pixel')

    weights = Filename(None, doc='Filename for trained weights')

    conf_threshold = Number(0.35, bounds=(0, 1), doc='Confidence threshold')
    iou_threshold = Number(0.45, bounds=(0, 1), doc='IoU threshold')
    max_detections = Integer(1000, bounds=(0, None), doc='Maximum detections')

    categories = [('Image', ['crop', 'crop_x', 'crop_y', 'crop_width', 'crop_height', 'only_show_cropped']),
                  ('Movement', ['move_stage', 'max_displacement']),
                  ('Network', ['weights']),
                  ('Parameters', ['conf_threshold', 'iou_threshold', 'max_detections'])
                  ]


class YoloTracker(object):
    def __init__(self, yolo_path, device=''):
        self.config = TrackerConfig(name='Tracking')
        # Little hack to have a default file name
        default_weights = os.path.join(yolo_path, '..', 'best.pt')
        if os.path.exists(default_weights):
            self.config.weights = default_weights
        self.detections = None
        self.metadata = None
        # Ugly hack, but yolov5 is not packaged properly
        import sys
        sys.path.append(yolo_path)
        from utils.torch_utils import select_device
        self.yolo_path = yolo_path
        # Load model
        self.device = select_device(device)
        self.do_track = False
    
    def initialize(self, iou_thres=0.45, max_det=1000):
        from models.common import DetectMultiBackend
        data = os.path.join(self.yolo_path, 'data/coco128.yaml')
        self.model = DetectMultiBackend(self.config.weights, device=self.device, dnn=False, data=data, fp16=False)
        self.stride, self.names, self.pt = self.model.stride, self.model.names, self.model.pt
        self.imgsz = None
        self.conf_thres = self.config.conf_threshold
        self.iou_thres = self.config.iou_threshold
        self.max_det = max_det
    
    def start(self):
        self.initialize()
        self.do_track = True

    def stop(self):
        self.do_track = False

    def detect(self, image):
        from utils.general import check_img_size, non_max_suppression
        if self.config.crop and (image.shape[0] > self.config.crop_height or image.shape[1] > self.config.crop_width):
            start_row, end_row = self.config.crop_y, self.config.crop_y + self.config.crop_height
            start_col, end_col = self.config.crop_x, self.config.crop_x + self.config.crop_width
            # Crop area (x, y, w, h) in relative values
            crop_rect = np.array([start_col/image.shape[1], start_row/image.shape[0], (end_col-start_col)/image.shape[1], (end_row-start_row)/image.shape[0]])
            image = image[start_row:end_row, start_col:end_col]
        else:
            crop_rect = None
        
        # Convert
        if image.ndim == 3:
            image = image.transpose((2, 0, 1))
        else:
            # weights were trained on color images, so repeat the values for RGB
            image = np.tile(image[None, :, :], (3, 1, 1))
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
            confidence = np.array([p[4] for p in pred[0].cpu()])
            meta_data = {'dist_to_center': dist_to_center, 'confidence': confidence, 'crop_rect': crop_rect}
        else:
            meta_data = {'dist_to_center': np.array([]), 'confidence': np.array([]), 'crop_rect': crop_rect}
        return boxes, meta_data

    def receive_image(self, image):
        if not self.do_track:
            if self.config.only_show_cropped:
                print(self.config.crop_y, self.config.crop_x, self.config.crop_width, self.config.crop_height)
                return np.array(image[self.config.crop_y:self.config.crop_y+self.config.crop_height,
                                      self.config.crop_x:self.config.crop_x+self.config.crop_width,
                                      :])
            else:
                return image
        import time
        start = time.time()
        self.detections, self.metadata = self.detect(image)
        # Make sure that the "stage move" does not invalidate our detection coordinates
        crop_x, crop_y, crop_width, crop_height = self.config.crop_x, self.config.crop_y, self.config.crop_width, self.config.crop_height
        if len(self.detections) and self.config.move_stage:
            distances = self.metadata['dist_to_center']
            min_idx = np.argmin(distances)
            # Move crop area so that the object is in the center
            move_x = min(int((self.detections[min_idx, 0] - 0.5) * self.config.crop_width), self.config.max_displacement)
            self.config.crop_x = int(np.clip(self.config.crop_x + move_x, 0, image.shape[1]-self.config.crop_width))
            move_y = min(int((self.detections[min_idx, 1] - 0.5) * self.config.crop_height), self.config.max_displacement)
            self.config.crop_y = int(np.clip(self.config.crop_y + move_y, 0, image.shape[0]-self.config.crop_height))
            
        took = time.time() - start
        print('Detected {} Paramecia in {:.2f}s (confidence: {})'.format(len(self.detections),
                                                                         took,
                                                                         ', '.join('{:.2f}'.format(c) for c in self.metadata['confidence'])))
        if self.config.only_show_cropped:
            return np.array(image[crop_y:crop_y+crop_height, crop_x:crop_x+crop_width])
        else:
            return image

    def mark_cells(self, pixmap):
        if not self.do_track:
            return
        from PyQt5 import QtGui, QtCore

        painter = QtGui.QPainter(pixmap)
        if self.metadata.get('crop_rect', None) is not None and not self.config.only_show_cropped:
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

        pen_outside = QtGui.QPen(QtGui.QColor(64, 83, 211, 125))
        pen_outside.setWidth(2)
        pen_outside.setCosmetic(True)  # width independent of scaling
        pen_center = QtGui.QPen(QtGui.QColor(221, 179, 16, 125))
        pen_center.setWidth(2)
        pen_center.setCosmetic(True)  # width independent of scaling
        distances = self.metadata['dist_to_center']
        min_idx = np.argmin(distances)
        for idx, d in enumerate(self.detections):
            if idx == min_idx:
                pen = pen_center
            else:
                pen = pen_outside
            # Modulate transparency by confidence level → confidence 0 = transparent, confidence 1 = opaque
            if 'confidence' in self.metadata:
                c = pen.color()
                c.setAlpha(round(self.metadata['confidence'][idx]*255))
            painter.setPen(pen)
            box = QtCore.QRectF(*d)
            painter.drawRect(box)
        painter.end()
