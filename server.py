import socket
import logging
from traceback import format_exc
from threading import Thread, Lock

from websocket import WebSocket
from exceptions import InvalidRequest
from frame import CLOSE_NORMAL


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
                sock, address = self.sock.accept()
                client = Client(self, sock, address)

                client.server_handshake()
                self.clients.append(client)
                logging.info('Registered client %s', client)

                thread = Thread(target=client.receive_forever)
                thread.daemon = True
                thread.start()
            except InvalidRequest as e:
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
            msg += ' "%s"' % reason

        logging.debug(msg)


class Client(WebSocket):
    def __init__(self, server, sock, address):
        super(Client, self).__init__(sock)
        self.server = server
        self.address = address
        self.send_lock = Lock()

    def send_frame(self, frame):
        self.send_lock.acquire()
        WebSocket.send_frame(self, frame)
        self.send_lock.release()

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
        logging.error(format_exc(e))

    def __str__(self):
        return '<Client at %s:%d>' % self.address


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    Server(port, log_level=logging.DEBUG).run()
