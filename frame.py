import struct
from os import urandom

from exceptions import SocketClosed


OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA


class Frame(object):
    """
    A Frame instance represents a web socket data frame as defined in RFC 6455.
    To encoding a frame for sending it over a socket, use Frame.pack(). To
    receive and decode a frame from a socket, use receive_frame() (or,
    preferably, receive_fragments()).
    """
    def __init__(self, opcode, payload, masking_key='', final=True, rsv1=False,
            rsv2=False, rsv3=False):
        """
        Create a new frame.

        `opcode' is one of the constants as defined above.

        `payload' is a string of bytes containing the data sendt in the frame.

        `final` is a boolean indicating whether this frame is the last in a
        chain of fragments.

        `rsv1', `rsv2' and `rsv3' are booleans indicating bit values for RSV1,
        RVS2 and RSV3, which are only non-zero if defined so by extensions.
        """
        if len(masking_key)  not in (0, 4):
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
        header = struct.pack('!B', (self.fin << 7) | (self.rsv1 << 6) |
                             (self.rsv2 << 5) | (self.rsv3 << 4) | self.opcode)

        mask = bool(self.masking_key) << 7
        payload_len = len(self.payload)

        if payload_len <= 125:
            header += struct.pack('!B', mask | payload_len)
        elif payload_len < (1 << 16):
            header += struct.pack('!BH', mask | 126, payload_len)
        elif payload_len < (1 << 63):
            header += struct.pack('!BQ', mask | 127, payload_len)
        else:
            raise Exception('the payload length is too damn high!')

        if mask:
            return header + self.masking_key + self.mask_payload()

        return header + self.payload

    def mask_payload(self):
        return mask(self.masking_key, self.payload)

    def fragment(self, fragment_size, mask=False):
        """
        Fragment the frame into a chain of fragment frames, as explained in the
        docs of the function receive_fragments().

        `fragment_size' indicates the maximum payload size of each fragment.
        The payload of the original frame is split into one or more parts, and
        each part is converted to a Frame instance.

        `mask' is a boolean (default False) indicating whether the payloads
        should be masked. If True, each frame is assigned a randomly generated
        masking key.
        """
        frames = []

        for start in range(0, len(self.payload), fragment_size):
            payload = self.payload[start:start + fragment_size]
            key = urandom(4) if mask else ''
            frames.append(Frame(OPCODE_CONTINUATION, payload, key, False))

        frames[0].opcode = self.opcode
        frames[-1].final = True

        return frames

    def __str__(self):
        return '<Frame opcode=0x%X len=%d>' % (self.opcode, len(self.payload))


def receive_fragments(sock):
    """
    Receive a sequence of frames that belong together:
    - An initial frame with non-zero opcode
    - Zero or more frames with opcode = 0 and final = False
    - A final frame with opcode = 0 and final = True

    The first and last frame may be the same frame, having a non-zero opcode
    and final = True. Thus, this function returns a list of at least a single
    frame.
    """
    fragments = [receive_frame(sock)]

    while not fragments[-1].final:
        fragments.append(receive_frame(sock))

    return fragments


def receive_frame(sock):
    """
    Receive a single frame on socket `sock'.
    """
    b1, b2 = struct.unpack('!BB', recvn(sock, 2))

    final = bool(b1 & 0x80)
    rsv1 = bool(b1 & 0x40)
    rsv2 = bool(b1 & 0x20)
    rsv3 = bool(b1 & 0x10)
    opcode = b1 & 0x0F

    mask = bool(b2 & 0x80)
    payload_len = b2 & 0x7F

    if payload_len == 126:
        payload_len = struct.unpack('!H', recvn(sock, 2))
    elif payload_len == 127:
        payload_len = struct.unpack('!Q', recvn(sock, 8))

    if mask:
        masking_key = recvn(sock, 4)
        payload = mask(masking_key, recvn(sock, payload_len))
    else:
        masking_key = ''
        payload = recvn(sock, payload_len)

    return Frame(opcode, payload, masking_key=masking_key, final=final,
                 rsv1=rsv1, rsv2=rsv2, rsv3=rsv3)


def recvn(sock, n):
    """
    Keep receiving data from `sock' until exactly `n' bytes have been read.
    """
    data = ''

    while len(data) < n:
        received = sock.recv(n - len(data))

        if not len(received):
            raise SocketClosed()

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
