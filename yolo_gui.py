'''
This GUI only shows the camera image, without any additional controls (stage,
manipulators, pressure controller, etc.)
'''
import os
import sys

from PyQt5 import QtWidgets

from holypipette.log_utils import console_logger
from holypipette.gui import CameraGui

from setup_script import *

console_logger()  # Log to the standard console as well

class YoloTracker():
    def __init__(self, yolo_path, weights, device='', conf_thres=0.35, iou_thres=0.45, max_det=1000):
        self.detections = None
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
    

    def detect(self, image):
        from utils.general import check_img_size, non_max_suppression
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
        w, h = self.imgsz
        return np.array([[p[0]/w, p[1]/h, (p[2] - p[0])/w, (p[3] - p[1])/h]
                         for p in pred[0]])

    def receive_image(self, image):
        # TODO process image
        import time
        start = time.time()
        print('Start processing image')
        self.detections = self.detect(image)
        took = time.time() - start
        print('Detected {} Paramecia in {:.2f}s'.format(len(self.detections), took))
        print(self.detections)

        return image

    def mark_cells(self, pixmap):
        from PyQt5 import QtGui, QtCore
        painter = QtGui.QPainter(pixmap)
        pen = QtGui.QPen(QtGui.QColor(0, 200, 0, 125))
        pen.setWidth(2)
        pen.setCosmetic(True)  # width independent of scaling
        painter.setPen(pen)
        painter.scale(pixmap.width(), pixmap.height())
        for d in self.detections:
            box = QtCore.QRectF(*d)
            painter.drawRect(box)
        painter.end()

yolo_tracker = YoloTracker(yolo_path='/home/marcel/programming/Paramecium-deeplearning/yolov5', weights='/home/marcel/programming/Paramecium-deeplearning/best.pt') 

app = QtWidgets.QApplication(sys.argv)
gui = CameraGui(camera,
                image_edit=yolo_tracker.receive_image,
                display_edit=yolo_tracker.mark_cells)
gui.initialize()
gui.show()
ret = app.exec_()

sys.exit(ret)
