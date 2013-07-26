#!/usr/bin/env python
import logging

from server import Server


class EchoServer(Server):
    def onmessage(self, client, message):
        Server.onmessage(self, client, message)
        client.send(message)


if __name__ == '__main__':
    EchoServer(8000, 'localhost',
               #secure=True, keyfile='cert.pem', certfile='cert.pem',
               loglevel=logging.DEBUG).run()
