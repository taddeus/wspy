import struct
from os import urandom
from string import printable

from errors import SocketClosed


OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA

CLOSE_NORMAL = 1000
CLOSE_GOING_AWAY = 1001
CLOSE_PROTOCOL_ERROR = 1002
CLOSE_NOACCEPT_DTYPE = 1003
CLOSE_INVALID_DATA = 1007
CLOSE_POLICY = 1008
CLOSE_MESSAGE_TOOBIG = 1009
CLOSE_MISSING_EXTENSIONS = 1010
CLOSE_UNABLE = 1011


def printstr(s):
    return ''.join(c if c in printable else '.' for c in s)


class Frame(object):
    """
    A Frame instance represents a web socket data frame as defined in RFC 6455.
    To encoding a frame for sending it over a socket, use Frame.pack(). To
    receive and decode a frame from a socket, use receive_frame().
    """
    def __init__(self, opcode, payload, masking_key='', mask=False, final=True,
            rsv1=False, rsv2=False, rsv3=False):
        """
        Create a new frame.

        `opcode` is one of the constants as defined above.

        `payload` is a string of bytes containing the data sendt in the frame.

        `masking_key` is an optional custom key to use for masking, or `mask`
        can be used instead to let this constructor generate a random masking
        key.

        `final` is a boolean indicating whether this frame is the last in a
        chain of fragments.

        `rsv1`, `rsv2` and `rsv3` are booleans indicating bit values for RSV1,
        RVS2 and RSV3, which are only non-zero if defined so by extensions.
        """
        if mask:
            masking_key = urandom(4)

        if len(masking_key) not in (0, 4):
            raise ValueError('invalid masking key "%s"' % masking_key)

        self.final = final
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3
        self.opcode = opcode
        self.masking_key = masking_key
        self.payload = payload

    def pack(self):
        """
        Pack the frame into a string according to the following scheme:

        +-+-+-+-+-------+-+-------------+-------------------------------+
        |F|R|R|R| opcode|M| Payload len |    Extended payload length    |
        |I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
        |N|V|V|V|       |S|             |   (if payload len==126/127)   |
        | |1|2|3|       |K|             |                               |
        +-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
        |     Extended payload length continued, if payload len == 127  |
        + - - - - - - - - - - - - - - - +-------------------------------+
        |                               |Masking-key, if MASK set to 1  |
        +-------------------------------+-------------------------------+
        | Masking-key (continued)       |          Payload Data         |
        +-------------------------------- - - - - - - - - - - - - - - - +
        :                     Payload Data continued ...                :
        + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
        |                     Payload Data continued ...                |
        +---------------------------------------------------------------+
        """
        header = struct.pack('!B', (self.final << 7) | (self.rsv1 << 6)
                                   | (self.rsv2 << 5) | (self.rsv3 << 4)
                                   | (self.opcode & 0xf))
        mask = bool(self.masking_key) << 7
        payload_len = len(self.payload)

        if payload_len <= 125:
            header += struct.pack('!B', mask | payload_len)
        elif payload_len < (1 << 16):
            header += struct.pack('!BH', mask | 126, payload_len)
        elif payload_len < (1 << 63):
            header += struct.pack('!BQ', mask | 127, payload_len)
        else:
            # FIXME: RFC 6455 defines an action for this...
            raise Exception('the payload length is too damn high!')

        if mask:
            return header + self.masking_key + self.mask_payload()

        return header + self.payload

    def mask_payload(self):
        return mask(self.masking_key, self.payload)

    def fragment(self, fragment_size, mask=False):
        """
        Fragment the frame into a chain of fragment frames:
        - An initial frame with non-zero opcode
        - Zero or more frames with opcode = 0 and final = False
        - A final frame with opcode = 0 and final = True

        The first and last frame may be the same frame, having a non-zero
        opcode and final = True. Thus, this function returns a list containing
        at least a single frame.

        `fragment_size` indicates the maximum payload size of each fragment.
        The payload of the original frame is split into one or more parts, and
        each part is converted to a Frame instance.

        `mask` is a boolean (default False) indicating whether the payloads
        should be masked. If True, each frame is assigned a randomly generated
        masking key.
        """
        frames = []

        for start in xrange(0, len(self.payload), fragment_size):
            payload = self.payload[start:start + fragment_size]
            frames.append(Frame(OPCODE_CONTINUATION, payload, mask=mask,
                                final=False))

        frames[0].opcode = self.opcode
        frames[-1].final = True

        return frames

    def __str__(self):
        s = '<%s opcode=0x%X len=%d' \
            % (self.__class__.__name__, self.opcode, len(self.payload))

        if self.masking_key:
            s += ' masking_key=%4s' % printstr(self.masking_key)

        max_pl_disp = 30
        pl = self.payload[:max_pl_disp]

        if len(self.payload) > max_pl_disp:
             pl += '...'

        return s + ' payload=%s>' % pl


