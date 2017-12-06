from pyltc import framerate
from pyltc cimport framerate

cdef class Counter:
    cdef public object frame
    cdef public int _value
    cpdef set_value(self, int value)
    cpdef incr(self)
    cpdef decr(self)

cdef class Frame(Counter):
    cdef public framerate.FrameFormat frame_format
    cdef public Second second
    cdef public Minute minute
    cdef public Hour hour
    cdef public list df_frame_numbers
    cdef public int total_frames
    cdef public bint drop_enabled
    cpdef from_dt(self, dt)
    cpdef microseconds_to_frame(self, microseconds)
    cpdef incr(self)
    cpdef decr(self)
    cdef _set_from_kwargs(self, dict kwargs)
    cpdef _set(self, list hmsf)
    cpdef set_total_frames(self, int total_frames)
    cpdef calc_total_frames(self)
    cpdef check_drop(self)
    cpdef get_hmsf(self)
    cpdef get_hmsf_values(self)
    cpdef get_hmsf_dict(self)
    cpdef get_tc_string(self)

cdef class Second(Counter):
    pass

cdef class Minute(Counter):
    pass

cdef class Hour(Counter):
    pass
