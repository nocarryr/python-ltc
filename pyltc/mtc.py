
class MTCField(object):
    def __init__(self, **kwargs):
        self.value = kwargs.get('value', 0)
    @property
    def value(self):
        return self.get_value()
    @value.setter
    def value(self, value):
        self.set_value(value)
    def get_value(self):
        return getattr(self, '_value', 0)
    def set_value(self, value):
        self._value = value
    @classmethod
    def iter_subclasses(cls):
        for _cls in cls.__subclasses__():
            yield _cls
    def decode(self, values):
        v = 0
        for value in values:
            index = value >> 4
            value = value - (index << 4)
            if index == self.index[0]:
                v += value
            elif index == self.index[1]:
                v += self.decode_msb(value)
        self.value = v
    def decode_msb(self, value):
        return value << 4
    def __repr__(self):
        return '{self.__class__.__name__}: {self}'.format(self=self)
    def __str__(self):
        return '{:02d}'.format(self.value)

class Frame(MTCField):
    index = [0, 1]
    def get_value(self):
        value = getattr(self, '_value', 0)
        return value + 2

class Second(MTCField):
    index = [2, 3]

class Minute(MTCField):
    index = [4, 5]

class Hour(MTCField):
    index = [6, 7]
    def decode_msb(self, value):
        return (value & 0x01) << 4

class FrameRate(MTCField):
    index = [7]
    value_map = [
        [24, False],
        [25, False],
        [30, True],
        [30, False],
    ]
    def __init__(self, **kwargs):
        self.rate = kwargs.get('rate')
        self.drop_frame = kwargs.get('drop_frame', False)
    def get_value(self):
        return {k:getattr(self, k) for k in ['rate', 'drop_frame']}
    def set_value(self, value):
        if isinstance(value, list):
            self.rate, self.drop_frame = value
        elif isinstance(value, dict):
            for key in ['rate', 'drop_frame']:
                v = value.get(key)
                if v is not None:
                    setattr(self, key, v)
    def decode(self, values):
        for value in values:
            index = value >> 4
            value = value - (index << 4)
            if index != 7:
                continue
            value = value >> 2
            try:
                l = self.value_map[value]
            except IndexError:
                l = [None, None]
            self.rate, self.drop_frame = l
    def __str__(self):
        if self.drop_frame:
            s = 'df'
        else:
            s = ''
        return '{}{}'.format(self.rate, s)


class MTCDataBlock(object):
    def __init__(self, **kwargs):
        self.fields = {}
        self.field_index_map = {}
        for cls in MTCField.iter_subclasses():
            attr = cls.__name__.lower()
            f = cls(value=kwargs.get(attr, 0))
            self.fields[attr] = f
            for i in f.index:
                if i not in self.field_index_map:
                    self.field_index_map[i] = {}
                self.field_index_map[i][attr] = f
            setattr(self, attr, f)
    def decode(self, data):
        field_data = {k:[] for k in self.fields.keys()}
        for i, value in enumerate(data):
            if value != 0xF1:
                continue
            value = data[i+1]
            index = value >> 4
            for key in self.field_index_map[index].keys():
                field_data[key].append(value)
        for key, values in field_data.items():
            f = self.fields[key]
            f.decode(values)
    def get_hmsf(self):
        keys = ['hour', 'minute', 'second', 'frame']
        return [self.fields[key].value for key in keys]
    def __str__(self):
        keys = ['hour', 'minute', 'second', 'frame']
        return ':'.join([str(self.fields[key]) for key in keys])
