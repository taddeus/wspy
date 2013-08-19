from errors import HandshakeError


class Extension(object):
    name = ''
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

    def __str__(self, frame):
        if len(self.parameters):
            params = ' ' + ', '.join(p + '=' + str(getattr(self, p))
                                     for p in self.parameters)
        else:
            params = ''

        return '<Extension "%s"%s>' % (self.name, params)

    def header_params(self, frame):
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

        if self.max_window_bits is None:
            # FIXME: is this correct? None may actually be a better value
            self.max_window_bits = 0

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

    def header_params(self):
        raise NotImplementedError  # TODO

    def encode(self, data):
        raise NotImplementedError  # TODO

    def decode(self, data):
        raise NotImplementedError  # TODO


def filter_extensions(extensions):
    """
    Remove extensions that use conflicting rsv bits and/or opcodes, with the
    first options being the most preferable.
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
