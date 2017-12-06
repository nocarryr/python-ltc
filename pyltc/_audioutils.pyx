import numpy as np
cimport numpy as np

cdef class _Resampler:
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
    def __init__(self, **kwargs):
        kwargs.setdefault('in_sample_rate', 160 * 10)
        super().__init__(**kwargs)
    cpdef generate_samples(self, data):
        cdef np.ndarray a, yvals
        cdef int y, v, i, y_max, yval_index

        a = np.zeros(160, dtype=self.dtype)

        if self.use_float_samples:
            yvals = np.array([-1., 1.], dtype=self.dtype)
        else:
            yvals = np.array([-1, 1], dtype=self.dtype)
        yval_index = 0
        y = yvals[yval_index]

        i = 0
        for v in data:
            a[i] = y
            if v:
                # Flip-flop for "True"
                if yval_index == 1:
                    yval_index = 0
                else:
                    yval_index = 1
                y = yvals[yval_index]
            a[i+1] = y

            # Flip-flop at end of bit
            if yval_index == 1:
                yval_index = 0
            else:
                yval_index = 1
            y = yvals[yval_index]
            i += 2
        a = np.repeat(a, int(self.in_periods.size / 160))
        if not self.use_float_samples:
            y_max = int(self.y_max / 2)
            a *= y_max
        return self.resample(a)
