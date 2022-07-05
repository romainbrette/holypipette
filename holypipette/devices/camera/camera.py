'''
A generic camera class

TODO:
* A stack() method which takes a series of photos along Z axis
'''
from __future__ import print_function
import collections
import os
import time
import threading
import imageio

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage.filters import gaussian_filter
from scipy.ndimage import fourier_gaussian
import warnings
from scipy.optimize import brentq
try:
    import cv2
except:
    warnings.warn('OpenCV not available')
from PIL import Image

__all__ = ['Camera', 'FakeCamera', 'RecordedVideoCamera']


class FileWriteThread(threading.Thread): # saves frames individually
    def __init__(self, *args, **kwds):
        self.queue = kwds.pop('queue')
        self.debug_write_delay = kwds.pop('debug_write_delay', 0)
        self.directory = kwds.pop('directory')
        self.file_prefix = kwds.pop('file_prefix')
        threading.Thread.__init__(self, *args, **kwds)
        self.first_frame = None
        self.running = True

    def write_frame(self):
        frame_number, elapsed_time, frame = self.queue.popleft()
        if frame_number is None:
            # Marker for end of recording
            return False
        
        # Make all frame numbers relative to the first frame
        if self.first_frame is None:
            self.first_frame = frame_number
        frame_number -= self.first_frame
        fname = os.path.join(self.directory, '{}_{:05d}.tiff'.format(self.file_prefix, frame_number))
        imageio.imwrite(fname, frame)
        time.sleep(self.debug_write_delay)
        if frame_number % 20 == 0:
            print('Finished writing {}.'.format(fname))
        return True

    def run(self):
        self.running = True
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        
        while self.running:
            try:
                if len(self.queue) > self.queue.maxlen // 2:
                    print('WARNING: FileWriteThread queue is getting full ({}/{)'.format(len(self.queue),
                                                                                         self.queue.maxlen))
                if not self.write_frame():
                    break
            except IndexError:
                # queue is emtpy, wait
                time.sleep(0.01)
                # TODO: Store image metadata to file as well?

        if len(self.queue):
            print('Still need to write {} images to disk.'.format(len(self.queue)))
            while True:
                if not self.write_frame():
                    break


class AcquisitionThread(threading.Thread):
    def __init__(self, camera, queues):
        self.camera = camera
        self.queues = queues
        self.running = True

        threading.Thread.__init__(self, name='image_acquire_thread')

    def run(self):
        self.running = True

        start_time = time.time()
        last_frame = 0
        while self.running:
            frame = self.camera.raw_snap()
            # Put image into queues for disk storage and display
            for queue in self.queues:
                queue.append((last_frame, time.time() - start_time, frame))
            last_frame += 1
        
        # Put the end marker into the queues
        for queue in self.queues:
            queue.append((None, None, None))


class Camera(object):
    """
    Base class for all camera devices. At the end of the initialization, derived classes need to
    call self.start_acquisition() to start the thread that continously acquires images from the
    camera.
    """
    def __init__(self):
        super(Camera, self).__init__()
        self._file_queue = collections.deque(maxlen=1000)
        self._last_frame_queue = collections.deque(maxlen=1)
        self._acquisition_thread = None
        self._file_thread = None
        self._debug_write_delay = 0
        self.width = 1000
        self.height = 1000
        self.flipped = False # Horizontal flip

    def start_acquisition(self):
        self._acquisition_thread = AcquisitionThread(camera=self,
                                                     queues=[self._file_queue,
                                                             self._last_frame_queue])
        self._acquisition_thread.start()
    
    def stop_acquisition(self):
        self._acquisition_thread.running = False

    def start_recording(self, directory='', file_prefix=''):
        self._file_queue.clear()
        self._file_thread = FileWriteThread(queue=self._file_queue,
                                            directory=directory,
                                            file_prefix=file_prefix,
                                            debug_write_delay=self._debug_write_delay)
        self._file_thread.start()

    def stop_recording(self):
        if self._file_thread:
            self._file_thread.running = False

    def flip(self):
        self.flipped = not self.flipped

    def preprocess(self, img):
        if self.flipped:
            if len(img.shape)==2:
                return np.array(img[:,::-1])
            else:
                return np.array(img[:,::-1,:])
        else:
            return img

    def new_frame(self):
        '''
        Returns True if a new frame is available
        '''
        return True

    def snap(self):
        '''
        Returns the current image
        '''
        return self.preprocess(self.raw_snap())

    def raw_snap(self):
        return None

    def last_frame(self):
        '''
        Get the last snapped frame.
        '''
        try:
            return self.preprocess(self._last_frame_queue[0][-1])
        except IndexError:  # no frame (yet)
            return None

    def close(self):
        """Shut down the camera device, free resources, etc."""
        pass

    def set_exposure(self, value):
        print('Setting exposure time not supported for this camera')

    def get_exposure(self):
        print('Getting exposure time not supported for this camera')
        return -1

    def change_exposure(self, change):
        if self.get_exposure() > 0:
            self.set_exposure(self.get_exposure() + change)

    def auto_exposure(self):
        '''
        Auto exposure assumes frames are 8 bits.
        '''
        mean_luminance = 127

        def f(value):
            self.set_exposure(value)
            time.sleep(.2+.001*value) # wait for new frame with updated value
            while not self.new_frame():
                time.sleep(0.05)
            m = self.snap().mean()
            return m-mean_luminance
        exposure = brentq(f, 0.1,100., rtol=0.1)
        self.set_exposure(exposure)

    def reset(self):
        pass


