import socket
import logging
from traceback import format_exc

from websocket import WebSocket


class Server(object):
    def __init__(self, port, address='', log_level=logging.INFO, protocols=[],
            encoding=None):
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
        self.encoding = encoding

    def run(self):
        while True:
            try:
                client_socket, address = self.sock.accept()
                logging.debug('Attempting handshake with %s:%d' % address)
                self.handshake(client_socket)

                client = Client(client_socket, address, self)
                self.clients.append(client)
                logging.info('Registered client %s', client)
                self.onopen(client)

                client.run_threaded()
            except KeyboardInterrupt:
                logging.info('Received interrupt, stopping server...')
                break
            except Exception as e:
                logging.error(format_exc(e))

    def onopen(self, client):
        """
        Called when a new client connects.
        """
        pass

    def onclose(self, client):
        """
        Called when a client disconnects.
        """
        pass

    def onmessage(self, client, message):
        """
        Called when a message is received from some client. `message' is a
        Message object
        """
        raise NotImplemented


class Client(WebSocket):
    def __init__(self, server, sock, address):
        super(Client, self).__init__(sock, address)
        self.server = server

    def handle_message(self, message):
        self.server.onmessage(self, message)


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    Server(port=port, log_level=logging.DEBUG, encoding='utf-8').run()
