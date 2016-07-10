import collections

class AudioBackend(object):
    frames_per_queue = 2
    queue_length = 2
    def __init__(self, **kwargs):
        self.generator = kwargs.get('generator')
        self.sample_rate = self.generator.sample_rate
        self.bit_depth = self.generator.bit_depth
        self.queue = collections.deque()
        self.running = False
        self.initialized = False
    def init_backend(self):
        pass
    def get_frames(self, num_frames=None):
        if num_frames is None:
            num_frames = self.frames_per_queue
        return self.generator.generate_frames(num_frames)
    def fill_buffer(self):
        while len(self.queue) < self.queue_length:
            self.queue.append(self.get_frames())
    def next_buffer(self):
        if not len(self.queue):
            self.fill_buffer()
        return self.queue.popleft()
    def start(self):
        if self.running:
            return
        if not self.initialized:
            self.init_backend()
        self.running = True
        self.fill_buffer()
        self._start()
    def _start(self):
        raise NotImplementedError('must be defined by subclass')
    def stop(self):
        if not self.running:
            return
        self._stop()
        self.running = False
    def _stop(self):
        raise NotImplementedError('must be defined by subclass')
