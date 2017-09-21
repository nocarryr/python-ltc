import time
import numpy as np

def test_jackaudio(jack_listen_client, ltc_frame_format):
    import datetime
    from pyltc.tcgen import AudioGenerator
    from pyltc.audio import pyjack_audio

    generator = AudioGenerator(
        frame_format=ltc_frame_format,
        bit_depth=32,
        use_float_samples=True,
        dtype=np.dtype(np.float32),
        sample_rate=48000,
        use_current_time=False,
    )

    start_frame = generator.frame.copy()
    start_hmsf = start_frame.get_hmsf_values()

    client_gen = AudioGenerator(
        frame_format=ltc_frame_format,
        bit_depth=32,
        use_float_samples=True,
        dtype=np.dtype(np.float32),
        sample_rate=48000,
        use_current_time=False,
        frame={k:v for k, v in zip(['hours', 'minutes', 'seconds', 'frames'], start_hmsf)},
    )

    start_dt = datetime.datetime.now()

    aud = pyjack_audio.JackAudio(
        generator=generator,
        client_name=jack_listen_client.generator_name,
    )
    aud.start()

    jack_listen_client.start()

    time.sleep(10)

    # Stop the receiver first to avoid empty samples at the end
    jack_listen_client.stop()
    aud.stop()

    received_samples = jack_listen_client.data

    print('jack_listen_client data_size: ', received_samples.size)
    print('generator start: ', str(start_frame))
    print('generator end: ', str(generator.frame))
    print('client_gen tc start: ', str(client_gen.frame))


    # Generate expected_samples from an independant tc gen
    expected_samples = None
    while True:
        _samples = client_gen.generate_frame()
        if expected_samples is None:
            expected_samples = _samples
        else:
            expected_samples = np.concatenate((expected_samples, _samples))
        if client_gen.frame > generator.frame:
            break
        client_gen.incr_frame()
    print('client_gen tc end: ', str(client_gen.frame))

    if expected_samples.size > received_samples.size:
        expected_samples = expected_samples[:received_samples.size]

    # Clean the data, remove nan's and set values to min/max
    nan_ix = np.nonzero(np.isnan(expected_samples))
    expected_samples[nan_ix] = 0.
    received_samples[nan_ix] = 0.

    expected_samples[expected_samples>0.] = 1.
    expected_samples[expected_samples<=0.] = -1.
    received_samples[received_samples>0.] = 1.
    received_samples[received_samples<=0.] = -1.


    assert received_samples.size > 0
    print('final sample size: ', received_samples.size)

    assert np.array_equal(received_samples, expected_samples)
