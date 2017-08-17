from fractions import Fraction

import pytest

def test_frame_rate():
    from pyltc.frames import FrameRate

    with pytest.raises(Exception, message='FrameRate definition not found for 42'):
        frame_rate = FrameRate.from_float(42)

    frame_rate_objs = []

    for flt_val in sorted(FrameRate.defaults.keys()):
        numerator, denom = FrameRate.defaults[flt_val]

        frac_val = Fraction(numerator, denom)

        frame_rate = FrameRate(numerator, denom)
        assert frame_rate.value == frac_val

        assert FrameRate.from_float(flt_val) == frame_rate

        if flt_val == int(flt_val):
            assert frame_rate.float_value == flt_val
        else:
            assert round(frame_rate.float_value, 2) == round(flt_val, 2)

        assert float(str(frame_rate)) == round(flt_val, 2)

        num_denom_str = repr(frame_rate).split('(')[1].split(')')[0]
        assert int(num_denom_str.split('/')[0]) == frame_rate.numerator
        assert int(num_denom_str.split('/')[1]) == frame_rate.denom

        assert frame_rate.value in FrameRate._registry
        frame_rate_objs.append(frame_rate)

    for i, frame_rate in enumerate(frame_rate_objs):

        ## FrameRate._registry check
        frame_rate2 = FrameRate(frame_rate.numerator, frame_rate.denom)
        assert frame_rate is frame_rate2
        assert id(frame_rate) == id(frame_rate2)

        ## Equality checking (same values)
        assert frame_rate2 >= frame_rate
        assert frame_rate2 <= frame_rate
        assert frame_rate2 == frame_rate

        assert frame_rate >= frame_rate2
        assert frame_rate <= frame_rate2
        assert frame_rate == frame_rate2

        if i > 0:
            prev_frame_rate = frame_rate_objs[i-1]
        else:
            prev_frame_rate = None

        try:
            next_frame_rate = frame_rate_objs[i+1]
        except IndexError:
            next_frame_rate = None

        ## gt, ge, lt, le, eq, ne checks
        if prev_frame_rate is not None:
            assert prev_frame_rate != frame_rate
            assert prev_frame_rate < frame_rate
            assert frame_rate > prev_frame_rate
            assert prev_frame_rate <= frame_rate
            assert not prev_frame_rate >= frame_rate
            assert frame_rate >= prev_frame_rate
            assert not frame_rate <= prev_frame_rate
            assert not frame_rate == prev_frame_rate
            assert not prev_frame_rate == frame_rate

        if next_frame_rate is not None:
            assert next_frame_rate != frame_rate
            assert next_frame_rate > frame_rate
            assert frame_rate < next_frame_rate
            assert next_frame_rate >= frame_rate
            assert frame_rate <= next_frame_rate
            assert not next_frame_rate <= frame_rate
            assert not frame_rate >= next_frame_rate
            assert not frame_rate == next_frame_rate
            assert not next_frame_rate == frame_rate


def test_frame_rate_ops():
    from pyltc.frames import FrameRate

    for flt_val, args in FrameRate.defaults.items():
        frame_rate = FrameRate(*args)

        for frame_count in range(1, 43202):
            fr_secs = float(frame_rate * frame_count)
            flt_secs = frame_rate.float_value * frame_count
            if frame_rate.denom != 1:
                if frame_count % frame_rate.denom == 0:
                    assert flt_secs == fr_secs
                elif fr_secs < 1:
                    assert round(flt_secs, 2) == round(fr_secs, 2)
                else:
                    assert round(flt_secs, 0) == round(fr_secs, 0)
            else:
                assert flt_secs == fr_secs

def test_basic():
    from pyltc.frames import FrameFormat, Frame
    fmt = FrameFormat(rate=29.97, drop_frame=True)
    frame = Frame(frame_format=fmt)
    assert frame.total_frames == 0
    assert frame.get_tc_string() == '00:00:00:00'
    frame += 30
    assert frame.total_frames == 30
    assert frame.value == 0
    assert frame.get_tc_string() == '00:00:01:00'
    frame.set(hours=1, minutes=8, seconds=59, frames=29)
    assert frame.get_tc_string() == '01:08:59:29'
    assert frame.total_frames == 110039
    frame += 1
    assert frame.value == 2
    assert frame.get_tc_string() == '01:09:00:02'
    assert frame.total_frames == 110040
    frame += 28
    assert frame.value == 2
    assert frame.get_tc_string() == '01:09:01:02'
    assert frame.total_frames == 110068
    frame.set(seconds=59, frames=29)
    assert frame.get_tc_string() == '01:09:59:29'
    frame += 1
    assert frame.value == 0
    assert frame.get_tc_string() == '01:10:00:00'

def test_5994_df():
    from pyltc.frames import FrameFormat, Frame
    fmt = FrameFormat(rate=59.94, drop_frame=True)
    frame = Frame(frame_format=fmt)
    assert frame.total_frames == 0
    assert frame.get_tc_string() == '00:00:00:00'
    frame += 60
    assert frame.total_frames == 60
    assert frame.value == 0
    assert frame.get_tc_string() == '00:00:01:00'
    frame.set(hours=1, minutes=8, seconds=59, frames=59)
    assert frame.get_tc_string() == '01:08:59:59'
    assert frame.total_frames == 220079
    frame += 1
    assert frame.value == 4
    assert frame.get_tc_string() == '01:09:00:04'
    assert frame.total_frames == 220080
    frame += 56
    assert frame.value == 4
    assert frame.get_tc_string() == '01:09:01:04'
    assert frame.total_frames == 220136
    frame.set(seconds=59, frames=59)
    assert frame.get_tc_string() == '01:09:59:59'
    frame += 1
    assert frame.value == 0
    assert frame.get_tc_string() == '01:10:00:00'

def test_dt():
    import datetime
    from pyltc.frames import FrameFormat, Frame
    fmt = FrameFormat(rate=29.97, drop_frame=True)
    frame = Frame(frame_format=fmt)
    print(frame.frame_times)
    dt = datetime.datetime.now()
    for m in [9, 10]:
        dt = dt.replace(minute=m)
        print('minute={}'.format(m))
        for f in range(29):
            ms = f / 29.97 * 1e6
            ms = int(round(ms))
            ms += 1
            dt = dt.replace(microsecond=ms)
            frame.from_dt(dt)
            assert frame.hour.value == dt.hour
            assert frame.minute.value == dt.minute
            assert frame.second.value == dt.second
            if f in [0, 1] and frame.drop_enabled:
                assert frame.value == 2
            else:
                assert frame.value == f

def test_copy():
    import datetime
    from pyltc.frames import FrameFormat, Frame
    fmt = FrameFormat(rate=29.97, drop_frame=True)
    frame = Frame(frame_format=fmt)
    dt = datetime.datetime.now()
    frame.from_dt(dt)
    frame2 = frame.copy()
    assert frame.total_frames == frame2.total_frames
    assert frame.get_tc_string() == frame2.get_tc_string()