class FakeParamecium(object):
    def __init__(self):
        self.position = np.array([0., 0., 0.])
        self.center = np.array([0., 0., 0.])
        self.velocity = 200  # um per second
        self.sigma = 1
        self._last_update = time.time()
        self.angle = 0

    def update_position(self):
        dt = time.time() - self._last_update
        self._last_update = time.time()
        to_center = np.arctan2(self.position[1], self.position[0])
        bias = (self.position[0]**2 + self.position[1]**2)/20000  # bias is quadratic function of distance
        angle = self.angle + dt*(self.sigma*np.random.randn() +
                                 bias*((to_center - self.angle + np.pi) % (2*np.pi) - np.pi))
        self.angle = (angle + np.pi) % (2*np.pi) - np.pi
        self.position += self.velocity*dt*np.array([np.cos(self.angle), np.sin(self.angle), 0.0])


class FakeCamera(Camera):
    def __init__(self, manipulator=None, image_z=0, paramecium=False):
        super(FakeCamera, self).__init__()
        self.width = 1024
        self.height = 768
        self.exposure_time = 30
        self.manipulator = manipulator
        self.image_z = image_z
        self.scale_factor = .5  # micrometers in pixels
        self.depth_of_field = 2.
        if paramecium:
            self.paramecium = FakeParamecium()
        else:
            self.paramecium = None
        self.frame = np.array(np.clip(gaussian_filter(np.random.randn(self.width * 2, self.height * 2)*0.5, 10)*50 + 128, 0, 255), dtype=np.uint8)
        
        self.start_acquisition()

    def set_exposure(self, value):
        if 0 < value <= 200:
            self.exposure_time = value

    def get_exposure(self):
        return self.exposure_time

    def get_microscope_image(self, x, y, z):
        frame = np.roll(self.frame, int(y), axis=0)
        frame = np.roll(frame, int(x), axis=1)
        frame = frame[self.height//2:self.height//2+self.height,
                      self.width//2:self.width//2+self.width]
        return np.array(frame, copy=True)

    def raw_snap(self):
        '''
        Returns the current image.
        This is a blocking call (wait until next frame is available)
        '''
        if self.manipulator is not None:
            # Use the part of the image under the microscope

            stage_x, stage_y, stage_z = self.manipulator.position_group([7, 8, 9])
            stage_z -= self.image_z
            stage_x *= self.scale_factor
            stage_y *= self.scale_factor
            stage_z *= self.scale_factor
            frame = self.get_microscope_image(stage_x, stage_y, stage_z)
            if self.paramecium is not None:
                self.paramecium.update_position()
                p_x, p_y, p_z = self.paramecium.position
                p_angle = self.paramecium.angle + np.pi/2
                p_x *= self.scale_factor
                p_y *= self.scale_factor
                p_z *= self.scale_factor
                # FIXME: do not ignore Z
                p_width = 30*self.scale_factor
                p_height = 100*self.scale_factor
                xx, yy = np.meshgrid(np.arange(-self.width//2, self.width//2), np.arange(-self.height//2, self.height//2))
                frame[((xx - (p_x - stage_x))*np.cos(p_angle) + (yy - (p_y - stage_y))*np.sin(p_angle))**2 / (p_width/2)**2 +
                      ((xx - (p_x - stage_x))*np.sin(p_angle) - (yy - (p_y - stage_y))*np.cos(p_angle))**2 / (p_height/2)**2 < 1] = 50
                frame[((xx - (p_x - stage_x))*np.cos(p_angle) + (yy - (p_y - stage_y))*np.sin(p_angle))**2 / (p_width/2)**2 +
                      ((xx - (p_x - stage_x))*np.sin(p_angle) - (yy - (p_y - stage_y))*np.cos(p_angle))**2 / (p_height/2)**2 < 0.8] = 100

            for direction, axes in [(np.pi/2, [1, 2, 3]),
                                    (-np.pi/2, [4, 5, 6])]:
                manipulators = np.zeros((self.height, self.width), dtype=np.int16)
                x, y, z = self.manipulator.position_group(axes)
                # Quick&dirty 3D transformation
                x = np.cos(self.manipulator.angle)*(x + 50/self.scale_factor)
                z = np.sin(self.manipulator.angle)*(x + 50/self.scale_factor) + z
                # scale
                x *= self.scale_factor
                y *= self.scale_factor
                z *= self.scale_factor
                # cut off a tip
                # Position relative to stage
                x -= stage_x
                y -= stage_y
                z -= stage_z
                X, Y = np.meshgrid(np.arange(self.width) - self.width/2 + x,
                                   np.arange(self.height) - self.height/2 + y)
                angle = np.arctan2(X, Y)
                dist = np.sqrt(X**2 + Y**2)
                border = (0.075 + 0.0025 * abs(z) / self.depth_of_field)
                manipulators[(np.abs(angle - direction) < border) & (dist > 50)] = 5
                edge_width = 0.02 if z > 0 else 0.04  # Make a distinction between below and above
                manipulators[(np.abs(angle - direction) < border) & (np.abs(angle - direction) > border-edge_width) & (dist > 50)] = 75
                frame[manipulators>0] = manipulators[manipulators>0]
        else:
            img = Image.fromarray(self.frame)
            frame = np.array(img.resize((self.width, self.height)))
        exposure_factor = self.exposure_time/30.
        frame = frame + np.random.randn(self.height, self.width)*5
        return np.array(np.clip(frame*exposure_factor, 0, 255),
                        dtype=np.uint8)


def text_phantom(text, size):
    # Availability is platform dependent
    font = 'Arial'
    
    # Create font
    pil_font = ImageFont.truetype(font + ".ttf", size=size[0] // len(text),
                                  encoding="unic")
    text_width, text_height = pil_font.getsize(text)

    # create a blank canvas with extra space between lines
    canvas = Image.new('RGB', size, (0, 0, 0))

    # draw the text onto the canvas
    draw = ImageDraw.Draw(canvas)
    offset = ((size[0] - text_width) // 2,
              (size[1] - text_height) // 2)
    white = "#ffffff"
    draw.text(offset, text, font=pil_font, fill=white)

    # Convert the canvas into an array with values in [0, 1]
    frame = np.asarray(canvas)
    return frame


class DebugCamera(Camera):
    '''A fake camera that shows the frame number'''
    def __init__(self, frames_per_s=20, write_delay=0):
        super(DebugCamera, self).__init__()
        self.width = 1024
        self.height = 768
        self.frameno = 0
        self.last_frame_time = None
        self.delay = 1/frames_per_s
        self._debug_write_delay=write_delay
        self.start_acquisition()

    def raw_snap(self):
        '''
        Returns the current image.
        This is a blocking call (wait until next frame is available)
        '''
        frame = text_phantom('{:05d}'.format(self.frameno), (self.width, self.height))
        self.frameno += 1
        if self.last_frame_time is not None:
            if time.time() - self.last_frame_time < self.delay:
                time.sleep(self.delay - (time.time() - self.last_frame_time))
        self.last_frame_time = time.time()
        return frame
        

class RecordedVideoCamera(Camera):
    def __init__(self, file_name, pixel_per_um, slowdown=1):
        super(RecordedVideoCamera, self).__init__()
        self.file_name = file_name
        self.video = cv2.VideoCapture(file_name)
        self.video.open(self.file_name)
        self.width = int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.pixel_per_um = pixel_per_um
        self.frame_rate = self.video.get(cv2.CAP_PROP_FPS)
        self.time_between_frames = 1/self.frame_rate * slowdown
        self._last_frame_time = None
        self.start_acquisition()

    def raw_snap(self):
        if self._last_frame_time is not None:
            if time.time() - self._last_frame_time < self.time_between_frames:
                # We are too fast, sleep a bit before returning the frame
                sleep_time = self.time_between_frames - (time.time() - self._last_frame_time)
                time.sleep(sleep_time)
        success, frame = self.video.read()
        self._last_frame_time = time.time()        
        
        if not success and self._acquisition_thread.running:
            raise ValueError('Cannot read from file %s.' % self.file_name)
        
        return frame

    def close(self):
        self.video.release()
        super(RecordedVideoCamera, self).close()
