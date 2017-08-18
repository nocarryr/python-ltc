import numbers
import operator
from fractions import Fraction

class FrameRate(object):
    defaults = {
        24:(24, 1),
        25:(25, 1),
        29.97:(30000, 1001),
        30:(30, 1),
        59.94:(60000, 1001),
        60:(60, 1),
    }
    _registry = {}
    def __new__(cls, numerator, denom=1):
        key = Fraction(numerator, denom)
        if key in cls._registry:
            return cls._registry[key]
        obj = super(FrameRate, cls).__new__(cls)
        cls._registry[key] = obj
        return obj
    def __init__(self, numerator, denom=1):
        self.__numerator = numerator
        self.__denom = denom
        self.__value = Fraction(numerator, denom)
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
        return float(self.value)
    @property
    def rounded(self):
        if self.denom == 1:
            return self.numerator
        return round(self.value)
    def _coerce_value(self, other):
        if isinstance(other, FrameRate):
            return other.value
        elif isinstance(other, (numbers.Number, Fraction)):
            return other
        return NotImplemented
    def _coerce_op(self, other, op, reverse_op=False):
        other = self._coerce_value(other)
        if other is NotImplemented:
            return NotImplemented
        if reverse_op:
            return op(other, self.value)
        return op(self.value, other)
    def _rcoerce_op(self, other, op):
        return self._coerce_op(other, op, reverse_op=True)
    def __eq__(self, other): return self._coerce_op(other, operator.eq)
    def __ne__(self, other): return self._coerce_op(other, operator.ne)
    def __lt__(self, other): return self._coerce_op(other, operator.lt)
    def __le__(self, other): return self._coerce_op(other, operator.le)
    def __gt__(self, other): return self._coerce_op(other, operator.gt)
    def __ge__(self, other): return self._coerce_op(other, operator.ge)
    def __mul__(self, other): return self._coerce_op(other, operator.mul)
    def __rmul__(self, other): return self._rcoerce_op(other, operator.mul)
    def __div__(self, other): return self._coerce_op(other, operator.div)
    def __rdiv__(self, other): return self._rcoerce_op(other, operator.div)
    def __truediv__(self, other): return self._coerce_op(other, operator.truediv)
    def __rtruediv__(self, other): return self._rcoerce_op(other, operator.truediv)
    def __floordiv__(self, other): return self._coerce_op(other, operator.floordiv)
    def __rfloordiv__(self, other): return self._rcoerce_op(other, operator.floordiv)
    def __mod__(self, other): return self._coerce_op(other, operator.mod)
    def __rmod__(self, other): return self._rcoerce_op(other, operator.mod)
    def __repr__(self):
        return '<FrameRate: {self} ({self.numerator}/{self.denom})>'.format(self=self)
    def __str__(self):
        if self.denom == 1:
            return str(self.numerator)
        return '{:05.2f}'.format(self.float_value)

class FrameFormat(object):
    def __init__(self, **kwargs):
        rate = kwargs.get('rate')
        if isinstance(rate, numbers.Number):
            rate = FrameRate.from_float(rate)
        self.rate = rate
        self.drop_frame = kwargs.get('drop_frame')
    def __repr__(self):
        return '{self.__class__.__name__}: {self}'.format(self=self)
    def __str__(self):
        if self.drop_frame:
            s = 'Drop'
        else:
            s = 'Non-Drop'
        return '{}fps ({})'.format(self.rate, self.drop_frame)

class Counter(object):
    def __init__(self, **kwargs):
        self.frame = kwargs.get('frame')
        self._value = 0
    @property
    def value(self):
        v = getattr(self, '_value', None)
        if v is None:
            v = self._value = 0
        return v
    @value.setter
    def value(self, value):
        self.set_value(value)
    def set_value(self, value):
        self._value = value
    def __iadd__(self, i):
        while i > 0:
            self.incr()
            i -= 1
        return self
    def __isub__(self, i):
        while i > 0:
            self.decr()
            i -= 1
        return self
    def __repr__(self):
        return '{self.__class__.__name__}: {self}'.format(self=self)
    def __str__(self):
        return '%02d' % (self.value)

