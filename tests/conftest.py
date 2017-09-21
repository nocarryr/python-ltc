import shlex
import subprocess
import time
import threading
try:
    import queue
except ImportError:
    import Queue as queue

import numpy as np
import jack

import pytest

FRAME_FORMATS = [
    {'rate':29.97},
    {'rate':29.97, 'drop_frame':True},
    {'rate':59.94},
    {'rate':59.94, 'drop_frame':True},
    {'rate':30},
    {'rate':25},
    {'rate':24},
]

@pytest.fixture(params=FRAME_FORMATS)
def frame_format(request):
    return request.param

@pytest.fixture(params=[fmt for fmt in FRAME_FORMATS if fmt['rate']<=30])
def ltc_frame_format(request):
    return request.param

@pytest.fixture
def jackd_server(request, monkeypatch, worker_id):
    servername = 'pytest_server_{}'.format(worker_id)
    cmdstr = 'jackd -n{} -ddummy -r48000 -p1024'.format(servername)
    monkeypatch.setenv('JACK_DEFAULT_SERVER', servername)
    p = subprocess.Popen(shlex.split(cmdstr))
    def close_jackd():
        p.terminate()
    request.addfinalizer(close_jackd)
    return servername

@pytest.fixture
def jack_listen_client(request, jackd_server, worker_id):

    class ListenClient(object):
        def __init__(self):
            self.first_timestamp = None
            self.jack_ready = False
            self._queue = queue.Queue()
            self.data = None
            self.client = None
            self.inport = None
            self.queue_thread = None
            self.worker_id = worker_id
            self.servername = jackd_server
            self.client_name = 'PyTest_Listener_{}'.format(worker_id)
            self.generator_name = 'LTCGenerator_{}'.format(worker_id)
        def start(self):
            self.queue_thread = QueueThread(self)
            self.queue_thread.start()
            c = self.client = jack.Client(self.client_name)
            p = self.inport = c.inports.register('input_1')
            c.set_process_callback(self.jack_process_callback)

            c.activate()
            c.connect(
                '{}:output_1'.format(self.generator_name),
                '{}:input_1'.format(self.client_name),
            )
            while not self.jack_ready:
                time.sleep(.1)
                self.check_jack_ready()
        def stop(self):
            if self.queue_thread is not None:
                self.queue_thread.stop()
                self.queue_thread = None
            if self.inport is not None:
                self.inport.disconnect()
                self.inport.unregister()
                self.inport = None
            if self.client is not None:
                self.client.deactivate()
                self.client.close()
                self.client = None
            self.jack_ready = False
        def check_jack_ready(self):
            if self.first_timestamp is not None:
                self.jack_ready = True
                return True
            return False
        def jack_process_callback(self, size):
            if self.first_timestamp is None:
                self.first_timestamp = self.client.last_frame_time
            for inport in self.client.inports:
                data = inport.get_array()
                self._queue.put_nowait(data)

    class QueueThread(threading.Thread):
        def __init__(self, listen_client):
            super(QueueThread, self).__init__()
            self.listen_client = listen_client
            self.running = threading.Event()
            self.stopped = threading.Event()
        def run(self):
            self.running.set()
            while self.running.is_set():
                data = self.listen_client._queue.get()
                self.listen_client._queue.task_done()
                if data is None:
                    break
                if self.listen_client.data is None:
                    data = data[np.nonzero(data)]
                    if not data.size:
                        continue
                    self.listen_client.data = data
                else:
                    self.listen_client.data = np.concatenate((self.listen_client.data, data))
            self.stopped.set()
        def stop(self):
            self.running.clear()
            self.listen_client._queue.put(None)
            self.stopped.wait()

    listen_client = ListenClient()
    request.addfinalizer(listen_client.stop)

    return listen_client
