import time

import pygame
from pygame import mixer

from pyltc.audio.base import AudioBackend
from pyltc.tcgen import AudioGenerator

class PygameAudio(AudioBackend):
    frames_per_queue = 10
    def __init__(self, **kwargs):
        super(PygameAudio, self).__init__(**kwargs)
        self.use_loop = kwargs.get('use_loop', True)
    def init_backend(self):
        pygame.init()
        mixer.init(
            frequency=self.sample_rate,
            size=self.bit_depth * -1,
            channels=1,
            buffer=1024,
        )
        self.sounds_in_queue = 0
        self.channel = mixer.find_channel()
        self.end_event_type = pygame.USEREVENT
        self.channel.set_endevent(self.end_event_type)
    def get_frames(self, num_frames=None):
        a = super(PygameAudio, self).get_frames(num_frames)
        return mixer.Sound(a)
    def queue_next_sound(self):
        s = self.next_buffer()
        if self.channel.get_busy():
            self.channel.queue(s)
            self.sounds_in_queue += 1
        else:
            self.sounds_in_queue = 0
            self.channel.play(s)
            self.queue_next_sound()
        self.fill_buffer()
    def _start(self):
        self.queue_next_sound()
        if self.use_loop:
            self.run_loop()
    def _stop(self):
        mixer.stop()
    def on_sound_end(self, *args):
        self.sounds_in_queue -= 1
        if self.sounds_in_queue < 2:
            self.queue_next_sound()
    def check_events(self, *args):
        end_event = False
        for e in pygame.event.get():
            if e.type == self.end_event_type:
                end_event = True
                break
        if end_event:
            self.on_sound_end()
    def run_loop(self):
        fr = self.generator.frame_format.rate
        interval = 1 / float(fr)
        interval *= self.frames_per_queue
        while True:
            self.check_events()
            time.sleep(interval)
            if not self.running:
                break


def main(**kwargs):
    generator = AudioGenerator(
        frame_format={'rate':29.97, 'drop_frame':True},
        bit_depth=16,
    )
    aud = PygameAudio(generator=generator, use_loop=False)
    aud.start()
    try:
        aud.run_loop()
    except KeyboardInterrupt:
        aud.stop()

if __name__ == '__main__':
    main()
