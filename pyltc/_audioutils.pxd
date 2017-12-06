import numpy as np
cimport numpy as np

cdef class _Resampler:
    cdef public object out_sample_rate, in_sample_rate
    cdef public int bit_depth
    cdef public bint use_float_samples
    cdef public float y_min, y_max
    cdef public np.ndarray in_periods, out_periods, nans
    cdef public np.dtype dtype
    cpdef resample(self, np.ndarray a)

cdef class _LTCDataBlockSampler(_Resampler):
    cpdef generate_samples(self, data)