class ControlFrame(Frame):
    """
    A control frame is a frame with an opcode OPCODE_CLOSE, OPCODE_PING or
    OPCODE_PONG. These frames must be handled as defined by RFC 6455, and
    """
    def fragment(self, fragment_size, mask=False):
        """
        Control frames must not be fragmented.
        """
        raise TypeError('control frames must not be fragmented')

    def pack(self):
        """
        Same as Frame.pack(), but asserts that the payload size does not exceed
        125 bytes.
        """
        if len(self.payload) > 125:
            raise ValueError('control frames must not be larger than 125' \
                             'bytes')

        return Frame.pack(self)

    def unpack_close(self):
        """
        Unpack a close message into a status code and a reason. If no payload
        is given, the code is None and the reason is an empty string.
        """
        if self.payload:
            code = struct.unpack('!H', str(self.payload[:2]))
            reason = str(self.payload[2:])
        else:
            code = None
            reason = ''

        return code, reason


def receive_frame(sock):
    """
    Receive a single frame on socket `sock`. The frame scheme is explained in
    the docs of Frame.pack().
    """
    b1, b2 = struct.unpack('!BB', recvn(sock, 2))

    final = bool(b1 & 0x80)
    rsv1 = bool(b1 & 0x40)
    rsv2 = bool(b1 & 0x20)
    rsv3 = bool(b1 & 0x10)
    opcode = b1 & 0x0F

    masked = bool(b2 & 0x80)
    payload_len = b2 & 0x7F

    if payload_len == 126:
        payload_len = struct.unpack('!H', recvn(sock, 2))
    elif payload_len == 127:
        payload_len = struct.unpack('!Q', recvn(sock, 8))

    if masked:
        masking_key = recvn(sock, 4)
        payload = mask(masking_key, recvn(sock, payload_len))
    else:
        masking_key = ''
        payload = recvn(sock, payload_len)

    # Control frames have most significant bit 1
    cls = ControlFrame if opcode & 0x8 else Frame

    return cls(opcode, payload, masking_key=masking_key, final=final,
               rsv1=rsv1, rsv2=rsv2, rsv3=rsv3)


def recvn(sock, n):
    """
    Keep receiving data from `sock` until exactly `n` bytes have been read.
    """
    data = ''

    while len(data) < n:
        received = sock.recv(n - len(data))

        if not len(received):
            raise SocketClosed(None, 'no data read from socket')

        data += received

    return data


def mask(key, original):
    """
    Mask an octet string using the given masking key.
    The following masking algorithm is used, as defined in RFC 6455:

    for each octet:
        j = i MOD 4
        transformed-octet-i = original-octet-i XOR masking-key-octet-j
    """
    if len(key) != 4:
        raise ValueError('invalid masking key "%s"' % key)

    key = map(ord, key)
    masked = bytearray(original)

    for i in xrange(len(masked)):
        masked[i] ^= key[i % 4]

    return masked
