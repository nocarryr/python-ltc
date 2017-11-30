import numpy as np

def test_decode():
    from pyltc.tcgen import AudioGenerator
    from pyltc.audioutils import LTCDataBlockDecoder
    from pyltc.frames import FrameFormat
    generated = []
    decoded = []
    def on_datablock(datablock):
        decoded.append(np.array(datablock))
    g = AudioGenerator(
        use_current_time=False,
        bit_depth=16,
        frame_format=FrameFormat(rate=29.97, drop_frame=True),
        use_float_samples=True,
    )
    decoder = LTCDataBlockDecoder(
        datablock_callback=on_datablock,
    )
    for i in range(20):
        samples = g.generate_frame()
        in_data = g.get_data_block_array()
        generated.append(in_data)
        decoder.decode(samples)
        g.incr_frame()
    assert len(decoded) > 0
    print('num_generated={}, num_decoded={}'.format(len(generated), len(decoded)))
    offset = None
    for x, in_data in enumerate(generated):
        for y, out_data in enumerate(decoded):
            if np.array_equal(in_data, out_data):
                offset = (x, y)
                break
        if offset is not None:
            break
    print('offset={}'.format(offset))
    assert offset is not None
    x, y = offset
    while True:
        try:
            in_data = generated[x]
            out_data = decoded[y]
        except IndexError:
            break
        #print(x, y)
        #print(np.nonzero(np.not_equal(in_data, out_data)))
        assert np.array_equal(in_data, out_data)
        x += 1
        y += 1
