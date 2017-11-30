import os

import numpy as np
import scipy.io.wavfile as wavfile

def bools_to_int(b):
    n = 0
    for i, v in enumerate(b):
        if v:
            n += 1 << i
    return n

def test_datablock(ltc_frame_format):
    from pyltc.tcgen import Generator
    from pyltc.frames import FrameFormat

    fmt = FrameFormat(**ltc_frame_format)

    g = Generator(
        use_current_time=False,
        frame_format=fmt,
    )
    sync_word = [False, False]
    sync_word.extend([True] * 12)
    sync_word.extend([False, True])
    sync_word = np.array(sync_word)
    while g.frame.hour.value < 1:
        data = g.get_data_block_array()
        assert data.size == 80
        assert np.count_nonzero(data) % 2 == 0

        # drop_frame flag
        assert data[10] == ltc_frame_format.get('drop_frame', False)

        # reserved zero
        assert data[58] == False

        v = bools_to_int(data[:4])
        assert v == g.frame._value % 10

        v = bools_to_int(data[8:10])
        assert v == g.frame._value // 10

        v = bools_to_int(data[16:20])
        assert v == g.frame.second.value % 10

        v = bools_to_int(data[24:27])
        assert v == g.frame.second.value // 10

        v = bools_to_int(data[32:36])
        assert v == g.frame.minute.value % 10

        v = bools_to_int(data[40:43])
        assert v == g.frame.minute.value // 10

        v = bools_to_int(data[48:52])
        assert v == g.frame.hour.value % 10

        v = bools_to_int(data[56:58])
        assert v == g.frame.hour.value // 10

        assert len(data[64:]) == len(sync_word)
        assert np.array_equal(data[64:], sync_word)

        g.incr_frame()

def test_wave_write(ltc_frame_format, tmpdir):
    from pyltc.tcgen import AudioGenerator
    from pyltc.frames import FrameFormat

    fmt = FrameFormat(**ltc_frame_format)

    g = AudioGenerator(
        use_current_time=True,
        bit_depth=16,
        frame_format=fmt,
    )
    num_frames = int(g.frame_format.rate * 60)
    num_samples = num_frames / g.frame_format.rate * g.sample_rate
    while num_samples.denominator != 1:
        num_frames += 1
        num_samples = num_frames / g.frame_format.rate * g.sample_rate
    print('num_frames={}, num_samples={}'.format(num_frames, num_samples))

    if g.frame_format.drop_frame:
        df = 'DF'
    else:
        df = 'ND'
    filename = os.path.join(str(tmpdir), '{}frames-{}{}.wav'.format(num_frames, g.frame_format.rate, df))
    a = g.generate_frames(num_frames)
    print('min={}, max={}'.format(a.min(), a.max()))
    g.sampler.write_wavefile(a, filename)
    rs, b = wavfile.read(filename)
    assert rs == g.sample_rate
    assert np.array_equal(a, b)


    sample_diff = num_samples - b.size

    assert -1 <= sample_diff <= 1
