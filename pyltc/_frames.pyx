import numbers
import operator

from pyltc.framerate import FrameRate, FrameFormat

HMSF_KEYS = ('hours', 'minutes', 'seconds', 'frames')

cdef inline dict hmsf_from_kwargs(dict kwargs):
    cdef str key
    return {key:kwargs.get(key) for key in HMSF_KEYS if key in kwargs}

cdef inline dict hmsf_to_dict(list hmsf):
    cdef str key
    cdef int val
    return {key:val for key, val in zip(HMSF_KEYS, hmsf)}

cdef inline list hmsf_dict_to_list(dict hmsf_dict):
    cdef str key
    return [hmsf_dict.get(key) for key in HMSF_KEYS]

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

cdef class Counter(object):
    cdef public object frame
    cdef public int _value
    def __cinit__(self, **kwargs):
        self.frame = kwargs.get('frame')
        self._value = 0
    @property
    def value(self):
        return self._value
    @value.setter
    def value(self, int value):
        self.set_value(value)
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
    cdef public object frame_format
    cdef public Second second
    cdef public Minute minute
    cdef public Hour hour
    cdef public list df_frame_numbers, frame_times
    cdef public int total_frames
    cdef public bint drop_enabled
    def __cinit__(self, **kwargs):
        cdef object total_frames
        cdef dict hmsf
        self.frame_format = kwargs.get('frame_format')
        self._value = 0
        self.second = Second(frame=self)
        self.minute = Minute(frame=self)
        self.hour = Hour(frame=self)
        self.drop_enabled = False
        if self.frame_format.rate.rounded == 30:
            self.df_frame_numbers = [0, 1]
        elif self.frame_format.rate.rounded == 60:
            self.df_frame_numbers = [0, 1, 2, 3]
        else:
            self.df_frame_numbers = kwargs.get('df_frame_numbers', [])
        total_frames = kwargs.get('total_frames')
        if total_frames is not None:
            self.set_total_frames(total_frames)
        else:
            hmsf = hmsf_from_kwargs(kwargs)
            if len(hmsf):
                self.set(**hmsf)
        if not hasattr(self, 'total_frames'):
            self.total_frames = self.calc_total_frames()
        self.frame_times = self._build_frame_times()
    cdef list _build_frame_times(self):
        cdef float fr = self.frame_format.rate.float_value
        cdef int i
        return [i / fr for i in range(int(round(fr)))]
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
        cdef bint decr_second
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
        self._set_from_kwargs(kwargs)
    cdef _set_from_kwargs(self, dict kwargs):
        cdef list hmsf_list = self.get_hmsf_values()
        cdef dict hmsf_dict
        cdef str key

        hmsf_dict = hmsf_to_dict(hmsf_list)
        for key in HMSF_KEYS:
            if key in kwargs and kwargs[key] is not None:
                hmsf_dict[key] = kwargs[key]

        hmsf_list = hmsf_dict_to_list(hmsf_dict)
        self._set(hmsf_list)
    cpdef _set(self, list hmsf):
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
        cdef int fr = self.frame_format.rate.rounded
        seconds = self.second.value
        seconds += self.minute.value * 60
        seconds += self.hour.value * 3600
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
        cdef list l
        l = [
            self.hour,
            self.minute,
            self.second,
            self,
        ]
        return l
    cpdef get_hmsf_values(self):
        cdef list l
        l = [
            self.hour.value,
            self.minute.value,
            self.second.value,
            self.value,
        ]
        return l
    cpdef get_tc_string(self):
        cdef list hmsf = self.get_hmsf_values()
        return self.frame_format.format_tc_string(hmsf)
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
    def __add__(_Frame self, other):
        cdef int total_frames
        total_frames = int(self) + int(other)
        return self.__class__(frame_format=self.frame_format, total_frames=total_frames)
    def __sub__(_Frame self, other):
        cdef int total_frames
        total_frames = int(self) - int(other)
        return self.__class__(frame_format=self.frame_format, total_frames=total_frames)
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
