'''
Support for configuration objects (based on the param package)
'''
import warnings
try:
    import yaml
except ImportError:
    warnings.warn('Could not import pyyaml, will not be able to save or load configuration files')

import param
from param import Number, Boolean  # to make it available for import

class NumberWithUnit(param.Number):
    __slots__ = ['unit', 'magnitude']

    def __init__(self, default, unit, magnitude=1.0, *args, **kwds):
        super(NumberWithUnit, self).__init__(default=default, *args, **kwds)
        self.unit = unit
        self.magnitude = magnitude


class Config(param.Parameterized):
    def __init__(self, value_changed=None, *args, **kwds):
        super(Config, self).__init__(*args, **kwds)
        self._value_changed = value_changed

    def __setattr__(self, key, value):
        super(Config, self).__setattr__(key, value)
        if not key.startswith('_') and getattr(self, '_value_changed', None) is not None:
            self._value_changed(key, value)

    def to_dict(self):
        return {name: getattr(self, name) for name in self.params()
                if name != 'name'}

    def from_dict(self, config_dict):
        for name, value in config_dict.items():
            setattr(self, name, value)

    def to_file(self, filename):
        config_dict = self.to_dict()
        with open(filename, 'w') as f:
            yaml.dump(config_dict, f)

    def from_file(self, filename):
        with open(filename, 'r') as f:
            config_dict = yaml.load(f)
        self.from_dict(config_dict)
