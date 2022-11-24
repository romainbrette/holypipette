'''
A camera class that watches for new TIFF files and displays them.
'''
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .camera import *
import cv2

__all__ = ['WatchdogCamera']

class TIFFMonitor(FileSystemEventHandler):
    def __init__(self):
        super(WatchdogCamera, self).__init__()
        self.image = None

    def on_created(self, event):
        filename = event.src_path
        if '.tif' in filename:
            self.image = cv2.imread(filename)

class WatchdogCamera(Camera):
    '''
    A camera that looks for new created TIFF files
    '''
    def __init__(self, path, pixel_per_um):
        super(WatchdogCamera, self).__init__()
        self.path = path
        self.pixel_per_um = pixel_per_um

        self.observer = Observer()
        self.monitor = TIFFMonitor()
        self.observer.start()
        self.observer.schedule(self.monitor, path, recursive=True)

    def raw_snap(self):
        frame = None
        return self.monitor.image

    def __del__(self):
        self.observer.stop()
        self.observer.join()
