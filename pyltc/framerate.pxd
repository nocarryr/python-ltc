
cdef class FrameRate:
    cdef int __numerator, __denom, __rounded
    cdef object __value
    cdef float __float_value
    cdef inline list _build_frame_times(self)

cdef class FrameFormat:
    cdef public FrameRate rate
    cdef public bint drop_frame
    cdef public char *tc_fmt_str
    cpdef format_tc_string(self, hmsf)
