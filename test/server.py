#!/usr/bin/env python
import sys
import logging
from os.path import abspath, dirname

basepath = abspath(dirname(abspath(__file__)) + '/..')
sys.path.insert(0, basepath)

from server import Server
from extension import DeflateFrame


class EchoServer(Server):
    def onmessage(self, client, message):
        Server.onmessage(self, client, message)
        client.send(message)


class WebkitDeflateFrame(DeflateFrame):
    name = 'x-webkit-deflate-frame'


if __name__ == '__main__':
    deflate = WebkitDeflateFrame()
    #deflate = WebkitDeflateFrame(defaults={'no_context_takeover': True})
    EchoServer(('localhost', 8000), extensions=[deflate],
               #ssl_args=dict(keyfile='cert.pem', certfile='cert.pem'),
               loglevel=logging.DEBUG).run()
