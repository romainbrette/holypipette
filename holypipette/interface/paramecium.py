from holypipette.config import Config, NumberWithUnit, Number, Boolean
from holypipette.controller.paramecium import ParameciumController
from holypipette.interface import TaskInterface, command, blocking_command


class ParameciumConfig(Config):
    droplet_quantity = Number(1, bounds=(1, 100), doc='Number of microdroplets to make')
    droplet_pressure = NumberWithUnit(15, bounds=(-1000, 1000), doc='Pressure to make droplet', unit='mbar')
    droplet_time = NumberWithUnit(5, bounds=(0, 100), doc='Necessary time to make one droplet', unit='s')

    categories = [('Droplets', ['droplet_quantity', 'droplet_pressure', 'droplet_time'])]


class ParameciumInterface(TaskInterface):

    def __init__(self, calibrated_unit, microscope, calibrated_stage, pressure):
        super(ParameciumInterface, self).__init__()
        self.config = ParameciumConfig(name='Paramecium')
        # TODO: Make this work correctly with changes in the selected manipulator
        self.calibrated_unit = calibrated_unit
        self.calibrated_stage = calibrated_stage
        self.microscope = microscope
        self.pressure = pressure
        self.controller = ParameciumController(calibrated_unit, microscope,
                                               calibrated_stage, pressure,
                                               self.config)

    @command(category='Paramecium',
             description='Store the position of the paramecium tank')
    def store_paramecium_position(self):
        self.controller.paramecium_tank_position = self.calibrated_unit.position()
        self.info('Paramecium tank position stored')

    @blocking_command(category='Paramecium',
                      description='Microdroplet making for paramecium '
                                  'patch clamp',
                      task_description='Microdroplet making')
    def microdroplet_making(self):
        self.execute(self.controller, 'microdroplet_making')

    @blocking_command(category='Paramecium',
                      description='Calibrated stage moving to compensate the '
                                  'movement of paramecium',
                      task_description='Paramecium tracking')
    def paramecium_movement(self):
        self.execute(self.controller, 'paramecium_movement')

    @blocking_command(category='Paramecium',
                      description='Moving down the calibrated manipulator to '
                                  'hold the paramecium',
                      task_description='Paramecium immobilization')
    def paramecium_catching(self):
        self.execute(self.controller, 'paramecium_catching')
