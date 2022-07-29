"""
GUI for tracking Paramecia.

Adds a tracking button to the standard camera GUI, and uses the
image_edit and display_edit functionality to detect Paramecia and
annotate them in the display.
"""
from PyQt5 import QtWidgets
import qtawesome as qta

from . import CameraGui


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
        self.setWindowTitle("Tracking GUI")
    
    def toggle_tracking(self):
        if self.track_button.isChecked():
            self.tracker.start()
        else:
            self.tracker.stop()
