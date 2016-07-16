from setuptools import setup

setup(
    name = 'python-ltc',
    version = '0.0.1',
    author = 'Matthew Reid',
    author_email = 'matt@nomadic-recording.com',
    description = 'Timecode Tools',
    packages=['pyltc'],
    include_package_data=True,
    install_requires=['numpy', 'scipy'],
    setup_requires=['setuptools-markdown'],
    long_description_markdown_filename='README.md',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)
