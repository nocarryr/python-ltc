import shlex
import subprocess

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
def jackd_server(request):
    cmdstr = 'jackd -ddummy -r48000 -p1024'
    p = subprocess.Popen(shlex.split(cmdstr))
    def close_jackd():
        p.terminate()
    request.addfinalizer(close_jackd)
    return p
