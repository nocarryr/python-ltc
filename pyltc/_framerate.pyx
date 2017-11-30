import numbers
import operator
from fractions import Fraction

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

cdef class _FrameRate(object):
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
    def from_float(cls, value):
        if value not in cls.defaults:
            raise Exception('FrameRate definition not found for {}'.format(value))
        numerator, denom = cls.defaults[value]
        return cls(numerator, denom)
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
    def __richcmp__(_FrameRate self, other, op):
        cdef int cmp_result
        cdef object other_value
        if isinstance(other, _FrameRate):
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
        if not isinstance(self, _FrameRate):
            return self * other.value
        if isinstance(other, _FrameRate):
            other = other.value
        return self.value * other
    def __div__(self, other):
        if not isinstance(self, _FrameRate):
            return self / other.value
        if isinstance(other, _FrameRate):
            other = other.value
        return self.value / other
    def __truediv__(self, other):
        if not isinstance(self, _FrameRate):
            return self / other.value
        if isinstance(other, _FrameRate):
            other = other.value
        return self.value / other
    def __floordiv__(self, other):
        if not isinstance(self, _FrameRate):
            return self // other.value
        if isinstance(other, _FrameRate):
            other = other.value
        return self.value // other
    def __mod__(self, other):
        if not isinstance(self, _FrameRate):
            return self % other.value
        if isinstance(other, _FrameRate):
            other = other.value
        return self.value % other
    def __repr__(self):
        return '<FrameRate: {self} ({self.numerator}/{self.denom})>'.format(self=self)
    def __str__(self):
        if self.denom == 1:
            return str(self.numerator)
        return '{:05.2f}'.format(self.float_value)

cdef class _FrameFormat(object):
    cdef public object rate
    cdef public bint drop_frame
    cdef public char *tc_fmt_str
    def __init__(self, **kwargs):
        rate = kwargs.get('rate')
        if isinstance(rate, numbers.Number):
            rate = _FrameRate.from_float(rate)
        self.rate = rate
        self.drop_frame = kwargs.get('drop_frame')
        if self.drop_frame:
            self.tc_fmt_str = '{:02d}:{:02d}:{:02d};{:02d}'
        else:
            self.tc_fmt_str = '{:02d}:{:02d}:{:02d}:{:02d}'
    cpdef format_tc_string(self, hmsf):
        return self.tc_fmt_str.decode('UTF-8').format(*hmsf)
    def __richcmp__(_FrameFormat self, _FrameFormat other, int op):
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
