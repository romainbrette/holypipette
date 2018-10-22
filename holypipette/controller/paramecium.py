from .base import TaskController


class ParameciumController(TaskController):
    def __init__(self, calibrated_unit, microscope,
                 calibrated_stage, pressure, config):
        super(ParameciumController, self).__init__()
        self.config = config
        self.pressure = pressure
        self.calibrated_unit = calibrated_unit
        self.calibrated_stage = calibrated_stage
        self.microscope = microscope
        self.paramecium_tank_position = None

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
