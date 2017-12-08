import time
import threading
import datetime
from fractions import Fraction

import numpy as np

from pyltc import fields
from pyltc.frames import Frame, FrameFormat
from pyltc.audioutils import FrameResampler


class Generator(object):
    def __init__(self, **kwargs):
        frame_format = kwargs.get('frame_format')
        if not isinstance(frame_format, FrameFormat):
            frame_format = FrameFormat(**frame_format)
        self.frame_format = frame_format
        fkwargs = kwargs.get('frame', {})
        fkwargs['frame_format'] = frame_format
        self.frame = Frame(**fkwargs)
        self.data_block = fields.LTCDataBlock(generator=self)
    def set_hmsf(self, **kwargs):
        self.frame.set(**kwargs)
    def incr_frame(self, value=1):
        self.frame += value
    def set_frame_from_dt(self, dt=None, ts=None):
        if dt is None:
            if ts is None:
                ts = time.time()
            if self.use_utc:
                dt = datetime.datetime.utcfromtimestamp(ts)
            else:
                dt = datetime.datetime.fromtimestamp(ts)
        self.frame.from_dt(dt)
    def get_data_block_value(self):
        return self.data_block.get_value()
    def get_data_block_string(self):
        return self.data_block.get_string()
    def get_data_block_array(self):
        return self.data_block.get_array()

class FreeRunGenerator(Generator):
    def __init__(self, **kwargs):
        super(FreeRunGenerator, self).__init__(**kwargs)
        self.use_current_time = kwargs.get('use_current_time', True)
        self.use_utc = kwargs.get('use_utc', False)
        self.frame_callback = kwargs.get('frame_callback')
        self.running = threading.Event()
        self.stopped = threading.Event()
        self.frame_event = threading.Event()
        self.run_thread = None
    def start(self, loop=True):
        if self.running.is_set():
            return
        self.run_thread = TimerThread(self)
        self.run_thread.start()
        self.running.wait()
        if loop:
            try:
                while self.running.is_set():
                    s = self.wait_for_frame()
                    if s is False:
                        break
                    self._frame_callback(s)
            except KeyboardInterrupt:
                self.stop()
    def stop(self):
        if not self.running.is_set():
            return
        self.run_thread.stop()
        self.stopped.wait()
        self.run_thread = None
    def wait_for_frame(self, timeout=None):
        self.frame_event.wait(timeout)
        if not self.running.is_set:
            return False
        return self.get_data_block_string()

    def _frame_callback(self, s):
        pass

class AudioGenerator(Generator):
    def __init__(self, **kwargs):
        super(AudioGenerator, self).__init__(**kwargs)
        self.use_current_time = kwargs.get('use_current_time', True)
        self.use_utc = kwargs.get('use_utc', False)
        if self.use_current_time:
            self.set_frame_from_dt()
        rs = self.sample_rate = kwargs.get('sample_rate', 48000)
        fr = self.frame_format.rate
        self.samples_per_frame = rs / fr
        if int(self.samples_per_frame) == float(self.samples_per_frame):
            self.even_samples = True
        else:
            self.even_samples = False
            self.num_samples = 0
            self.frame_count = 0
        self.use_float_samples = kwargs.get('use_float_samples', False)
        self.bit_depth = kwargs.get('bit_depth', 8)
        self.dtype = kwargs.get('dtype')
        self.sampler = FrameResampler(
            out_sample_rate=self.sample_rate,
            use_float_samples=self.use_float_samples,
            bit_depth=self.bit_depth,
            dtype=self.dtype,
            frame_rate=self.frame_format.rate,
        )
    def calc_offset(self, samples):
        self.num_samples += samples.size
        self.frame_count += 1
        num_samples = self.samples_per_frame * self.frame_count
        if float(num_samples) == int(num_samples):
            offset = int(num_samples - self.num_samples)
            self.num_samples += offset
        else:
            offset = 0
        return offset
    def generate_frame(self, only_zero=False):
        if only_zero:
            a = np.zeros(80, dtype=bool)
        else:
            a = self.get_data_block_array()
        samples = self.sampler.generate_samples(a)
        if not self.even_samples:
            offset = self.calc_offset(samples)
            if offset > 0:
                offset_samples = np.array([samples[-1]] * offset)
                samples = np.concatenate((samples, offset_samples))
            elif offset < 0:
                i = int(self.current_offset)
                samples = samples[:-offset]
        return samples
    def generate_frames(self, num_frames, only_zero=False):
        spf = int(self.samples_per_frame)
        a = np.full((num_frames, spf+2), np.inf, dtype=self.dtype)
        for i in range(num_frames):
            _a = self.generate_frame(only_zero)
            if _a.size > a.shape[1]:
                infarr = np.full((num_frames, _a.size-a.shape[1]), np.inf, dtype=self.dtype)
                a = np.append(a, infarr, axis=1)
            a[i][:_a.size] = _a
            if only_zero is False:
                self.incr_frame()
        a = a.flatten()
        not_nan_ix = np.nonzero(np.logical_not(np.isinf(a)))
        return a[not_nan_ix]


class TimerThread(threading.Thread):
    def __init__(self, generator):
        super(TimerThread, self).__init__()
        self.generator = generator
    def run(self):
        g = self.generator
        fr = g.frame_format.rate.float_value
        interval = 1 / fr
        start_ts = self.start_time = time.time()
        last_ts = start_ts
        if g.use_current_time:
            g.set_frame_from_dt(ts=start_ts)
        g.running.set()
        while g.running.is_set():
            time.sleep(interval)
            if g.use_current_time:
                g.set_frame_from_dt()
            else:
                g.incr_frame()
            g.frame_event.set()
        g.stopped.set()
    def stop(self):
        g = self.generator
        g.running.clear()
        g.frame_event.set()
        g.stopped.set()


def build_gen(**kwargs):
    kwargs.setdefault('frame_format', {'rate':29.97, 'drop_enabled':True})
    return AudioGenerator(**kwargs)

def time_test(num_frames=30, **kwargs):
    times = []
    g = build_gen(**kwargs)
    for i in range(num_frames):
        start_ts = time.time()
        a = g.generate_frame()
        g.incr_frame()
        end_ts = time.time()
        times.append(end_ts - start_ts)
    frame_time = 1 / g.frame_format.rate.float_value
    slowtimes = [t for t in times if t >= frame_time]
    print('min={}, max={}'.format(min(times), max(times)))
    if len(slowtimes):
        print('was slow {} times: {}'.format(len(slowtimes), slowtimes))
    return times

def plot_wave(**kwargs):
    import matplotlib
    matplotlib.use('Qt4Agg')
    import matplotlib.pyplot as plt
    g = build_gen(**kwargs)
    a = g.generate_frames(2, only_zero=True)
    g.current_offset = 0.
    b = g.generate_frames(2)
    g.current_offset = 0.
    g.incr_frame()
    c = g.generate_frames(2)
    rs = float(g.sample_rate)
    t = np.arange(0, a.size / rs, 1 / rs)
    t2 = np.arange(0, b.size / rs, 1/ rs)
    t3 = np.arange(0, c.size / rs, 1/ rs)
    print(a.size, b.size, c.size)
    ax1 = plt.subplot(3, 1, 1)
    plt.plot(t, a)
    plt.grid()
    ax2 = plt.subplot(3, 1, 2, sharex=ax1, sharey=ax1)
    plt.grid()
    plt.plot(t2, b)
    ax3 = plt.subplot(3, 1, 3, sharex=ax1, sharey=ax1)
    plt.grid()
    plt.plot(t3, c)
    plt.show()
    return t, a

if __name__ == '__main__':
    t, a = plot_wave()
