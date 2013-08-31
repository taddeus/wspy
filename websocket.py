import socket
import ssl

from frame import receive_frame
from handshake import ServerHandshake, ClientHandshake
from errors import SSLError


INHERITED_ATTRS = ['bind', 'close', 'listen', 'fileno', 'getpeername',
                   'getsockname', 'getsockopt', 'setsockopt', 'setblocking',
                   'settimeout', 'gettimeout', 'shutdown', 'family', 'type',
                   'proto']


class websocket(object):
    """
    Implementation of web socket, upgrades a regular TCP socket to a websocket
    using the HTTP handshakes and frame (un)packing, as specified by RFC 6455.
    The API of a websocket is identical to that of a regular socket, as
    illustrated by the examples below.

    Server example:
    >>> import wspy, socket
    >>> sock = wspy.websocket()
    >>> sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    >>> sock.bind(('', 8000))
    >>> sock.listen(5)

    >>> client = sock.accept()
    >>> client.send(wspy.Frame(wspy.OPCODE_TEXT, 'Hello, Client!'))
    >>> frame = client.recv()

    Client example:
    >>> import wspy
    >>> sock = wspy.websocket(location='/my/path')
    >>> sock.connect(('', 8000))
    >>> sock.send(wspy.Frame(wspy.OPCODE_TEXT, 'Hello, Server!'))
    """
    def __init__(self, sock=None, protocols=[], extensions=[], origin=None,
                 location='/', trusted_origins=[], locations=[], auth=None,
                 sfamily=socket.AF_INET, sproto=0):
        """
        Create a regular TCP socket of family `family` and protocol

        `sock` is an optional regular TCP socket to be used for sending binary
        data. If not specified, a new socket is created.

        `protocols` is a list of supported protocol names.

        `extensions` is a list of supported extensions (`Extension` instances).

        `origin` (for client sockets) is the value for the "Origin" header sent
        in a client handshake .

        `location` (for client sockets) is optional, used to request a
        particular resource in the HTTP handshake. In a URL, this would show as
        ws://host[:port]/<location>. Use this when the server serves multiple
        resources (see `locations`).

        `trusted_origins` (for server sockets) is a list of expected values
        for the "Origin" header sent by a client. If the received Origin header
        has value not in this list, a HandshakeError is raised. If the list is
        empty (default), all origins are excepted.

        `locations` (for server sockets) is an optional list of resources
        serverd by this server. If specified (without trailing slashes), these
        are used to verify the resource location requested by a client. The
        requested location may be used to distinquish different services in a
        server implementation.

        `auth` is optional, used for HTTP Basic or Digest authentication during
        the handshake. It must be specified as a (username, password) tuple.

        `sfamily` and `sproto` are used for the regular socket constructor.
        """
        self.protocols = protocols
        self.extensions = extensions
        self.origin = origin
        self.location = location
        self.trusted_origins = trusted_origins
        self.locations = locations
        self.auth = auth

        self.secure = False

        self.handshake_sent = False

        self.hooks_send = []
        self.hooks_recv = []

        self.sock = sock or socket.socket(sfamily, socket.SOCK_STREAM, sproto)

    def __getattr__(self, name):
        if name in INHERITED_ATTRS:
            return getattr(self.sock, name)

        raise AttributeError("'%s' has no attribute '%s'"
                             % (self.__class__.__name__, name))

    def accept(self):
        """
        Equivalent to socket.accept(), but transforms the socket into a
        websocket instance and sends a server handshake (after receiving a
        client handshake). Note that the handshake may raise a HandshakeError
        exception.
        """
        sock, address = self.sock.accept()
        wsock = websocket(sock)
        wsock.secure = self.secure
        ServerHandshake(wsock).perform(self)
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
            for hook in self.hooks_send:
                frame = hook(frame)

            #print 'send frame:', frame, 'to %s:%d' % self.sock.getpeername()
            self.sock.sendall(frame.pack())

    def recv(self):
        """
        Receive a single frames. This can be either a data frame or a control
        frame.
        """
        frame = receive_frame(self.sock)

        for hook in self.hooks_recv:
            frame = hook(frame)

        #print 'receive frame:', frame, 'from %s:%d' % self.sock.getpeername()
        return frame

    def recvn(self, n):
        """
        Receive exactly `n` frames. These can be either data frames or control
        frames, or a combination of both.
        """
        return [self.recv() for i in xrange(n)]

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

    def add_hook(self, send=None, recv=None, prepend=False):
        """
        Add a pair of send and receive hooks that are called for each frame
        that is sent or received. A hook is a function that receives a single
        argument - a Frame instance - and returns a `Frame` instance as well.

        `prepend` is a flag indicating whether the send hook is prepended to
        the other send hooks. This is expecially useful when a program uses
        extensions such as the built-in `DeflateFrame` extension. These
        extensions are installed using these hooks as well.

        For example, the following code creates a `Frame` instance for data
        being sent and removes the instance for received data. This way, data
        can be sent and received as if on a regular socket.
        >>> import wspy
        >>> sock.add_hook(lambda data: tswpy.Frame(tswpy.OPCODE_TEXT, data),
        >>>               lambda frame: frame.payload)

        To add base64 encoding to the example above:
        >>> import base64
        >>> sock.add_hook(base64.encodestring, base64.decodestring, True)

        Note that here `prepend=True`, so that data passed to `send()` is first
        encoded and then packed into a frame. Of course, one could also decide
        to add the base64 hook first, or to return a new `Frame` instance with
        base64-encoded data.
        """
        if send:
            self.hooks_send.insert(0 if prepend else -1, send)

        if recv:
            self.hooks_recv.insert(-1 if prepend else 0, recv)
