
class FrameFormat(object):
    def __init__(self, **kwargs):
        self.rate = kwargs.get('rate')
        self.rate_rounded = int(round(self.rate))
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
        fr = float(self.frame_format.rate)
        self.frame_times = [i / fr for i in range(int(round(fr)))]
    def incr(self):
        self.total_frames += 1
        value = self.value + 1
        if value > self.frame_format.rate:
            value = 0
            self.second += 1
        self.value = value
    def set_value(self, value):
        if value in [0, 1] and self.drop_enabled:
            value = 2
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
        fr = float(self.frame_format.rate)
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
        fr = self.frame_format.rate_rounded
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
        if value >= 59:
            value = 0
            self.frame.minute += 1
        self.value = value

class Minute(Counter):
    def incr(self):
        value = self.value + 1
        if value >= 59:
            self.frame.hour += 1
            value = 0
        self.value = value
        self.frame.check_drop()

class Hour(Counter):
    def incr(self):
        self.value += 1
