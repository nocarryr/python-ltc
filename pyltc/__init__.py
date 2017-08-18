import pkg_resources

try:
    __version__ = pkg_resources.require('python-ltc')[0].version
except: # pragma: no cover
    __version__ = 'unknown'