class Frame(Counter):
    def __init__(self, **kwargs):
        self.frame_format = kwargs.get('frame_format')
        self._value = 0
        self.second = Second(frame=self)
        self.minute = Minute(frame=self)
        self.hour = Hour(frame=self)
        self.drop_enabled = False
        if self.frame_format.rate.rounded == 30:
            self.df_frame_numbers = (0, 1)
        elif self.frame_format.rate.rounded == 60:
            self.df_frame_numbers = (0, 1, 2, 3)
        else:
            self.df_frame_numbers = []
        total_frames = kwargs.get('total_frames')
        if total_frames is not None:
            self.total_frames = total_frames
        else:
            keys = ['hours', 'minutes', 'seconds', 'frames']
            hmsf = {k:kwargs.get(k) for k in keys if k in kwargs}
            if len(hmsf):
                self.set(**hmsf)
        if not hasattr(self, 'total_frames'):
            self.total_frames = 0
        fr = self.frame_format.rate.float_value
        self.frame_times = [i / fr for i in range(int(round(fr)))]
    def incr(self):
        self.total_frames += 1
        value = self.value + 1
        if value >= self.frame_format.rate.rounded:
            value = 0
            self.second += 1
        self.value = value
    def decr(self):
        self.total_frames -= 1
        value = self.value - 1
        decr_second = False
        if value < 0:
            decr_second = True
        elif self.frame_format.drop_frame and value in self.df_frame_numbers:
            if self.minute.value % 10 != 0:
                decr_second = True
        if decr_second:
            value = int(self.frame_format.rate.rounded - 1)
            self.second -= 1
        self.value = value
    def set_value(self, value):
        if self.drop_enabled and value in self.df_frame_numbers:
            value = self.df_frame_numbers[-1] + 1
        self._value = value
    def set(self, **kwargs):
        keys = ['hours', 'minutes', 'seconds']
        hmsf = {k:kwargs.get(k) for k in keys if k in kwargs}
        for key in keys:
            if key not in kwargs:
                continue
            if key == 'frames':
                obj = self
            else:
                attr = key.rstrip('s')
                obj = getattr(self, attr)
            obj.value = kwargs[key]
        self.check_drop()
        self.value = kwargs.get('frames', self.value)
        self.total_frames = self.calc_total_frames()
    def from_dt(self, dt):
        keys = ['hours', 'minutes', 'seconds']
        d = {k: getattr(dt, k.rstrip('s')) for k in keys}
        d['frames'] = self.microseconds_to_frame(dt.microsecond)
        self.set(**d)
    def microseconds_to_frame(self, microseconds):
        fr = self.frame_format.rate.float_value
        s = microseconds / 1e6
        l = self.frame_times
        if s in l:
            return l.index(s)
        closest = None
        for i, f in enumerate(l):
            if closest is None or f < s:
                closest = f
            elif f > s:
                if f - s < s - closest:
                    return i
                return i - 1
    def calc_total_frames(self):
        seconds = self.second.value
        seconds += self.minute.value % 60
        seconds += self.hour.value * 3600
        fr = self.frame_format.rate.rounded
        frames = seconds * fr
        frames += self.value
        return frames
    def check_drop(self):
        if not self.frame_format.drop_frame:
            return
        drop = self.minute.value % 10 != 0
        self.drop_enabled = drop
    def get_hmsf(self):
        l = []
        for attr in ['hour', 'minute', 'second']:
            l.append(getattr(self, attr))
        l.append(self)
        return l
    def get_tc_string(self):
        return ':'.join([str(obj) for obj in self.get_hmsf()])
    def copy(self):
        f = Frame(frame_format=self.frame_format, total_frames=self.total_frames)
        f._value = self._value
        f.second._value = self.second._value
        f.minute._value = self.minute._value
        f.hour._value = self.hour._value
        return f

class Second(Counter):
    def incr(self):
        value = self.value + 1
        if value > 59:
            value = 0
            self.frame.minute += 1
        self.value = value
    def decr(self):
        value = self.value - 1
        if value < 0:
            value = 59
            self.frame.minute -= 1
        self.value = value
    def set_value(self, value):
        self._value = value
        self.frame.check_drop()

class Minute(Counter):
    def incr(self):
        value = self.value + 1
        if value > 59:
            self.frame.hour += 1
            value = 0
        self.value = value
        self.frame.check_drop()
    def decr(self):
        value = self.value - 1
        if value < 0:
            value = 59
            self.frame.hour -= 1
        self.value = value

class Hour(Counter):
    def incr(self):
        self.value += 1
    def decr(self):
        self.value -= 1
