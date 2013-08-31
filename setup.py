#!/usr/bin/env python
from distutils.core import setup


setup(name='twspy',
      version='0.8',
      description='A standalone implementation of websockets (RFC 6455)',
      author='Taddeus Kroes',
      author_email='taddeuskroes@gmail.com',
      url='https://github.com/taddeus/twspy',
      package_dir={'twspy': '.'},
      packages=['twspy'],
      license='3-clause BSD License')
