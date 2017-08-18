import sys
from setuptools import setup, find_packages

def convert_readme():
    try:
        import pypandoc
    except ImportError:
        return read_rst()
    rst = pypandoc.convert_file('README.md', 'rst')
    with open('README.rst', 'w') as f:
        f.write(rst)
    return rst

def read_rst():
    try:
        with open('README.rst', 'r') as f:
            rst = f.read()
    except IOError:
        rst = None
    return rst

def get_long_description():
    if {'sdist', 'bdist_wheel'} & set(sys.argv):
        long_description = convert_readme()
    else:
        long_description = read_rst()
    return long_description

if {'sdist', 'bdist_wheel'} & set(sys.argv):
    convert_readme()

setup(
    name = 'python-ltc',
    version = 'v0.0.2',
    author = 'Matthew Reid',
    author_email = 'matt@nomadic-recording.com',
    url='https://github.com/nocarryr/python-ltc',
    license='GPLv3',
    description = 'Tools for working with LTC (Linear Timecode)',
    packages=find_packages(exclude=['tests*']),
    include_package_data=True,
    install_requires=['numpy', 'scipy', 'JACK-Client'],
    setup_requires=['pypandoc'],
    long_description=get_long_description(),
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Environment :: Console',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Multimedia',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Sound/Audio :: MIDI',
        'Topic :: Multimedia :: Video',
        'Topic :: Multimedia :: Video :: Non-Linear Editor',
    ],
)
