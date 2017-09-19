import numbers
import operator
from fractions import Fraction

from pyltc.framerate import FrameRate, FrameFormat

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

cdef inline bint coerce_allowed(x, y):
    cdef object self, other
    self = x
    other = y
    # if isinstance(x, _Frame):
    #     self = x
    #     other = y
    # elif isinstance(y, _Frame):
    #     other = x
    #     self = y
    # else:
    #     return False
    if isinstance(other, _Frame):
        if self.frame_format != other.frame_format:
            return False
    elif not isinstance(other, numbers.Number):
        return False
    return True

cdef class Counter(object):
    cdef public object frame
    cdef public int _value
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
        self.set_value(int(value))
    cpdef set_value(self, int value):
        self._value = value
    def __iadd__(self, int i):
        while i > 0:
            self.incr()
            i -= 1
        return self
    def __isub__(self, int i):
        while i > 0:
            self.decr()
            i -= 1
        return self
    cpdef incr(self):
        self._value += 1
    cpdef decr(self):
        self._value -= 1

cdef class _Frame(Counter):
    cdef public object frame_format, second, minute, hour, df_frame_numbers, frame_times
    cdef public int total_frames
    cdef public bint drop_enabled
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
            self.df_frame_numbers = kwargs.get('df_frame_numbers', [])
        total_frames = kwargs.get('total_frames')
        if total_frames is not None:
            self.set_total_frames(total_frames)
        else:
            keys = ['hours', 'minutes', 'seconds', 'frames']
            hmsf = {k:kwargs.get(k) for k in keys if k in kwargs}
            if len(hmsf):
                self.set(**hmsf)
        if not hasattr(self, 'total_frames'):
            self.total_frames = self.calc_total_frames()
        fr = self.frame_format.rate.float_value
        self.frame_times = [i / fr for i in range(int(round(fr)))]
    cpdef incr(self):
        cdef int value
        self.total_frames += 1
        value = self.value + 1
        if value >= self.frame_format.rate.rounded:
            value = 0
            self.second += 1
        self.value = value
    cpdef decr(self):
        cdef int value
        self.total_frames -= 1
        value = self.value - 1
        decr_second = False
        if value < 0:
            decr_second = True
        elif self.frame_format.drop_frame and value in self.df_frame_numbers:
            if self.second.value == 0 and self.minute.value % 10 != 0:
                decr_second = True
        if decr_second:
            value = int(self.frame_format.rate.rounded - 1)
            self.second -= 1
        self.value = value
    cpdef set_value(self, int value):
        if self.drop_enabled and value in self.df_frame_numbers:
            value = self.df_frame_numbers[-1] + 1
        self._value = value
    def set(self, **kwargs):
        cdef object keys
        cdef int i
        keys = ['hours', 'minutes', 'seconds', 'frames']
        hmsf = self.get_hmsf_values()
        for i in range(4):
            if keys[i] in kwargs and kwargs[keys[i]] is not None:
                hmsf[i] = kwargs[keys[i]]
        self._set(hmsf)
    cpdef _set(self, hmsf):
        self.hour.value = hmsf[0]
        self.minute.value = hmsf[1]
        self.second.value = hmsf[2]
        self.check_drop()
        self.value = hmsf[3]
        self.total_frames = self.calc_total_frames()
    cpdef set_total_frames(self, int total_frames):
        cdef int Doffset, Moffset, drops_per_ten_minutes, drop_num, D, M, add_frames

        self.total_frames = total_frames
        fr = self.frame_format.rate
        if self.frame_format.drop_frame:
            Doffset = int(fr * 60 * 10)
            Moffset = int(fr * 60)
            drops_per_ten_minutes = int(fr.rounded * 60 * 10) - Doffset
            drop_num = len(self.df_frame_numbers)
            D = total_frames // Doffset
            M = total_frames % Doffset
            if M in self.df_frame_numbers:
                add_frames = drops_per_ten_minutes * D
            else:
                add_frames = drops_per_ten_minutes * D + drop_num * ((M - drop_num) // Moffset)
            if add_frames > 0:
                total_frames += add_frames

        self.hour.value = (((total_frames // fr.rounded) // 60) // 60) % 24
        self.minute.value = ((total_frames // fr.rounded) // 60) % 60
        self.second.value = (total_frames // fr.rounded) % 60
        self.value = total_frames % fr.rounded
        self.check_drop()
    cpdef calc_total_frames(self):
        cdef int seconds, frames, drop_num, total_dropped, total_minutes
        seconds = self.second.value
        seconds += self.minute.value * 60
        seconds += self.hour.value * 3600
        fr = self.frame_format.rate.rounded
        frames = seconds * fr
        frames += self.value

        if self.frame_format.drop_frame:
            total_minutes = 60 * self.hour.value + self.minute.value
            drop_num = len(self.df_frame_numbers)
            total_dropped = drop_num * (total_minutes - total_minutes // 10)
            frames -= total_dropped
        return frames
    cpdef check_drop(self):
        if not self.frame_format.drop_frame:
            return
        self.drop_enabled = self.second.value == 0 and self.minute.value % 10 != 0
    cpdef get_hmsf(self):
        cdef object l
        l = [
            self.hour,
            self.minute,
            self.second,
            self,
        ]
        return l
    cpdef get_hmsf_values(self):
        cdef object l
        l = [
            self.hour.value,
            self.minute.value,
            self.second.value,
            self.value,
        ]
        return l
    cpdef get_tc_string(self):
        return self.frame_format.format_tc_string(self.get_hmsf_values())
    cpdef _coerce_op(_Frame self, other, op):
        tf = op(int(self), int(other))
        return self.__class__(frame_format=self.frame_format, total_frames=tf)
    def __iadd__(_Frame self, other):
        cdef int total_frames
        total_frames = int(other)
        if total_frames == 1:
            self.incr()
        else:
            self.set_total_frames(self.total_frames + total_frames)
        return self
    def __isub__(_Frame self, other):
        cdef int total_frames
        total_frames = int(other)
        if total_frames == 1:
            self.decr()
        else:
            self.set_total_frames(self.total_frames - total_frames)
        return self
    def __int__(self):
        return self.total_frames
    def __richcmp__(_Frame self, other, int op):
        cdef int self_total_frames, other_total_frames, cmp_result
        self_total_frames = int(self)
        other_total_frames = int(other)
        if self_total_frames < other_total_frames:
            cmp_result = -1
        elif self_total_frames > other_total_frames:
            cmp_result = 1
        else:
            cmp_result = 0
        return richcmp_helper(cmp_result, op)
    def __add__(_Frame self, other): return self._coerce_op(other, operator.add)
    def __sub__(_Frame self, other): return self._coerce_op(other, operator.sub)
    def __repr__(self):
        return '{self.__class__.__name__}: {self} - {self.frame_format}'.format(self=self)
    def __str__(self):
        return self.get_tc_string()


cdef class Second(Counter):
    cpdef incr(self):
        cdef int value
        value = self.value + 1
        if value > 59:
            value = 0
            self.frame.minute += 1
        self.value = value
    cpdef decr(self):
        cdef int value
        value = self.value - 1
        if value < 0:
            value = 59
            self.frame.minute -= 1
        self.value = value
    cpdef set_value(self, int value):
        self._value = value
        self.frame.check_drop()

cdef class Minute(Counter):
    cpdef incr(self):
        cdef int value
        value = self.value + 1
        if value > 59:
            self.frame.hour += 1
            value = 0
        self.value = value
        self.frame.check_drop()
    cpdef decr(self):
        cdef int value
        value = self.value - 1
        if value < 0:
            value = 59
            self.frame.hour -= 1
        self.value = value

cdef class Hour(Counter):
    cpdef incr(self):
        self.value += 1
    cpdef decr(self):
        self.value -= 1
