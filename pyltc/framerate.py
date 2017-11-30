import numbers
import operator
from quicktions import Fraction

from pyltc._framerate import _FrameRate, _FrameFormat

class FrameRate(_FrameRate):
    _registry = {}
    def __new__(cls, numerator, denom=1):
        key = Fraction(numerator, denom)
        if key in cls._registry:
            return cls._registry[key]
        obj = super(FrameRate, cls).__new__(cls)
        cls._registry[key] = obj
        return obj

class FrameFormat(_FrameFormat):
    def __init__(self, **kwargs):
        rate = kwargs.get('rate')
        if isinstance(rate, numbers.Number):
            rate = FrameRate.from_float(rate)
            kwargs['rate'] = rate
        super(FrameFormat, self).__init__(**kwargs)
