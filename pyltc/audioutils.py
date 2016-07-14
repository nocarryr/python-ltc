import wave

import numpy as np
from scipy.interpolate import interp1d
from scipy import signal
import scipy.io.wavfile as wavfile


class Resampler(object):
    def __init__(self, **kwargs):
        self.out_sample_rate = kwargs.get('out_sample_rate')
        self.in_sample_rate = kwargs.get('in_sample_rate')
        self.in_periods = np.arange(0, 1, 1 / float(self.in_sample_rate))
        self.out_periods = np.arange(0, 1, 1 / float(self.out_sample_rate))
        self.nans = np.full(self.in_periods.size, np.nan)
        self.bit_depth = int(kwargs.get('bit_depth', 16))
        self.dtype = np.dtype('>i{}'.format(int(self.bit_depth / 8)))
        self.y_max = int((1 << self.bit_depth) / 2 - 1)
        self.y_min = self.y_max * -1
    def resample(self, a):
        if self.in_sample_rate == self.out_sample_rate:
            return a
        if a.size < self.in_periods.size:
            a = np.concatenate((a, self.nans))[:self.in_periods.size]
            strip_nans = True
        else:
            strip_nans = False
        f = interp1d(self.in_periods, a, bounds_error=False, fill_value=np.nan)
        x = self.out_periods
        r = f(x)
        if strip_nans:
            r = r[~np.isnan(r)]
        if r.dtype is not self.dtype:
            r = np.asarray(r, dtype=self.dtype)
        return r
    def write_wavefile(self, a, filename):
        wavfile.write(filename, self.out_sample_rate, a)

class FrameResampler(Resampler):
    def __init__(self, **kwargs):
        self.frame_rate = float(kwargs.get('frame_rate'))
        self.frame_samples = int(self.frame_rate * 100)
        out_sample_rate = kwargs.get('out_sample_rate')
        kwargs.setdefault('in_sample_rate', int(out_sample_rate / self.frame_rate))
        super(FrameResampler, self).__init__(**kwargs)
        self.data_block_sampler = LTCDataBlockSampler(
            out_sample_rate=self.in_sample_rate,
            bit_depth=self.bit_depth,
        )
    def generate_samples(self, data):
        return self.data_block_sampler.generate_samples(data)

class LTCDataBlockSampler(Resampler):
    def __init__(self, **kwargs):
        kwargs.setdefault('in_sample_rate', 160 * 10)
        super(LTCDataBlockSampler, self).__init__(**kwargs)
    def generate_samples(self, data):
        def iter_yvals():
            while True:
                yield -1
                yield 1
        t = self.in_periods
        a = np.zeros(160, dtype=self.dtype)
        y_iter = iter_yvals()
        y = next(y_iter)
        i = 0
        for v in data:
            a[i] = y
            if v:
                y = next(y_iter)
            a[i+1] = y
            y = next(y_iter)
            i += 2
        a = np.repeat(a, self.in_periods.size / 160)
        y_max = int(self.y_max / 2)
        a *= y_max
        return self.resample(a)
