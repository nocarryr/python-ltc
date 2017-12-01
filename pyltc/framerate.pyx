import numbers
import operator
from quicktions import Fraction

cdef inline bint richcmp_helper(int compare, int op):
    if op == 2: # ==
        return compare == 0
    elif op == 3: # !=
        return compare != 0
    elif op == 0: # <
        return compare < 0
    elif op == 1: # <=
        return compare <= 0
    elif op == 4: # >
        return compare > 0
    elif op == 5: # >=
        return compare >= 0

cdef dict FRAME_TIMES = {}
cdef dict FRAME_RATE_REGISTRY = {}

cdef class FrameRate(object):
    defaults = {
        24:(24, 1),
        25:(25, 1),
        29.97:(30000, 1001),
        30:(30, 1),
        59.94:(60000, 1001),
        60:(60, 1),
    }
    cdef int __numerator, __denom, __rounded
    cdef object __value
    cdef float __float_value
    def __init__(self, int numerator, int denom=1):
        self.__numerator = numerator
        self.__denom = denom
        if self.denom == 1:
            self.__value = Fraction(numerator, denom)
            self.__rounded = numerator
        else:
            self.__value = Fraction(numerator, denom)
            self.__rounded = round(self.__value)
        self.__float_value = float(self.__value)
    @classmethod
    def create(cls, int numerator, int denom=1):
        key = Fraction(numerator, denom)
        if key in FRAME_RATE_REGISTRY:
            return FRAME_RATE_REGISTRY[key]
        obj = cls(numerator, denom)
        FRAME_RATE_REGISTRY[key] = obj
        return obj
    @staticmethod
    def _get_registry():
        return FRAME_RATE_REGISTRY
    @classmethod
    def from_float(cls, value):
        if value not in cls.defaults:
            raise Exception('FrameRate definition not found for {}'.format(value))
        numerator, denom = cls.defaults[value]
        return cls.create(numerator, denom)
    @property
    def numerator(self):
        return self.__numerator
    @property
    def denom(self):
        return self.__denom
    @property
    def value(self):
        return self.__value
    @property
    def float_value(self):
        if self.denom == 1:
            return self.__numerator
        return self.__float_value
    @property
    def rounded(self):
        return self.__rounded
    @property
    def frame_times(self):
        cdef list frame_times
        if self.__value in FRAME_TIMES:
            frame_times = FRAME_TIMES[self.__value]
        else:
            frame_times = self._build_frame_times()
            FRAME_TIMES[self.__value] = frame_times
        return frame_times
    cdef list _build_frame_times(self):
        cdef float fr = self.__float_value
        cdef int i
        return [i / fr for i in range(int(round(fr)))]
    def __richcmp__(FrameRate self, other, op):
        cdef int cmp_result
        cdef object other_value
        if isinstance(other, FrameRate):
            other_value = other.value
        elif isinstance(other, (numbers.Number, Fraction)):
            other_value = other
        else:
            return NotImplemented
        if self.value < other_value:
            cmp_result = -1
        elif self.value > other_value:
            cmp_result = 1
        else:
            cmp_result = 0
        return richcmp_helper(cmp_result, op)
    def __mul__(self, other):
        if not isinstance(self, FrameRate):
            return self * other.value
        if isinstance(other, FrameRate):
            other = other.value
        return self.value * other
    def __div__(self, other):
        if not isinstance(self, FrameRate):
            return self / other.value
        if isinstance(other, FrameRate):
            other = other.value
        return self.value / other
    def __truediv__(self, other):
        if not isinstance(self, FrameRate):
            return self / other.value
        if isinstance(other, FrameRate):
            other = other.value
        return self.value / other
    def __floordiv__(self, other):
        if not isinstance(self, FrameRate):
            return self // other.value
        if isinstance(other, FrameRate):
            other = other.value
        return self.value // other
    def __mod__(self, other):
        if not isinstance(self, FrameRate):
            return self % other.value
        if isinstance(other, FrameRate):
            other = other.value
        return self.value % other
    def __repr__(self):
        return '<FrameRate: {self} ({self.numerator}/{self.denom})>'.format(self=self)
    def __str__(self):
        if self.denom == 1:
            return str(self.numerator)
        return '{:05.2f}'.format(self.float_value)

cdef class FrameFormat(object):
    cdef public FrameRate rate
    cdef public bint drop_frame
    cdef public char *tc_fmt_str
    def __init__(self, **kwargs):
        cdef object rate
        rate = kwargs.get('rate')
        if isinstance(rate, numbers.Number):
            rate = FrameRate.from_float(rate)
        self.rate = rate
        self.drop_frame = kwargs.get('drop_frame', False)
        if self.drop_frame:
            self.tc_fmt_str = '{:02d}:{:02d}:{:02d};{:02d}'
        else:
            self.tc_fmt_str = '{:02d}:{:02d}:{:02d}:{:02d}'
    cpdef format_tc_string(self, hmsf):
        return self.tc_fmt_str.decode('UTF-8').format(*hmsf)
    def __richcmp__(FrameFormat self, FrameFormat other, int op):
        cdef object eq
        eq = False
        if self.drop_frame is other.drop_frame:
            if self.rate == other.rate:
                eq = True
        if op == 2:
            return eq
        elif op == 3:
            return not eq
        else:
            return False
    def __repr__(self):
        return '{self.__class__.__name__}: {self}'.format(self=self)
    def __str__(self):
        if self.drop_frame:
            s = 'Drop'
        else:
            s = 'Non-Drop'
        return '{}fps ({})'.format(self.rate, s)
