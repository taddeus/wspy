#!/usr/bin/env python
import sys
import logging
from os.path import abspath, dirname

basepath = abspath(dirname(abspath(__file__)) + '/..')
sys.path.insert(0, basepath)

from server import Server


class EchoServer(Server):
    def onmessage(self, client, message):
        Server.onmessage(self, client, message)
        client.send(message)


if __name__ == '__main__':
    EchoServer(8000, 'localhost',
               #secure=True, keyfile='cert.pem', certfile='cert.pem',
               loglevel=logging.DEBUG).run()
