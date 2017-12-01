import numpy as np
cimport numpy as np

BOOL_DTYPE = np.bool

cdef class Field(object):
    cdef public object generator
    cdef int _value
    cdef int start_bit, bit_length
    def __init__(self, **kwargs):
        self.generator = kwargs.get('generator')
        self._value = kwargs.get('value', 0)
        self.start_bit = self.__class__._start_bit
        self.bit_length = getattr(self, '_bit_length', 1)
    @classmethod
    def iter_subclasses(cls):
        for _cls in cls.__subclasses__():
            yield _cls
    @property
    def value(self):
        return self.get_value()
    @value.setter
    def value(self, value):
        self.set_value(value)
    cpdef set_array(self, np.ndarray a):
        cdef list v = [c == '1' for c in reversed(bin(self.value)[2:])]
        while len(v) < self.bit_length:
            v.append(False)
        a[self.start_bit:self.start_bit+self.bit_length] = v
    cpdef get_block_value(self):
        return self.value << self.start_bit
    cpdef get_value(self):
        return self._value
    cpdef set_value(self, int value):
        self._value = value
    def __repr__(self):
        return '{self.__class__.__name__}: {self.value}'.format(self=self)
    def __str__(self):
        return str(self.value)

cdef class FrameUnits(Field):
    _start_bit = 0
    _bit_length = 4
    cpdef get_value(self):
        return self.generator.frame.value % 10

cdef class FrameTens(Field):
    _start_bit = 8
    _bit_length = 2
    cpdef get_value(self):
        return self.generator.frame.value // 10

cdef class SecondUnits(Field):
    _start_bit = 16
    _bit_length = 4
    cpdef get_value(self):
        return self.generator.frame.second.value % 10

cdef class SecondTens(Field):
    _start_bit = 24
    _bit_length = 3
    cpdef get_value(self):
        return self.generator.frame.second.value // 10

cdef class MinuteUnits(Field):
    _start_bit = 32
    _bit_length = 4
    cpdef get_value(self):
        return self.generator.frame.minute.value % 10

cdef class MinuteTens(Field):
    _start_bit = 40
    _bit_length = 3
    cpdef get_value(self):
        return self.generator.frame.minute.value // 10

cdef class HourUnits(Field):
    _start_bit = 48
    _bit_length = 4
    cpdef get_value(self):
        return self.generator.frame.hour.value % 10

cdef class HourTens(Field):
    _start_bit = 56
    _bit_length = 2
    cpdef get_value(self):
        return self.generator.frame.hour.value // 10

cdef class DropFlag(Field):
    _start_bit = 10
    def __init__(self, **kwargs):
        super(DropFlag, self).__init__(**kwargs)
        if self.generator.frame_format.drop_frame:
            self._value = 1

cdef class ColorFrameFlag(Field):
    _start_bit = 11
    def __init__(self, **kwargs):
        super(ColorFrameFlag, self).__init__(**kwargs)
        self._value = 1

cdef class ParityBit(Field):
    _start_bit = 27

cdef class BinaryGroupLSB(Field):
    _start_bit = 43

cdef class BinaryGroupMSB(Field):
    _start_bit = 59

cdef class SyncWord(Field):
    _start_bit = 64
    _bit_length = 16
    def __init__(self, **kwargs):
        super(SyncWord, self).__init__(**kwargs)
        self._value = 0xBFFC

cdef class LTCDataBlock(object):
    cdef public object generator
    cdef public dict fields
    def __init__(self, **kwargs):
        self.generator = kwargs.get('generator')
        self.fields = {}
        for cls in Field.iter_subclasses():
            field = cls(generator=self.generator)
            self.fields[cls.__name__] = field
    cpdef get_value(self):
        cdef int v = 0
        cdef object field
        for field in self.fields.values():
            v += field.get_block_value()
        return v
    cpdef str get_string(self):
        cdef int v = self.get_value()
        cdef str s = bin(v)
        if s.count('0') % 2 == 1:
            v += 1 << ParityBit._start_bit
            s = bin(v)
        return s[2:]
    cpdef np.ndarray get_array(self):
        cdef np.ndarray a
        cdef object field
        a = np.zeros(80, dtype=BOOL_DTYPE)
        for field in self.fields.values():
            field.set_array(a)
        if np.count_nonzero(a) % 2 == 1:
            a[ParityBit._start_bit] = True
        return a
