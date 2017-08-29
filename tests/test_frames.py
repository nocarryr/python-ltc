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

def test_2997_df():
    from pyltc.frames import FrameFormat, Frame
    fmt = FrameFormat(rate=29.97, drop_frame=True)
    frame = Frame(frame_format=fmt, minutes=10)

    assert str(frame) == '00:10:00;00'

    # 29.97 drops 18 frames every 10 minutes (30fps * 10m * 60s == 18000)
    assert frame.total_frames == 17982



    frame = Frame(frame_format=fmt, minutes=9, seconds=59, frames=29)

    assert str(frame) == '00:09:59;29'
    assert frame.total_frames == 17981

    frame += 1
    assert str(frame) == '00:10:00;00'
    assert frame.total_frames == 17982


    frame = Frame(frame_format=fmt, total_frames=17982)
    assert str(frame) == '00:10:00;00'
    assert frame.total_frames == 17982


    frame = Frame(frame_format=fmt, minutes=10, frames=1)

    assert str(frame) == '00:10:00;01'
    assert frame.total_frames == 17983

    frame -= 1
    assert str(frame) == '00:10:00;00'
    assert frame.total_frames == 17982

    frame -= 1

    assert str(frame) == '00:09:59;29'
    assert frame.total_frames == 17981



def test_5994_df():
    from pyltc.frames import FrameFormat, Frame
    fmt = FrameFormat(rate=59.94, drop_frame=True)
    frame = Frame(frame_format=fmt, minutes=10)

    assert str(frame) == '00:10:00;00'

    # 59.94 drops 36 frames every 10 minutes (60fps * 10m * 60s == 36000)
    assert frame.total_frames == 35964

    frame = Frame(frame_format=fmt, minutes=9, seconds=59, frames=59)

    assert str(frame) == '00:09:59;59'
    assert frame.total_frames == 35963

    frame += 1
    assert str(frame) == '00:10:00;00'
    assert frame.total_frames == 35964


    frame = Frame(frame_format=fmt, total_frames=35964)
    assert str(frame) == '00:10:00;00'
    assert frame.total_frames == 35964


    frame = Frame(frame_format=fmt, minutes=10, frames=2)

    assert str(frame) == '00:10:00;02'
    assert frame.total_frames == 35966
    frame2 = Frame(frame_format=fmt, total_frames=frame.total_frames)
    assert frame.total_frames == frame2.total_frames
    assert str(frame) == str(frame2)

    frame -= 1
    assert str(frame) == '00:10:00;01'
    assert frame.total_frames == 35965

    frame -= 1
    assert str(frame) == '00:10:00;00'
    assert frame.total_frames == 35964

    frame -= 1

    assert str(frame) == '00:09:59;59'
    assert frame.total_frames == 35963


def test_timecode(frame_format):
    from pyltc.frames import FrameFormat, Frame

    fmt = FrameFormat(**frame_format)

    fmt_repr = repr(fmt)
    assert fmt_repr.split(': ')[0] == 'FrameFormat'
    assert float(fmt_repr.split(': ')[1].split('fps')[0]) == frame_format['rate']
    if frame_format.get('drop_frame'):
        assert fmt_repr.split('(')[1].split(')')[0] == 'Drop'
    else:
        assert fmt_repr.split('(')[1].split(')')[0] == 'Non-Drop'

    frame = Frame(frame_format=fmt)

    for total_frames in range(int(fmt.rate.rounded * 3600)):
        assert frame.total_frames == total_frames

        frame_string = str(frame)

        frame2 = Frame(frame_format=fmt)
        frame2.set_total_frames(total_frames)

        assert str(frame2) == frame_string

        frame3 = Frame(
            frame_format=fmt,
            hours=frame.hour.value,
            minutes=frame.minute.value,
            seconds=frame.second.value,
            frames=frame.value,
        )
        assert frame3.total_frames == frame.total_frames == total_frames
        assert str(frame3) == frame_string

        assert frame == frame2 == frame3 == total_frames


        frame4 = frame + Frame(frame_format=fmt, hours=2)


        assert frame4 != frame
        assert frame4 != total_frames
        assert frame4 > frame
        assert frame4 >= frame
        assert frame < frame4
        assert frame <= frame4
        assert frame4 > total_frames

        assert frame4.hour.value == frame.hour.value + 2
        assert frame4.minute.value == frame.minute.value
        assert frame4.second.value == frame.second.value
        assert frame4.value == frame.value

        frame4 = frame4 - Frame(frame_format=fmt, hours=2).total_frames
        assert frame4 == frame

        frame4 += 20
        assert frame4.total_frames == total_frames + 20

        if total_frames >= 20:
            frame4 -= 20
            assert frame4.total_frames == total_frames

        if frame_format.get('drop_frame'):
            h, m, s = [int(v) for v in frame_string.split(';')[0].split(':')]
            f = int(frame_string.split(';')[1])
            assert [h, m, s, f] == frame.get_hmsf_values()

            drop_enabled = frame.second.value == 0 and frame.minute.value % 10 != 0

            assert frame.drop_enabled is frame2.drop_enabled is frame3.drop_enabled

            if drop_enabled:
                assert frame.value >= 2
        else:
            hmsf = [int(v) for v in frame_string.split(':')]
            assert hmsf == frame.get_hmsf_values()

        frame_repr = repr(frame)
        assert frame_repr.split(': ')[0] == 'Frame'
        assert frame_repr.split(': ')[1].split(' - ')[0] == frame_string
        assert frame_repr.split(' - ')[1] == str(fmt)

        frame += 1


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

def test_copy(frame_format):
    import datetime
    from pyltc.frames import FrameFormat, Frame
    fmt = FrameFormat(**frame_format)
    frame = Frame(frame_format=fmt)
    dt = datetime.datetime.now()
    frame.from_dt(dt)
    frame2 = frame.copy()
    assert frame.total_frames == frame2.total_frames
    assert str(frame) == str(frame2)

def test_decr(frame_format):
    from pyltc.frames import FrameFormat, Frame

    fmt = FrameFormat(**frame_format)
    frame = Frame(frame_format=fmt)

    for total_frames in reversed(range(int(fmt.rate.rounded * 3600))):
        frame.set_total_frames(total_frames)
        assert frame.total_frames == total_frames

        frame_string = str(frame)

        frame2 = Frame(frame_format=fmt)
        frame2.set_total_frames(total_frames)

        assert str(frame2) == frame_string

        frame3 = Frame(
            frame_format=fmt,
            hours=frame.hour.value,
            minutes=frame.minute.value,
            seconds=frame.second.value,
            frames=frame.value,
        )
        assert frame3.total_frames == frame.total_frames == total_frames
        assert str(frame3) == frame_string

        if frame_format.get('drop_frame'):
            drop_enabled = frame.second.value == 0 and frame.minute.value % 10 != 0

            assert frame.drop_enabled is frame2.drop_enabled is frame3.drop_enabled

            if drop_enabled:
                assert frame.value >= 2

        frame -= 1
