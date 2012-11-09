import struct

from frame import ControlFrame, OPCODE_CLOSE, OPCODE_PING, OPCODE_PONG
from message import create_message
from exceptions import SocketClosed, PingError


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

        self.received_close_params = None
        self.close_frame_sent = False

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
        expecting the next data frame of a fragmented message. These control
        frames are handled immediately bu handle_control_frame().
        """
        fragments = []

        while not len(fragments) or not fragments[-1].final:
            frame = self.sock.recv()

            if isinstance(frame, ControlFrame):
                self.handle_control_frame(frame)

                # No more receiving data after a close message
                if frame.opcode == OPCODE_CLOSE:
                    break
            else:
                fragments.append(frame)

        payload = ''.join([f.payload for f in fragments])
        return create_message(fragments[0].opcode, payload)

    def handle_control_frame(self, frame):
        """
        Handle a control frame as defined by RFC 6455.
        """
        if frame.opcode == OPCODE_CLOSE:
            # Set parameters and keep receiving the current fragmented frame
            # chain, assuming that the CLOSE frame will be handled by
            # handle_close() as soon as possible
            self.received_close_params = frame.unpack_close()

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

                if self.received_close_params is not None:
                    self.handle_close(*self.received_close_params)
                    break
            except SocketClosed:
                self.onclose(None, '')
                break
            except Exception as e:
                self.onexception(e)

    def send_close(self, code, reason):
        """
        Send a CLOSE control frame.
        """
        payload = '' if code is None else struct.pack('!H', code) + reason
        self.sock.send(ControlFrame(OPCODE_CLOSE, payload))
        self.close_frame_sent = True

    def send_ping(self, payload=''):
        """
        Send a PING control frame with an optional payload.
        """
        self.sock.send(ControlFrame(OPCODE_PING, payload))
        self.ping_payload = payload
        self.ping_sent = True
        self.onping(payload)

    def handle_close(self, code=None, reason=''):
        """
        Handle a close message by sending a response close message if no CLOSE
        frame was sent before, and closing the connection. The onclose()
        handler is called afterwards.
        """
        if not self.close_frame_sent:
            payload = '' if code is None else struct.pack('!H', code)
            self.sock.send(ControlFrame(OPCODE_CLOSE, payload))

        self.sock.close()
        self.onclose(code, reason)

    def close(self, code=None, reason=''):
        """
        Close the socket by sending a CLOSE frame and waiting for a response
        close message. The onclose() handler is called after the CLOSE frame
        has been sent, but before the response has been received.
        """
        self.send_close(code, reason)
        # FIXME: swap the two lines below?
        self.onclose(code, reason)
        frame = self.sock.recv()
        self.sock.close()

        if frame.opcode != OPCODE_CLOSE:
            raise ValueError('expected CLOSE frame, got %s instead' % frame)

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

    def onexception(self, e):
        """
        Handle a raised exception.
        """
        return NotImplemented
