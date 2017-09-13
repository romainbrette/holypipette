'''
Live camera feed with mouse callback

Requires OpenCV
'''
from threading import Thread
import cv2

__all__ = ['LiveFeed','insert_cross']

def insert_cross(img):
    """
    Plots a red cross at the center of the image.
    """
    img = img.copy()
    height, width = img.shape[:2]
    cv2.line(img, (width / 2 + 10, height / 2), (width / 2 - 10, height / 2), (0, 0, 255))
    cv2.line(img, (width / 2, height / 2 + 10), (width / 2, height / 2 - 10), (0, 0, 255))
    return img


class LiveFeed(Thread):
    """
    A live camera feed.
    """

    def __init__(self, camera, mouse_callback = None, editing = insert_cross, title='Camera'):
        '''
        Live camera feed

        Parameters
        ----------
        camera : camera object, ie with a snap() method
        mouse_callback : function called on mouse click
        editing : image editing function (eg add a cross)
        title : title of window
        '''
        # Init thread
        Thread.__init__(self)

        # Init camera device
        self.cam = camera

        # Initializing variables for display
        self.frame = None # current frame
        self.width, self.height = self.cam.width, self.cam.height
        self.title = title
        self.show = True

        # OnMouse function when clicking on the window
        self.mouse_callback = mouse_callback
        self.editing = editing

        cv2.namedWindow(self.title, flags=cv2.WINDOW_NORMAL) # in init() maybe?
        if self.mouse_callback is not None:
            cv2.setMouseCallback(self.title, self.mouse_callback)
        self.start()

    def run(self):
        """
        Thread run, display camera frames
        """
        while self.show: # is that necessary?
            if self.cam.new_frame():
                # Get image and convert
                frame = self.cam.snap()
                #frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                # Convert to 8 bit gray scale # why? and shouldn't be done on Camera level?
                if frame.dtype == 'uint16':
                    self.frame = cv2.convertScaleAbs(frame, alpha=2**-2)
                else:
                    self.frame = cv2.convertScaleAbs(frame)

                # Display the image with editing (to add a cross, etc)
                cv2.imshow(self.title, self.editing(self.frame))
                cv2.waitKey(1) # displays image for 1 ms

        # End of Thread
        cv2.destroyAllWindows()

    def stop(self):
        self.show = False
