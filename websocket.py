import re
import socket
from hashlib import sha1

from frame import receive_frame
from errors import HandshakeError


WS_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
WS_VERSION = '13'


def split_stripped(value, delim=','):
    return map(str.strip, str(value).split(delim))


class websocket(object):
    """
    Implementation of web socket, upgrades a regular TCP socket to a websocket
    using the HTTP handshakes and frame (un)packing, as specified by RFC 6455.

    Server example:
    >>> sock = websocket()
    >>> sock.bind(('', 8000))
    >>> sock.listen()

    >>> client = sock.accept()
    >>> client.send(Frame(...))
    >>> frame = client.recv()

    Client example:
    >>> sock = websocket()
    >>> sock.connect(('', 8000))
    """
    def __init__(self, sock=None, protocols=[], extensions=[], sfamily=socket.AF_INET,
                 sproto=0):
        """
        Create a regular TCP socket of family `family` and protocol

        `sock` is an optional regular TCP socket to be used for sending binary
        data. If not specified, a new socket is created.

        `protocols` is a list of supported protocol names.

        `extensions` is a list of supported extensions.

        `sfamily` and `sproto` are used for the regular socket constructor.
        """
        self.protocols = protocols
        self.extensions = extensions
        self.sock = sock or socket.socket(sfamily, socket.SOCK_STREAM, sproto)

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
        wsock.server_handshake()
        return wsock, address

    def connect(self, address):
        """
        Equivalent to socket.connect(), but sends an client handshake request
        after connecting.
        """
        self.sock.sonnect(address)
        self.client_handshake()

    def send(self, *args):
        """
        Send a number of frames.
        """
        for frame in args:
            print 'send frame:', frame, 'to %s:%d' % self.sock.getpeername(), frame.payload
            self.sock.sendall(frame.pack())

    def recv(self):
        """
        Receive a single frames. This can be either a data frame or a control
        frame.
        """
        frame = receive_frame(self.sock)
        print 'receive frame:', frame, 'from %s:%d' % self.sock.getpeername()
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

    def server_handshake(self):
        """
        Execute a handshake as the server end point of the socket. If the HTTP
        request headers sent by the client are invalid, a HandshakeError
        is raised.
        """
        raw_headers = self.sock.recv(512).decode('utf-8', 'ignore')

        # request must be HTTP (at least 1.1) GET request, find the location
        location = re.search(r'^GET (.*) HTTP/1.1\r\n', raw_headers).group(1)
        headers = re.findall(r'(.*?): (.*?)\r\n', raw_headers)
        header_names = [name for name, value in headers]

        def header(name):
            return ', '.join([v for n, v in headers if n == name])

        # Check if headers that MUST be present are actually present
        for name in ('Host', 'Upgrade', 'Connection', 'Sec-WebSocket-Key',
                     'Origin', 'Sec-WebSocket-Version'):
            if name not in header_names:
                raise HandshakeError('missing "%s" header' % name)

        # Check WebSocket version used by client
        version = header('Sec-WebSocket-Version')

        if version != WS_VERSION:
            raise HandshakeError('WebSocket version %s requested (only %s '
                                 'is supported)' % (version, WS_VERSION))

        # Only supported protocols are returned
        proto = header('Sec-WebSocket-Extensions')
        protocols = split_stripped(proto) if proto else []
        protocols = [p for p in protocols if p in self.protocols]

        # Only supported extensions are returned
        ext = header('Sec-WebSocket-Extensions')
        extensions = split_stripped(ext) if ext else []
        extensions = [e for e in extensions if e in self.extensions]

        # Encode acceptation key using the WebSocket GUID
        key = header('Sec-WebSocket-Key')
        accept = sha1(key + WS_GUID).digest().encode('base64')

        # Construct HTTP response header
        shake = 'HTTP/1.1 101 Web Socket Protocol Handshake\r\n'
        shake += 'Upgrade: WebSocket\r\n'
        shake += 'Connection: Upgrade\r\n'
        shake += 'WebSocket-Origin: %s\r\n' % header('Origin')
        shake += 'WebSocket-Location: ws://%s%s\r\n' \
                 % (header('Host'), location)
        shake += 'Sec-WebSocket-Accept: %s\r\n' % accept

        if protocols:
            shake += 'Sec-WebSocket-Protocol: %s\r\n' % ', '.join(protocols)

        if extensions:
            shake += 'Sec-WebSocket-Extensions: %s\r\n' % ', '.join(extensions)

        self.sock.send(shake + '\r\n')

    def client_handshake(self):
        """
        Execute a handshake as the client end point of the socket. May raise a
        HandshakeError if the server response is invalid.
        """
        # TODO: implement HTTP request headers for client handshake
        raise NotImplementedError()
