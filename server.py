import socket
import logging
import time
from traceback import format_exc
from threading import Thread
from ssl import SSLError

from websocket import websocket
from connection import Connection
from frame import CLOSE_NORMAL
from errors import HandshakeError


class Server(object):
    """
    Websocket server, manages multiple client connections.

    Example usage:
    >>> import twspy

    >>> class GameServer(twspy.Server):
    >>>     def onopen(self, client):
    >>>         # client connected

    >>>     def onclose(self, client):
    >>>         # client disconnected

    >>>     def onmessage(self, client, message):
    >>>         # handle message from client

    >>> GameServer(8000).run()
    """

    def __init__(self, port, hostname='', loglevel=logging.INFO, protocols=[],
                 secure=False, max_join_time=2.0, **kwargs):
        """
        Constructor for a simple websocket server.

        `hostname` and `port` form the address to bind the websocket to.

        `loglevel` values should be imported from the logging module.
        logging.INFO only shows server start/stop messages, logging.DEBUG shows
        clients (dis)connecting and messages being sent/received.

        `protocols` is a list of supported protocols, passed directly to the
        websocket constructor.

        `secure` is a flag indicating whether the server is SSL enabled. In
        this case, `keyfile` and `certfile` must be specified. Any additional
        keyword arguments are passed to websocket.enable_ssl (and thus to
        ssl.wrap_socket).

        `max_join_time` is the maximum time (in seconds) to wait for client
        responses after sending CLOSE frames, it defaults to 2 seconds.
        """
        logging.basicConfig(level=loglevel,
                format='%(asctime)s: %(levelname)s: %(message)s',
                datefmt='%H:%M:%S')

        scheme = 'wss' if secure else 'ws'
        logging.info('Starting server at %s://%s:%d', scheme, hostname, port)

        self.sock = websocket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if secure:
            self.sock.enable_ssl(server_side=True, **kwargs)

        self.sock.bind((hostname, port))
        self.sock.listen(5)

        self.clients = []
        self.client_threads = []
        self.protocols = protocols

        self.max_join_time = max_join_time

    def run(self):
        while True:
            try:
                sock, address = self.sock.accept()

                client = Client(self, sock)
                self.clients.append(client)
                logging.debug('Registered client %s', client)

                thread = Thread(target=client.receive_forever)
                thread.daemon = True
                thread.start()
                self.client_threads.append(thread)
            except SSLError as e:
                logging.error('SSL error: %s', e)
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
            client.send_close_frame()

        start_time = time.time()

        while time.time() - start_time <= self.max_join_time \
                and any(t.is_alive() for t in self.client_threads):
            time.sleep(0.050)

    def remove_client(self, client, code, reason):
        self.clients.remove(client)
        self.onclose(client, code, reason)

    def onopen(self, client):
        logging.debug('Opened socket to %s', client)

    def onmessage(self, client, message):
        logging.debug('Received %s from %s', message, client)

    def onping(self, client, payload):
        logging.debug('Sent ping "%s" to %s', payload, client)

    def onpong(self, client, payload):
        logging.debug('Received pong "%s" from %s', payload, client)

    def onclose(self, client, code, reason):
        msg = 'Closed socket to %s' % client

        if code is not None:
            msg += ' [%d]' % code

        if len(reason):
            msg += ': ' + reason

        logging.debug(msg)

    def onerror(self, client, e):
        logging.error(format_exc(e))


class Client(Connection):
    def __init__(self, server, sock):
        self.server = server
        super(Client, self).__init__(sock)

    def __str__(self):
        try:
            return '<Client at %s:%d>' % self.sock.getpeername()
        except socket.error:
            return '<Client on closed socket>'

    def send(self, message, fragment_size=None, mask=False):
        logging.debug('Sending %s to %s', message, self)
        Connection.send(self, message, fragment_size=fragment_size, mask=mask)

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

    def onerror(self, e):
        self.server.onerror(self, e)


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    Server(port, loglevel=logging.DEBUG).run()
