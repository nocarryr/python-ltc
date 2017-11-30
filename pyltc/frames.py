from pyltc.framerate import FrameRate, FrameFormat
from pyltc._frames import _Frame, Second, Minute, Hour


class Frame(_Frame):
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
    def copy(self):
        return self.__class__(
            frame_format=self.frame_format,
            total_frames=self.total_frames,
        )
