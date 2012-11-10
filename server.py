import socket
import logging
from traceback import format_exc
from threading import Thread

from websocket import websocket
from connection import Connection
from frame import CLOSE_NORMAL
from exceptions import HandshakeError


class Server(object):
    def __init__(self, port, hostname='', loglevel=logging.INFO, protocols=[]):
        logging.basicConfig(level=loglevel,
                format='%(asctime)s: %(levelname)s: %(message)s',
                datefmt='%H:%M:%S')

        self.sock = websocket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        logging.info('Starting server at %s:%d', hostname, port)
        self.sock.bind((hostname, port))
        self.sock.listen(5)

        self.clients = []
        self.protocols = protocols

    def run(self):
        while True:
            try:
                sock, address = self.sock.accept()

                client = Client(self, sock, address)
                self.clients.append(client)
                logging.info('Registered client %s', client)

                thread = Thread(target=client.receive_forever)
                thread.daemon = True
                thread.start()
            except HandshakeError as e:
                logging.error('Invalid request: %s', e.message)
            except KeyboardInterrupt:
                logging.info('Received interrupt, stopping server...')
                break
            except Exception as e:
                logging.error(format_exc(e))

        self.quit_gracefully()

    def quit_gracefully(self):
        for client in self.clients:
            client.close(CLOSE_NORMAL)

    def remove_client(self, client, code, reason):
        self.clients.remove(client)
        self.onclose(client, code, reason)

    def onopen(self, client):
        logging.debug('Opened socket to %s' % client)

    def onmessage(self, client, message):
        logging.debug('Received %s from %s' % (message, client))

    def onping(self, client, payload):
        logging.debug('Sent ping "%s" to %s' % (payload, client))

    def onpong(self, client, payload):
        logging.debug('Received pong "%s" from %s' % (payload, client))

    def onclose(self, client, code, reason):
        msg = 'Closed socket to %s' % client

        if code is not None:
            msg += ' [%d]' % code

        if len(reason):
            msg += ': ' + reason

        logging.debug(msg)

    def onexception(self, client, e):
        logging.error(format_exc(e))


class Client(Connection):
    def __init__(self, server, sock):
        super(Client, self).__init__(sock)
        self.server = server

    def onopen(self):
        self.server.onopen(self)

    def onmessage(self, message):
        self.server.onmessage(self, message)

    def onping(self, payload):
        self.server.onping(self, payload)

    def onpong(self, payload):
        self.server.onpong(self, payload)

    def onclose(self, code, reason):
        self.server.remove_client(self, code, reason)

    def onexception(self, e):
        self.server.onexception(self, e)

    def __str__(self):
        return '<Client at %s:%d>' % self.sock.getpeername()


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    Server(port, loglevel=logging.DEBUG).run()
