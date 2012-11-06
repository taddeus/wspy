import re
from hashlib import sha1
from threading import Thread

from frame import FrameReceiver
from message import create_message
from exceptions import SocketClosed


WS_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
WS_VERSION = '13'


class WebSocket(FrameReceiver):
    def __init__(self, sock, address, encoding=None):
        super(WebSocket, self).__init__(sock)
        self.address = address
        self.encoding = encoding

    def send_message(self, message, fragment_size=None):
        if fragment_size is None:
            self.send_frame(message.frame())
        else:
            map(self.send_frame, message.fragment(fragment_size))

    def send_frame(self, frame):
        self.sock.sendall(frame.pack())

    def receive_message(self):
        frames = self.receive_fragments()
        payload = ''.join([f.payload for f in frames])
        return create_message(frames[0].opcode, payload)

    def handshake(self):
        raw_headers = self.sock.recv(512)

        if self.encoding:
            raw_headers = raw_headers.decode(self.encoding, 'ignore')

        location = re.search(r'^GET (.*) HTTP/1.1\r\n', raw_headers).group(1)
        headers = dict(re.findall(r'(.*?): (.*?)\r\n', raw_headers))

        # Check if headers that MUST be present are actually present
        for name in ('Host', 'Upgrade', 'Connection', 'Sec-WebSocket-Key',
                     'Origin', 'Sec-WebSocket-Version'):
            assert name in headers

        # Check WebSocket version used by client
        assert headers['Sec-WebSocket-Version'] == WS_VERSION

        # Make sure the requested protocols are supported by this server
        if 'Sec-WebSocket-Protocol' in headers:
            parts = headers['Sec-WebSocket-Protocol'].split(',')
            protocols = map(str.strip, parts)

            for protocol in protocols:
                assert protocol in self.protocols
        else:
            protocols = []

        key = headers['Sec-WebSocket-Key']
        accept = sha1(key + WS_GUID).digest().encode('base64')
        shake = 'HTTP/1.1 101 Web Socket Protocol Handshake\r\n'
        shake += 'Upgrade: WebSocket\r\n'
        shake += 'Connection: Upgrade\r\n'
        shake += 'WebSocket-Origin: %s\r\n' % headers['Origin']
        shake += 'WebSocket-Location: ws://%s%s\r\n' % (headers['Host'], location)
        shake += 'Sec-WebSocket-Accept: %s\r\n' % accept

        if self.protocols:
            shake += 'Sec-WebSocket-Protocol: %s\r\n' \
                     % ', '.join(self.protocols)

        self.sock.send(shake + '\r\n')

        self.onopen()

    def receive_forever(self):
        try:
            while True:
                self.onmessage(self, self.receive_message())
        except SocketClosed:
            self.onclose()

    def run_threaded(self, daemon=True):
        t = Thread(target=self.receive_forever)
        t.daemon = daemon
        t.start()

    def onopen(self):
        """
        Called after the handshake has completed.
        """
        pass

    def onclose(self):
        """
        Called when the other end of the socket disconnects.
        """
        pass

    def onmessage(self, message):
        """
        Called when a message is received. `message' is a Message object, which
        can be constructed from a single frame or multiple fragmented frames.
        """
        raise NotImplemented

    def close(self):
        raise SocketClosed()
