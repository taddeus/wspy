from frame import Frame, OPCODE_TEXT, OPCODE_BINARY, OPCODE_CLOSE, \
        OPCODE_PING, OPCODE_PONG


__all__ = ['Message', 'TextMessage', 'BinaryMessage', 'CloseMessage',
           'PingMessage', 'PongMessage']


class Message(object):
    def __init__(self, opcode, payload):
        self.opcode = opcode
        self.payload = payload

    def frame(self):
        return Frame(self.opcode, self.payload)

    def fragment(self, fragment_size, mask=False):
        return self.frame().fragment(fragment_size, mask)

    def __str__(self):
        return '<%s opcode=%x size=%d>' \
               % (self.__class__.__name__, self.opcode, len(self.payload))


class TextMessage(Message):
    def __init__(self, payload):
        super(TextMessage, self).__init__(OPCODE_TEXT, payload)


class BinaryMessage(Message):
    def __init__(self, payload):
        super(TextMessage, self).__init__(OPCODE_BINARY, payload)


class CloseMessage(Message):
    def __init__(self, payload):
        super(TextMessage, self).__init__(OPCODE_CLOSE, payload)


class PingMessage(Message):
    def __init__(self, payload):
        super(TextMessage, self).__init__(OPCODE_PING, payload)


class PongMessage(Message):
    def __init__(self, payload):
        super(TextMessage, self).__init__(OPCODE_PONG, payload)


OPCODE_CLASS_MAP = {
    OPCODE_TEXT: TextMessage,
    OPCODE_BINARY: BinaryMessage,
    OPCODE_CLOSE: CloseMessage,
    OPCODE_PING: PingMessage,
    OPCODE_PONG: PongMessage,
}


def create_message(opcode, payload):
    if opcode in OPCODE_CLASS_MAP:
        return OPCODE_CLASS_MAP(payload)

    return Message(opcode, payload)
