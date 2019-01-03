from .base import TaskController
from time import sleep
from scipy.optimize import golden, minimize_scalar
from numpy import array,arange

class ParameciumController(TaskController):
    def __init__(self, calibrated_unit, microscope,
                 calibrated_stage, camera, config):
        super(ParameciumController, self).__init__()
        self.config = config
        self.calibrated_unit = calibrated_unit
        self.calibrated_stage = calibrated_stage
        self.microscope = microscope
        self.camera = camera
        self.paramecium_tank_position = None

    def autofocus(self, position):
        '''
        Autofocus on cell at the clicked position
        '''
        pixel_per_um = getattr(self.camera, 'pixel_per_um', None)
        if pixel_per_um is None:
            pixel_per_um = self.calibrated_unit.stage.pixel_per_um()[0]
        size = self.config.autofocus_size * pixel_per_um
        width, height = self.camera.width, self.camera.height

        x, y, z = position
        bracket = (z-100., z+100.) # 200 um around the current focus position

        def image_variance(z):
            self.microscope.absolute_move(z)
            sleep(self.config.autofocus_sleep) # more?
            image = self.camera.snap()
            frame = image[int(y + height / 2 - size / 2):int(y + height / 2 + size / 2),
                    int(x + width / 2 - size / 2):int(
                        x + width / 2 + size / 2)]  # is there a third dimension?
            variance = frame.var()
            return -variance

        z = golden(image_variance, brack = bracket, tol = 0.0001)
        #z = minimize_scalar(image_variance, bounds=bracket, tol=0.01, method='bounded')
        #zlist = arange(z-100., z+100.,20)
        #variances = -array([image_variance(z0) for z0 in zlist])
        #i = variances.argmax()
        #z = zlist[i]
        self.microscope.absolute_move(z)
        sleep(self.config.autofocus_sleep)

        relative_z = (z-self.microscope.floor_Z)*self.microscope.up_direction

        self.debug('Focused at position {} above floor'.format(relative_z))

    def contact_detection(self):
        '''
        Moves the pipette down until it touches water.

        Algorithm: move down in steps of 5 um until mean intensity has changed by at least
        one standard deviation.

        Note that the focus is untouched (maybe it should follow the tip?).
        '''
        step_size = 5. # in um
        self.info("Moving the pipette down until it touches water")

        # Region of interest = 20 x 20 um around pipette tip
        x,y,_ = self.calibrated_unit.reference_position()
        width, height = self.camera.width, self.camera.height
        pixel_per_um = getattr(self.camera, 'pixel_per_um', None)
        if pixel_per_um is None:
            pixel_per_um = self.calibrated_unit.stage.pixel_per_um()[0]
        frame_width = 50*pixel_per_um
        frame_height = 50*pixel_per_um

        # Refocus on tip
        #z = self.calibrated_unit.reference_position()[2]
        #self.microscope.absolute_move(z)
        #self.microscope.wait_until_still()

        # Take image of ROI
        image = self.camera.snap()
        frame = image[int(y+height/2-frame_height/2):int(y+height/2+frame_height/2),
                int(x+width/2-frame_width/2):int(x+width/2+frame_width/2)] # is there a third dimension?
        # Mean intensity and contrast of the image
        mean = mean0 = frame.mean()
        std = std0 = frame.std()

        i = 0
        while (std<std0*1.3) and (i<20):
            mean0=mean
            #z = self.calibrated_unit.reference_position()[2]
            self.calibrated_unit.relative_move(-step_size*self.calibrated_unit.up_direction[2], 2)
            #self.microscope.absolute_move(z)
            #self.calibrated_unit.wait_until_still(2)
            sleep(0.2)
            #self.microscope.wait_until_still()
            image = self.camera.snap()
            frame = image[int(y + height / 2 - frame_height / 2):int(y + height / 2 + frame_height / 2),
                    int(x + width / 2 - frame_width / 2):int(
                        x + width / 2 + frame_width / 2)]  # is there a third dimension?
            # Mean intensity and contrast of the image
            mean = frame.mean()
            std = frame.std()
            self.info('Mean = {}; Std = {}'.format(mean,std))
            i+=1
        if std>std0*1.5:
            self.info("Successful contact with water surface")
        else:
            self.info("Failed contact with water surface")


    #### Note: this is Hoang's code but we don't use for now

    def microdroplet_making(self):
        if self.paramecium_tank_position is None:
            raise ValueError('Paramecium tank has not been set')
        try:
            self.pressure.set_pressure(0)
            i = 0
            start_position = self.calibrated_unit.position()
            z0 = self.microscope.position()

            # Move the pipette to the paramecium tank.
            self.info('Moving the pipette to the paramecium tank')
            self.microscope.absolute_move(0)
            self.microscope.wait_until_still()
            self.calibrated_unit.absolute_move(start_position[0]+15000, 0)
            self.calibrated_unit.wait_until_still(0)
            self.calibrated_unit.absolute_move(start_position[2] - 5000, 2)
            self.calibrated_unit.wait_until_still(2)
            self.calibrated_unit.absolute_move(self.paramecium_tank_position[1], 1)
            self.calibrated_unit.wait_until_still(1)
            self.calibrated_unit.absolute_move(self.paramecium_tank_position[2] - 5000, 2)
            self.calibrated_unit.wait_until_still(2)
            self.calibrated_unit.absolute_move(self.paramecium_tank_position[0], 0)
            self.calibrated_unit.wait_until_still(0)
            self.calibrated_unit.absolute_move(self.paramecium_tank_position[2], 2)
            self.calibrated_unit.wait_until_still(2)

            #Take the liquid. Calculate later
            self.info('Taking liquid')
            self.pressure.set_pressure(-self.config.droplet_pressure)
            self.sleep(self.config.droplet_time*self.config.droplet_quantity)
            self.pressure.set_pressure(0)

            #
            # Move back.
            self.info('Moving back to original position')
            self.calibrated_unit.absolute_move(start_position[0] + 15000, 0)
            self.calibrated_unit.wait_until_still(0)
            self.calibrated_unit.absolute_move(start_position[2]-5000, 2)
            self.calibrated_unit.wait_until_still(2)
            self.calibrated_unit.absolute_move(start_position[1], 1)
            self.calibrated_unit.wait_until_still(1)
            self.calibrated_unit.absolute_move(start_position[2], 2)
            self.calibrated_unit.wait_until_still(2)

            self.calibrated_unit.absolute_move(start_position[0], 0)
            self.calibrated_unit.wait_until_still(0)
            self.microscope.absolute_move(z0)
            self.microscope.wait_until_still()

            self.info('Releasing liquid')
            self.pressure.set_pressure(self.config.droplet_pressure)
            self.sleep(self.config.droplet_time)

        finally:
            self.pressure.set_pressure(15)

    # def paramecium_movement(self):
    #     from holypipette.gui import movingList
    #     try:
    #         movingList.tracking = True
    #         while movingList.paramecium_stop is False:
    #             if len(movingList.position_history) > 1:
    #                 xs = movingList.position_history[-1][0]
    #                 ys = movingList.position_history[-1][1]
    #                 self.calibrated_stage.reference_move(self.calibrated_stage.reference_position() - np.array([xs, ys, 0]))
    #     finally:
    #         self.info("Paramecium stopped!")
    #
    # def paramecium_catching(self):
    #     from holypipette.gui import movingList
    #     try:
    #         if self.contact_position is None:
    #             print ("Please detect the contact position!")
    #         else:
    #             move_position = movingList.position_history[-1]
    #             self.calibrated_unit.safe_move(np.array([move_position[0], move_position[1], self.microscope.position()]) + self.microscope.up_direction * np.array([0, 0, 1.]) * 15, recalibrate=False)
    #             self.calibrated_unit.wait_until_still()
    #             self.calibrated_unit.absolute_move(self.contact_position[2],2)
    #             self.calibrated_unit.wait_until_still()
    #     finally:
    #         print("Paramecium immobilized!")
    #         movingList.paramecium_stop = False
    #         del movingList.position_history[:]
    #         movingList.tracking = False
