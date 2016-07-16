import threading
import time

import numpy as np
import jack

from pyltc.audio.base import AudioBackend
from pyltc.tcgen import AudioGenerator

class SampleBuffer(object):
    def __init__(self, **kwargs):
        b = self.backend = kwargs.get('backend')
        self.sampwidth = 4
        self.block_size_bytes = b.block_size * b.queue_length * self.sampwidth
        self.buffer = jack.RingBuffer(self.block_size_bytes)
        self.total_size = self.buffer.write_space
    @property
    def ready(self):
        return self.buffer.write_space >= self.block_size_bytes
    def fill_zeros(self):
        sp = self.buffer.write_space
        if not sp:
            return
        size = int(sp / self.sampwidth)
        a = np.zeros(size, dtype=np.float32)
        return self.write(a)
    def can_write(self, data):
        return self.buffer.write_space >= data.size * self.sampwidth
    def write(self, data):
        #data = np.asarray(data, dtype=np.float32)
        bytes_written = self.buffer.write(data)
        return bytes_written
    def write_blocking(self, data):
        # = np.asarray(data, dtype=np.float32)
        size = data.nbytes
        while self.buffer.write_space < size:
            time.sleep(.01)
        self.buffer.write(data)
    def read(self, size):
        size = size * self.sampwidth
        return self.buffer.read(size)
    def clear(self):
        self.buffer.reset()
    def __len__(self):
        return self.buffer.write_space

class JackAudio(AudioBackend):
    block_size = 1024
    queue_length = 32
    def __init__(self, **kwargs):
        super(JackAudio, self).__init__(**kwargs)
        self.buffer = self.build_buffer()
        self.data_waiting = None
        self.process_timestamp = None
        self.buffer_lock = threading.Lock()
    def calc_time_offset(self):
        p_t = self.process_timestamp
        if p_t is None:
            return None
        t = self.client.frame_time
        return t - p_t
    def build_buffer(self):
        return SampleBuffer(backend=self)
    def fill_buffer(self):
        if self.process_timestamp is None:
            self.buffer.fill_zeros()
            return
        if self.data_waiting is not None:
            a = self.data_waiting
            self.data_waiting = None
        else:
            a = self.get_frames()
        if not self.buffer.can_write(a):
            self.data_waiting = a
            return
        while True:
            i = self.buffer.write(a)
            a = self.get_frames()
            if not self.buffer.can_write(a):
                self.data_waiting = a
                break
    def init_backend(self):
        self.buffer_thread = BufferThread(backend=self)
        c = self.client = jack.Client('LTCGenerator')
        c.set_blocksize_callback(self.on_jack_blocksize)
        c.blocksize = self.block_size
        o = self.outport = c.outports.register('output_1')
        c.set_process_callback(self.jack_process_callback)
    def _start(self):
        self.buffer_thread.start()
        self.buffer_thread.running.wait()
        self.client.activate()
        self.client.connect(self.outport, 'system:playback_1')
        self.client.connect(self.outport, 'system:playback_2')
    def _stop(self):
        self.buffer_thread.stop()
        self.buffer_thread = None
        self.outport.disconnect()
        self.outport.unregister()
        self.client.deactivate()
        self.client.close()
    def run_loop(self):
        gen_ready = False
        try:
            while True:
                if not gen_ready:
                    time.sleep(.1)
                    if self.process_timestamp is not None:
                        gen_ready = True
                        self.buffer_thread.ready.set()
                else:
                    time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
        self.stop()
    def on_jack_blocksize(self, size):
        if size == self.block_size:
            return
        print('blocksize change: {}'.format(size))
        with self.buffer_lock:
            self.buffer.clear()
            self.block_size = size
            self.buffer = self.build_buffer()
            self.data_waiting = None
        self.buffer_thread.idle.wait()
    def jack_process_callback(self, size):
        a = self.buffer.read(size)
        self.process_timestamp = self.client.last_frame_time
        for o in self.client.outports:
            o.get_buffer()[:] = a

class BufferThread(threading.Thread):
    def __init__(self, **kwargs):
        super(BufferThread, self).__init__()
        self.backend = kwargs.get('backend')
        self.running = threading.Event()
        self.stopped = threading.Event()
        self.ready = threading.Event()
        self.need_data = threading.Event()
        self.idle = threading.Event()
        self.wait_timeout = .01
    def run(self):
        self.running.set()
        self.ready.wait()
        print('buffer_thread ready')
        self.backend.generator.set_frame_from_dt()
        with self.backend.buffer_lock:
            self.backend.fill_buffer()
        print('buffer filled')
        while self.running.is_set():
            self.need_data.wait(self.wait_timeout)
            self.idle.clear()
            if not self.running.is_set():
                break
            with self.backend.buffer_lock:
                self.backend.fill_buffer()
            self.idle.set()
        self.stopped.set()
    def stop(self):
        self.running.clear()
        self.need_data.set()
        self.stopped.wait()

def main(**kwargs):
    generator = AudioGenerator(
        frame_format={'rate':29.97, 'drop_frame':True},
        bit_depth=32,
        use_float_samples=True,
        dtype=np.dtype(np.float32),
        sample_rate=48000,
    )
    aud = JackAudio(generator=generator)
    aud.start()
    aud.run_loop()

if __name__ == '__main__':
    main()
