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
    def __init__(self, opcode, payload, masking_key='', final=True, rsv1=False,
            rsv2=False, rsv3=False):
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

        if self.masking_key:
            return header + self.masking_key + self.mask_payload()

        return header + self.payload

    def mask_payload(self):
        return mask(self.masking_key, self.payload)

    def fragment(self, fragment_size, mask=False):
        frames = []

        for start in range(0, len(self.payload), fragment_size):
            payload = self.payload[start:start + fragment_size]
            key = urandom(4) if mask else ''
            frames.append(Frame(OPCODE_CONTINUATION, payload, key, False))

        frames[0].opcode = self.opcode
        frames[-1].final = True

        return frames

    def __str__(self):
        return '<Frame opcode=%c len=%d>' % (self.opcode, len(self.payload))


class FrameReceiver(object):
    def __init__(self, sock):
        self.sock = sock

    def assert_received(self, n, exact=False):
        if self.nreceived < n:
            recv = recv_exactly if exact else recv_at_least
            received = recv(self.sock, n - self.nreceived)

            if not len(received):
                raise SocketClosed()

            self.buf += received
            self.nreceived = len(self.buf)

    def receive_fragments(self):
        fragments = [self.receive_frame()]

        while not fragments[-1].final:
            fragments.append(self.receive_frame())

        return fragments

    def receive_frame(self):
        self.buf = ''
        self.nreceived = 0
        total_len = 2

        self.assert_received(2)
        b1, b2 = struct.unpack('!BB', self.buf[:2])
        final = bool(b1 & 0x80)
        rsv1 = bool(b1 & 0x40)
        rsv2 = bool(b1 & 0x20)
        rsv3 = bool(b1 & 0x10)
        opcode = b1 & 0x0F
        mask = bool(b2 & 0x80)
        payload_len = b2 & 0x7F

        if mask:
            total_len += 4

        if payload_len == 126:
            self.assert_received(4)
            total_len += 4 + struct.unpack('!H', self.buf[2:4])
            key_start = 4
        elif payload_len == 127:
            self.assert_received(8)
            total_len += 8 + struct.unpack('!Q', self.buf[2:10])
            key_start = 10
        else:
            total_len += payload_len
            key_start = 2

        self.assert_received(total_len, exact=True)

        if mask:
            payload_start = key_start + 4
            masking_key = self.buf[key_start:payload_start]
            payload = mask(masking_key, self.buf[payload_start:])
        else:
            masking_key = ''
            payload = self.buf[key_start:]

        return Frame(opcode, payload, masking_key=masking_key, final=final,
                      rsv1=rsv1, rsv2=rsv2, rsv3=rsv3)


def recv_exactly(sock, n):
    """
    Keep receiving data from `sock' until exactly `n' bytes have been read.
    """
    left = n
    data = ''

    while left > 0:
        received = sock.recv(left)
        data += received
        left -= len(received)

    return received


def recv_at_least(sock, n, at_least):
    """
    Keep receiving data from `sock' until at least `n' bytes have been read.
    """
    left = at_least
    data = ''

    while left > 0:
        received = sock.recv(n)
        data += received
        left -= len(received)

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


def concat_frames(frames):
    """
    Create a new Frame object with the concatenated payload of the given list
    of frames.
    """
    assert len(frames)
    first = frames[0]
    assert first.opcode != 0
    assert frames[-1].final
    return Frame(first.opcode, ''.join([f.payload for f in frames]),
                 rsv1=first.rsv1, rsv2=first.rsv2, rsv3=first.rsv3)
