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
    class JackDServer(object):
        def __init__(self, worker_id):
            self.worker_id = worker_id
            test_mod = request.node.name.split('[')[0]
            test_name = request.node.name.split('[')[1].rstrip(']')
            self.servername = '{}.{}_{}'.format(test_mod, test_name, worker_id)
            self.proc = None
        def is_running(self):
            cmdstr = 'jack_wait -s{} -w -t1'.format(self.servername)
            try:
                resp = subprocess.check_output(shlex.split(cmdstr))
            except subprocess.CalledProcessError as e:
                return False
            if isinstance(resp, bytes):
                resp = resp.decode('UTF-8')
            return 'server is available' in resp
        def wait_for_stop(self):
            cmdstr = 'jack_wait -s{} -q'.format(self.servername)
            subprocess.check_call(shlex.split(cmdstr))
        def wait_for_start(self):
            cmdstr = 'jack_wait -s{} -w'.format(self.servername)
            subprocess.check_call(shlex.split(cmdstr))
        def start(self):
            if self.is_running():
                if self.proc is not None:
                    return
                self.wait_for_stop()
            cmdstr = 'jackd -n{} -ddummy -r48000 -p1024'.format(self.servername)
            self.proc = subprocess.Popen(shlex.split(cmdstr))
            self.wait_for_start()
        def stop(self):
            p = self.proc
            if p is None:
                return
            self.proc = None
            p.terminate()
            p.wait()
            if self.is_running():
                self.wait_for_stop()
        def __enter__(self):
            self.start()
            return self
        def __exit__(self, *args):
            self.stop()
        def __repr__(self):
            return '<{self.__class__.__name__}: {self}>'.format(self=self)
        def __str__(self):
            return self.servername

    server = JackDServer(worker_id)

    monkeypatch.setenv('JACK_DEFAULT_SERVER', server.servername)
    monkeypatch.setenv('JACK_NO_START_SERVER', '1')

    return server

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
            self.servername = jackd_server.servername
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

    return {'client':listen_client, 'server':jackd_server}
