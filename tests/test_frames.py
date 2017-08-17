
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
