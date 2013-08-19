import socket
import ssl

from frame import receive_frame
from handshake import ServerHandshake, ClientHandshake
from errors import SSLError


class websocket(object):
    """
    Implementation of web socket, upgrades a regular TCP socket to a websocket
    using the HTTP handshakes and frame (un)packing, as specified by RFC 6455.
    The API of a websocket is identical to that of a regular socket, as
    illustrated by the examples below.

    Server example:
    >>> import twspy, socket
    >>> sock = twspy.websocket()
    >>> sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    >>> sock.bind(('', 8000))
    >>> sock.listen()

    >>> client = sock.accept()
    >>> client.send(twspy.Frame(twspy.OPCODE_TEXT, 'Hello, Client!'))
    >>> frame = client.recv()

    Client example:
    >>> import twspy
    >>> sock = twspy.websocket(location='/my/path')
    >>> sock.connect(('', 8000))
    >>> sock.send(twspy.Frame(twspy.OPCODE_TEXT, 'Hello, Server!'))
    """
    def __init__(self, sock=None, protocols=[], extensions=[], origin=None,
                 trusted_origins=[], location='/', auth=None,
                 sfamily=socket.AF_INET, sproto=0):
        """
        Create a regular TCP socket of family `family` and protocol

        `sock` is an optional regular TCP socket to be used for sending binary
        data. If not specified, a new socket is created.

        `protocols` is a list of supported protocol names.

        `extensions` is a list of supported extension classes.

        `origin` (for client sockets) is the value for the "Origin" header sent
        in a client handshake .

        `trusted_origins` (for servere sockets) is a list of expected values
        for the "Origin" header sent by a client. If the received Origin header
        has value not in this list, a HandshakeError is raised. If the list is
        empty (default), all origins are excepted.

        `location` is optional, used for the HTTP handshake. In a URL, this
        would show as ws://host[:port]/path.

        `auth` is optional, used for HTTP Basic or Digest authentication during
        the handshake. It must be specified as a (username, password) tuple.

        `sfamily` and `sproto` are used for the regular socket constructor.
        """
        self.protocols = protocols
        self.extensions = extensions
        self.origin = origin
        self.trusted_origins = trusted_origins
        self.location = location
        self.auth = auth
        self.sock = sock or socket.socket(sfamily, socket.SOCK_STREAM, sproto)
        self.secure = False
        self.handshake_sent = False

    def bind(self, address):
        self.sock.bind(address)

    def listen(self, backlog):
        self.sock.listen(backlog)

    def accept(self):
        """
        Equivalent to socket.accept(), but transforms the socket into a
        websocket instance and sends a server handshake (after receiving a
        client handshake). Note that the handshake may raise a HandshakeError
        exception.
        """
        sock, address = self.sock.accept()
        wsock = websocket(sock)
        ServerHandshake(wsock).perform()
        wsock.handshake_sent = True
        return wsock, address

    def connect(self, address):
        """
        Equivalent to socket.connect(), but sends an client handshake request
        after connecting.

        `address` is a (host, port) tuple of the server to connect to.
        """
        self.sock.connect(address)
        ClientHandshake(self).perform()
        self.handshake_sent = True

    def send(self, *args):
        """
        Send a number of frames.
        """
        for frame in args:
            for ext in self.extensions:
                frame = ext.hook_send(frame)

            #print 'send frame:', frame, 'to %s:%d' % self.sock.getpeername()
            self.sock.sendall(frame.pack())

    def recv(self):
        """
        Receive a single frames. This can be either a data frame or a control
        frame.
        """
        frame = receive_frame(self.sock)

        for ext in reversed(self.extensions):
            frame = ext.hook_recv(frame)

        #print 'receive frame:', frame, 'from %s:%d' % self.sock.getpeername()
        return frame

    def recvn(self, n):
        """
        Receive exactly `n` frames. These can be either data frames or control
        frames, or a combination of both.
        """
        return [self.recv() for i in xrange(n)]

    def getpeername(self):
        return self.sock.getpeername()

    def getsockname(self):
        return self.sock.getsockname()

    def setsockopt(self, level, optname, value):
        self.sock.setsockopt(level, optname, value)

    def getsockopt(self, level, optname):
        return self.sock.getsockopt(level, optname)

    def close(self):
        self.sock.close()

    def enable_ssl(self, *args, **kwargs):
        """
        Transforms the regular socket.socket to an ssl.SSLSocket for secure
        connections. Any arguments are passed to ssl.wrap_socket:
        http://docs.python.org/dev/library/ssl.html#ssl.wrap_socket
        """
        if self.handshake_sent:
            raise SSLError('can only enable SSL before handshake')

        self.secure = True
        self.sock = ssl.wrap_socket(self.sock, *args, **kwargs)
