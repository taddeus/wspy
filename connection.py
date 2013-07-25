import struct

from frame import ControlFrame, OPCODE_CLOSE, OPCODE_PING, OPCODE_PONG, \
                  OPCODE_CONTINUATION
from message import create_message
from errors import SocketClosed, PingError


class Connection(object):
    """
    A Connection uses a websocket instance to send and receive (optionally
    fragmented) messages, which are Message instances. Control frames are
    handled automatically in the way specified by RFC 6455.

    To use the Connection class, it should be extended and the extending class
    should implement the on*() event handlers.
    """
    def __init__(self, sock):
        """
        `sock` is a websocket instance which has completed its handshake.
        """
        self.sock = sock

        self.close_frame_received = False
        self.ping_sent = False
        self.ping_payload = None

        self.onopen()

    def send(self, message, fragment_size=None, mask=False):
        """
        Send a message. If `fragment_size` is specified, the message is
        fragmented into multiple frames whose payload size does not extend
        `fragment_size`.
        """
        if fragment_size is None:
            self.sock.send(message.frame(mask=mask))
        else:
            self.sock.send(*message.fragment(fragment_size, mask=mask))

    def receive(self):
        """
        Receive a message. A message may consist of multiple (ordered) data
        frames. A control frame may be delivered at any time, also when
        expecting the next continuation frame of a fragmented message. These
        control frames are handled immediately by handle_control_frame().
        """
        fragments = []

        while not len(fragments) or not fragments[-1].final:
            frame = self.sock.recv()

            if isinstance(frame, ControlFrame):
                self.handle_control_frame(frame)
            elif len(fragments) and frame.opcode != OPCODE_CONTINUATION:
                raise ValueError('expected continuation/control frame, got %s '
                                 'instead' % frame)
            else:
                fragments.append(frame)

        payload = bytearray()

        for f in fragments:
            payload += f.payload

        return create_message(fragments[0].opcode, payload)

    def handle_control_frame(self, frame):
        """
        Handle a control frame as defined by RFC 6455.
        """
        if frame.opcode == OPCODE_CLOSE:
            # Close the connection from this end as well
            self.close_frame_received = True
            code, reason = frame.unpack_close()

            # No more receiving data after a close message
            raise SocketClosed(code, reason)

        elif frame.opcode == OPCODE_PING:
            # Respond with a pong message with identical payload
            self.sock.send(ControlFrame(OPCODE_PONG, frame.payload))

        elif frame.opcode == OPCODE_PONG:
            # Assert that the PONG payload is identical to that of the PING
            if not self.ping_sent:
                raise PingError('received PONG while no PING was sent')

            self.ping_sent = False

            if frame.payload != self.ping_payload:
                raise PingError('received PONG with invalid payload')

            self.ping_payload = None
            self.onpong(frame.payload)

    def receive_forever(self):
        """
        Receive and handle messages in an endless loop. A message may consist
        of multiple data frames, but this is not visible for onmessage().
        Control messages (or control frames) are handled automatically.
        """
        while True:
            try:
                self.onmessage(self.receive())
            except SocketClosed as e:
                self.close(e.code, e.reason)
                break
            except Exception as e:
                self.onerror(e)

    def send_ping(self, payload=''):
        """
        Send a PING control frame with an optional payload.
        """
        self.sock.send(ControlFrame(OPCODE_PING, payload))
        self.ping_payload = payload
        self.ping_sent = True
        self.onping(payload)

    def close(self, code=None, reason=''):
        """
        Close the socket by sending a CLOSE frame and waiting for a response
        close message, unless such a message has already been received earlier
        (prior to calling this function, for example). The onclose() handler is
        called after the response has been received, but before the socket is
        actually closed. This order was chosen to prevent errors in
        stringification in the onclose() handler. For example,
        socket.getpeername() raises a Bad file descriptor error then the socket
        is closed.
        """
        # Send CLOSE frame
        payload = '' if code is None else struct.pack('!H', code) + reason
        self.sock.send(ControlFrame(OPCODE_CLOSE, payload))

        # Receive CLOSE frame
        if not self.close_frame_received:
            frame = self.sock.recv()

            if frame.opcode != OPCODE_CLOSE:
                raise ValueError('expected CLOSE frame, got %s instead' % frame)

            res_code, res_reason = frame.unpack_close()

            # FIXME: check if res_code == code and res_reason == reason?

            # FIXME: alternatively, keep receiving frames in a loop until a
            # CLOSE frame is received, so that a fragmented chain may arrive
            # fully first

        self.onclose(code, reason)
        self.sock.close()

    def onopen(self):
        """
        Called after the connection is initialized.
        """
        return NotImplemented

    def onmessage(self, message):
        """
        Called when a message is received. `message` is a Message object, which
        can be constructed from a single frame or multiple fragmented frames.
        """
        return NotImplemented

    def onping(self, payload):
        """
        Called after a PING control frame has been sent. This handler could be
        used to start a timeout handler for a PONG frame that is not received
        in time.
        """
        return NotImplemented

    def onpong(self, payload):
        """
        Called when a PONG control frame is received.
        """
        return NotImplemented

    def onclose(self, code, reason):
        """
        Called when the socket is closed by either end point.
        """
        return NotImplemented

    def onerror(self, e):
        """
        Handle a raised exception.
        """
        return NotImplemented
