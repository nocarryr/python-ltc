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
        self.use_float_samples = kwargs.get('use_float_samples', False)
        self.dtype = kwargs.get('dtype')
        if self.dtype is None:
            self.dtype = np.dtype('>i{}'.format(int(self.bit_depth / 8)))
        if self.use_float_samples:
            self.y_max = 1.
            self.y_min = -1.
        else:
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
        if r[-1] == 0:
            r[-1] = r[-2]
        return r
    def write_wavefile(self, a, filename):
        wavfile.write(filename, self.out_sample_rate, a)

class FrameResampler(Resampler):
    def __init__(self, **kwargs):
        self.frame_rate = kwargs.get('frame_rate')
        self.frame_samples = int(self.frame_rate * 100)
        out_sample_rate = kwargs.get('out_sample_rate')
        kwargs.setdefault('in_sample_rate', int(out_sample_rate / self.frame_rate.float_value))
        super(FrameResampler, self).__init__(**kwargs)
        self.data_block_sampler = LTCDataBlockSampler(
            out_sample_rate=self.in_sample_rate,
            bit_depth=self.bit_depth,
            use_float_samples=self.use_float_samples,
            dtype=self.dtype,
        )
    def generate_samples(self, data):
        return self.data_block_sampler.generate_samples(data)

class LTCDataBlockSampler(Resampler):
    def __init__(self, **kwargs):
        kwargs.setdefault('in_sample_rate', 160 * 10)
        super(LTCDataBlockSampler, self).__init__(**kwargs)
    def generate_samples(self, data):
        def iter_yvals():
            if self.use_float_samples:
                yvals = [-1., 1.]
            else:
                yvals = [-1, 1]
            while True:
                yield yvals[0]
                yield yvals[1]
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
        if not self.use_float_samples:
            y_max = int(self.y_max / 2)
            a *= y_max
        return self.resample(a)

class ZeroCrossLocator(object):
    def __init__(self, **kwargs):
        self.last_sample = None
    def detect(self, samples):
        if self.last_sample is not None:
            samples = np.concatenate((self.last_sample, samples))
        self.last_sample = samples[-1:]
        lo = np.sign(samples)
        lo[lo==0] = -1
        return np.where(np.diff(lo))[0]

class LTCDataBlockDecoder(ZeroCrossLocator):
    def __init__(self, **kwargs):
        super(LTCDataBlockDecoder, self).__init__(**kwargs)
        self.datablock_callback = kwargs.get('datablock_callback')
        self.data_buffer = []
        self.consec_ones = 0
        self.current_index = 0
        self.syncword_index = None
    def iter_decode(self, samples):
        transitions = self.detect(samples)
        diff = np.diff(transitions)
        dmin = diff[1:].min()
        minrange = list(range(dmin-2, dmin+3))
        dmax = diff.max()
        maxrange = list(range(dmax-2, dmax+3))
        diff_iter = np.nditer(diff)
        while True:
            if diff_iter.finished:
                break
            v = diff_iter[0]
            if v in minrange:
                diff_iter.iternext()
                yield True
            elif v in maxrange:
                yield False
            diff_iter.iternext()
    def decode(self, samples):
        bfr = self.data_buffer
        i = self.current_index
        consec_ones = self.consec_ones
        syncword_index = self.syncword_index
        for value in self.iter_decode(samples):
            if value:
                consec_ones += 1
            else:
                consec_ones = 0
            bfr.append(value)
            if consec_ones == 12 and syncword_index is None:
                syncword_index = i + 2
            if i == syncword_index:
                if len(bfr) >= 80:
                    datablock = bfr[-80:]
                    self.on_datablock(datablock)
                    syncword_index = None
                    i = 0
                    bfr = []
                else:
                    syncword_index = None
            i += 1
        self.consec_ones = consec_ones
        self.current_index = i
        self.syncword_index = syncword_index
        self.data_buffer = bfr
    def on_datablock(self, datablock):
        if self.datablock_callback is not None:
            self.datablock_callback(datablock)
