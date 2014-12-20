#!/usr/bin/env python
import sys
import logging
from os.path import abspath, dirname

basepath = abspath(dirname(abspath(__file__)) + '/..')
sys.path.insert(0, basepath)

from server import Server
from deflate_frame import DeflateFrame


class EchoServer(Server):
    def onmessage(self, client, message):
        Server.onmessage(self, client, message)
        client.send(message)


if __name__ == '__main__':
    EchoServer(('localhost', 8000),
               #extensions=[DeflateFrame(no_context_takeover=True)],
               extensions=[DeflateFrame()],
               #ssl_args=dict(keyfile='cert.pem', certfile='cert.pem'),
               loglevel=logging.DEBUG).run()
