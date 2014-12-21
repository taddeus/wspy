#!/usr/bin/env python
from distutils.core import setup
setup(
    name='wspy',
    version='0.91',
    description='A standalone implementation of websockets (RFC 6455).',
    author='Taddeus Kroes',
    author_email='taddeus@kompiler.org',
    url='https://github.com/taddeus/wspy',
    package_dir={'wspy': '.'},
    packages=['wspy'],
    license='3-clause BSD License'
)
