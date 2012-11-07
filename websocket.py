import re
import struct
from hashlib import sha1
from threading import Thread

from frame import ControlFrame, receive_fragments, receive_frame, \
        OPCODE_CLOSE, OPCODE_PING, OPCODE_PONG
from message import create_message
from exceptions import SocketClosed, PingError


WS_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
WS_VERSION = '13'


class WebSocket(object):
    def __init__(self, sock, encoding=None):
        self.sock = sock
        self.encoding = encoding

        self.received_close_params = None
        self.close_frame_sent = False

        self.ping_sent = False
        self.ping_payload = None

    def send_message(self, message, fragment_size=None):
        if fragment_size is None:
            self.send_frame(message.frame())
        else:
            map(self.send_frame, message.fragment(fragment_size))

    def send_frame(self, frame):
        self.sock.sendall(frame.pack())

    def handle_control_frame(self, frame):
        if frame.opcode == OPCODE_CLOSE:
            self.received_close_params = frame.unpack_close()
        elif frame.opcode == OPCODE_PING:
            # Respond with a pong message with identical payload
            self.send_frame(ControlFrame(OPCODE_PONG, frame.payload))
        elif frame.opcode == OPCODE_PONG:
            # Assert that the PONG payload is identical to that of the PING
            if not self.ping_sent:
                raise PingError('received PONG while no PING was sent')

            self.ping_sent = False

            if frame.payload != self.ping_payload:
                raise PingError('received PONG with invalid payload')

            self.ping_payload = None
            self.onpong(frame.payload)

    def receive_message(self):
        frames = receive_fragments(self.sock, self.handle_control_frame)
        payload = ''.join([f.payload for f in frames])
        return create_message(frames[0].opcode, payload)

    def send_handshake(self):
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

                if self.received_close_params is not None:
                    self.handle_close(*self.received_close_params)
                    break
        except SocketClosed:
            self.onclose(None, '')

    def run_threaded(self, daemon=True):
        t = Thread(target=self.receive_forever)
        t.daemon = daemon
        t.start()

    def send_close(self, code, reason):
        payload = '' if code is None else struct.pack('!H', code)
        self.send_frame(ControlFrame(OPCODE_CLOSE, payload))
        self.close_frame_sent = True

    def send_ping(self, payload=''):
        """
        Send a ping control frame with an optional payload.
        """
        self.send_frame(ControlFrame(OPCODE_PING, payload))
        self.ping_payload = payload
        self.ping_sent = True
        self.onping()

    def handle_close(self, code=None, reason=''):
        """
        Handle a close message by sending a response close message if no close
        message was sent before, and closing the connection. The onclose()
        handler is called afterwards.
        """
        if not self.close_frame_sent:
            payload = '' if code is None else struct.pack('!H', code)
            self.send_frame(ControlFrame(OPCODE_CLOSE, payload))

        self.sock.close()
        self.onclose(code, reason)

    def close(self, code=None, reason=''):
        """
        Close the socket by sending a close message and waiting for a response
        close message. The onclose() handler is called after the close message
        has been sent, but before the response has been received.
        """
        self.send_close(code, reason)
        # FIXME: swap the two lines below?
        self.onclose(code, reason)
        frame = receive_frame(self.sock)
        self.sock.close()

        if frame.opcode != OPCODE_CLOSE:
            raise ValueError('Expected close frame, got %s instead' % frame)

    def onopen(self):
        """
        Called after the handshake has completed.
        """
        pass

    def onmessage(self, message):
        """
        Called when a message is received. `message' is a Message object, which
        can be constructed from a single frame or multiple fragmented frames.
        """
        raise NotImplemented

    def onping(self, payload):
        """
        Called after a ping control frame has been sent. This handler could be
        used to start a timeout handler for a pong message that is not received
        in time.
        """
        raise NotImplemented

    def onpong(self, payload):
        """
        Called when a pong control frame is received.
        """
        raise NotImplemented

    def onclose(self, code, reason):
        """
        Called when the socket is closed by either end point.
        """
        pass
