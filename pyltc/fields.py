class Field(object):
    start_bit = None
    bit_length = 1
    def __init__(self, **kwargs):
        self.generator = kwargs.get('generator')
        self._value = kwargs.get('value', 0)
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
    def set_array(self, a):
        v = [c == '1' for c in reversed(bin(self.value)[2:])]
        while len(v) < self.bit_length:
            v.append(False)
        i = range(self.start_bit, self.start_bit + self.bit_length)
        a.put(i, v)
    def get_block_value(self):
        return self.value << self.start_bit
    def get_value(self):
        return self._value
    def set_value(self, value):
        self._value = value
    def __repr__(self):
        return '{self.__class__.__name__}: {self.value}'.format(self=self)
    def __str__(self):
        return str(self.value)

class FrameUnits(Field):
    start_bit = 0
    bit_length = 4
    def get_value(self):
        return self.generator.frame.value % 10

class FrameTens(Field):
    start_bit = 8
    bit_length = 2
    def get_value(self):
        return self.generator.frame.value // 10

class SecondUnits(Field):
    start_bit = 16
    bit_length = 4
    def get_value(self):
        return self.generator.frame.second.value % 10

class SecondTens(Field):
    start_bit = 24
    bit_length = 3
    def get_value(self):
        return self.generator.frame.second.value // 10

class MinuteUnits(Field):
    start_bit = 32
    bit_length = 4
    def get_value(self):
        return self.generator.frame.minute.value % 10

class MinuteTens(Field):
    start_bit = 40
    bit_length = 3
    def get_value(self):
        return self.generator.frame.minute.value // 10

class HourUnits(Field):
    start_bit = 48
    bit_length = 4
    def get_value(self):
        return self.generator.frame.hour.value % 10

class HourTens(Field):
    start_bit = 56
    bit_length = 2
    def get_value(self):
        return self.generator.frame.hour.value // 10

class DropFlag(Field):
    start_bit = 10
    def __init__(self, **kwargs):
        super(DropFlag, self).__init__(**kwargs)
        if self.generator.frame_format.drop_frame:
            self._value = 1

class ColorFrameFlag(Field):
    start_bit = 11
    def __init__(self, **kwargs):
        super(ColorFrameFlag, self).__init__(**kwargs)
        self._value = 1

class ParityBit(Field):
    start_bit = 27

class BinaryGroupLSB(Field):
    start_bit = 43

class BinaryGroupMSB(Field):
    start_bit = 59

class SyncWord(Field):
    start_bit = 64
    bit_length = 16
    def __init__(self, **kwargs):
        super(SyncWord, self).__init__(**kwargs)
        self._value = 0x3FFD
