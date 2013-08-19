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
                raise HandshakeError('unrecognized parameter "%s"' % param)

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
    """
    This is an implementation of the "deflate-frame" extension, as defined by
    http://tools.ietf.org/html/draft-tyoshino-hybi-websocket-perframe-deflate-06.

    Supported parameters are:
    - max_window_size: maximum size for the LZ77 sliding window.
    - no_context_takeover: disallows usage of LZ77 sliding window from
                           previously built frames for the current frame.

    Note that the deflate and inflate hooks modify the RSV1 bit and payload of
    existing `Frame` objects.
    """

    name = 'deflate-frame'
    rsv1 = True
    parameters = ['max_window_bits', 'no_context_takeover']

    # FIXME: is this correct?
    default_max_window_bits = 32768

    def __init__(self, **kwargs):
        super(DeflateFrame, self).__init__(**kwargs)

        if self.max_window_bits is None:
            self.max_window_bits = self.default_max_window_bits
        elif not isinstance(self.max_window_bits, int):
            raise HandshakeError('"max_window_bits" must be an integer')
        elif self.max_window_bits > 32768:
            raise HandshakeError('"max_window_bits" may not be larger than '
                                 '32768')

        if self.no_context_takeover is None:
            self.no_context_takeover = False
        elif self.no_context_takeover is not True:
            raise HandshakeError('"no_context_takeover" must have no value')

    def hook_send(self, frame):
        if not frame.rsv1:
            frame.rsv1 = True
            frame.payload = self.deflate(frame.payload)

        return frame

    def hook_recv(self, frame):
        if frame.rsv1:
            frame.rsv1 = False
            frame.payload = self.inflate(frame.payload)

        return frame

    def header_params(self):
        raise NotImplementedError  # TODO

    def deflate(self, data):
        raise NotImplementedError  # TODO

    def inflate(self, data):
        raise NotImplementedError  # TODO


class Multiplex(Extension):
    """
    This is an implementation of the "mux" extension, as defined by
    http://tools.ietf.org/html/draft-ietf-hybi-websocket-multiplexing-11.

    Supported parameters are:
    - quota: TODO
    """

    name = 'mux'
    rsv1 = True  # FIXME
    rsv2 = True  # FIXME
    rsv3 = True  # FIXME
    parameters = ['quota']

    def __init__(self, **kwargs):
        super(Multiplex, self).__init__(**kwargs)

        # TODO: check "quota" value

    def hook_send(self, frame):
        raise NotImplementedError  # TODO

    def hook_recv(self, frame):
        raise NotImplementedError  # TODO

    def header_params(self):
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
