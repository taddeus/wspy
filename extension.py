from errors import HandshakeError


class Extension(object):
    rsv1 = False
    rsv2 = False
    rsv3 = False
    opcodes = []
    parameters = []

    def __init__(self, **kwargs):
        for param in self.parameters:
            setattr(self, param, None)

        for param, value in kwargs.items():
            if param not in self.parameters:
                raise HandshakeError('invalid parameter "%s"' % param)

            if value is None:
                value = True

            setattr(self, param, value)

    def client_params(self, frame):
        return {}

    def hook_send(self, frame):
        return frame

    def hook_receive(self, frame):
        return frame


class DeflateFrame(Extension):
    name = 'deflate-frame'
    rsv1 = True
    parameters = ['max_window_bits', 'no_context_takeover']

    def __init__(self, **kwargs):
        super(DeflateFrame, self).__init__(**kwargs)
        self.max_window_bits = int(self.max_window_bits)

    def hook_send(self, frame):
        # FIXME: original `frame` is modified, maybe it should be copied?

        if not frame.rsv1:
            frame.rsv1 = True
            frame.payload = self.encode(frame.payload)

        return frame

    def hook_recv(self, frame):
        # FIXME: original `frame` is modified, maybe it should be copied?

        if frame.rsv1:
            frame.rsv1 = False
            frame.payload = self.decode(frame.payload)

        return frame

    def client_params(self):
        raise NotImplementedError  # TODO

    def encode(self, data):
        raise NotImplementedError  # TODO

    def decode(self, data):
        raise NotImplementedError  # TODO


def filter_extensions(extensions):
    """
    Remove extensions that use conflicting rsv bits and/or opcodes, with the
    first options being most preferable.
    """
    rsv1_reserved = True
    rsv2_reserved = True
    rsv3_reserved = True
    opcodes_reserved = []
    compat = []

    for ext in extensions:
        if ext.rsv1 and rsv1_reserved \
                or ext.rsv2 and rsv2_reserved \
                or ext.rsv3 and rsv3_reserved \
                or len(set(ext.opcodes) & set(opcodes_reserved)):
            continue

        rsv1_reserved |= ext.rsv1
        rsv2_reserved |= ext.rsv2
        rsv3_reserved |= ext.rsv3
        opcodes_reserved.extend(ext.opcodes)
        compat.append(ext)

    return compat
