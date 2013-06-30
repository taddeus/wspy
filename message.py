import json

from frame import Frame, OPCODE_TEXT, OPCODE_BINARY


__all__ = ['Message', 'TextMessage', 'BinaryMessage', 'JSONMessage']


class Message(object):
    def __init__(self, opcode, payload):
        self.opcode = opcode
        self.payload = payload

    def frame(self, mask=False):
        return Frame(self.opcode, self.payload, mask=mask)

    def fragment(self, fragment_size, mask=False):
        return self.frame().fragment(fragment_size, mask)

    def __str__(self):
        return '<%s opcode=0x%X size=%d>' \
               % (self.__class__.__name__, self.opcode, len(self.payload))


class TextMessage(Message):
    def __init__(self, payload):
        super(TextMessage, self).__init__(OPCODE_TEXT, payload.encode('utf-8'))


class BinaryMessage(Message):
    def __init__(self, payload):
        super(BinaryMessage, self).__init__(OPCODE_BINARY, payload)


class JSONMessage(TextMessage):
    def __init__(self, dictionary, **kwargs):
        self.data = {}
        self.data.extend(dictionary)
        self.data.extend(kwargs)
        super(JSONMessage, self).__init__(json.dumps(self.data))


OPCODE_CLASS_MAP = {
    OPCODE_TEXT: TextMessage,
    OPCODE_BINARY: BinaryMessage,
}


def create_message(opcode, payload):
    if opcode in OPCODE_CLASS_MAP:
        return OPCODE_CLASS_MAP[opcode](payload)

    return Message(opcode, payload)
