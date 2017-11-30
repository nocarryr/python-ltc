import numpy as np
cimport numpy as np

cdef class _Resampler(object):
    cdef public object out_sample_rate, in_sample_rate
    cdef public int bit_depth
    cdef public bint use_float_samples
    cdef public float y_min, y_max
    cdef public np.ndarray in_periods, out_periods, nans
    cdef public np.dtype dtype
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
    cpdef resample(self, np.ndarray a):
        cdef np.ndarray r
        cdef bint strip_nans
        if self.in_sample_rate == self.out_sample_rate:
            return a
        if a.size < self.in_periods.size:
            a = np.concatenate((a, self.nans))[:self.in_periods.size]
            strip_nans = True
        else:
            strip_nans = False
        r = np.interp(self.out_periods, self.in_periods, a, right=np.nan)
        if strip_nans:
            r = r[~np.isnan(r)]
        if r.dtype is not self.dtype:
            r = np.asarray(r, dtype=self.dtype)
        if r[-1] == 0:
            r[-1] = r[-2]
        return r

cdef class _LTCDataBlockSampler(_Resampler):
    def _iter_yvals(self):
        cdef object yvals
        if self.use_float_samples:
            yvals = [-1., 1.]
        else:
            yvals = [-1, 1]
        while True:
            yield yvals[0]
            yield yvals[1]
    cpdef generate_samples(self, data):
        cdef np.ndarray a
        cdef object y_iter, y, v
        cdef int i, y_max

        a = np.zeros(160, dtype=self.dtype)
        y_iter = self._iter_yvals()
        y = next(y_iter)
        i = 0
        for v in data:
            a[i] = y
            if v:
                y = next(y_iter)
            a[i+1] = y
            y = next(y_iter)
            i += 2
        a = np.repeat(a, int(self.in_periods.size / 160))
        if not self.use_float_samples:
            y_max = int(self.y_max / 2)
            a *= y_max
        return self.resample(a)
