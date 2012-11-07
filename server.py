import socket
import logging
from traceback import format_exc

from websocket import WebSocket
from exceptions import InvalidRequest


class Server(object):
    def __init__(self, port, address='', log_level=logging.INFO, protocols=[]):
        logging.basicConfig(level=log_level,
                format='%(asctime)s: %(levelname)s: %(message)s',
                datefmt='%H:%M:%S')

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        logging.info('Starting server at %s:%d', address, port)
        self.sock.bind((address, port))
        self.sock.listen(5)

        self.clients = []
        self.protocols = protocols

    def run(self):
        while True:
            try:
                client_socket, address = self.sock.accept()
                client = Client(self, client_socket, address)
                client.handshake()
                self.clients.append(client)
                logging.info('Registered client %s', client)
                client.run_threaded()
            except InvalidRequest as e:
                logging.error('Invalid request: %s', e.message)
            except KeyboardInterrupt:
                logging.info('Received interrupt, stopping server...')
                break
            except Exception as e:
                logging.error(format_exc(e))

    def onopen(self, client):
        logging.debug('Opened socket to client %s' % client)

    def onmessage(self, client, message):
        logging.debug('Received %s from %s' % (message, client))

    def onping(self, client, payload):
        logging.debug('Sent ping "%s" to %s' % (payload, client))

    def onpong(self, client, payload):
        logging.debug('Received pong "%s" from %s' % (payload, client))

    def onclose(self, client):
        logging.debug('Closed socket to client %s' % client)


class Client(WebSocket):
    def __init__(self, server, sock, address):
        super(Client, self).__init__(sock, address)
        self.server = server

    def onopen(self):
        self.server.onopen(self)

    def onmessage(self, message):
        self.server.onmessage(self, message)

    def onping(self, payload):
        self.server.onping(self, payload)

    def onpong(self, payload):
        self.server.onpong(self, payload)

    def onclose(self):
        self.server.onclose(self)

    def __str__(self):
        return '<Client at %s:%d>' % self.address


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    Server(port, log_level=logging.DEBUG).run()
