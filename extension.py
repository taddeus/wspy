class Extension(object):
    name = ''
    rsv1 = False
    rsv2 = False
    rsv3 = False
    opcodes = []
    defaults = {}
    request = {}

    def __init__(self, defaults={}, request={}):
        for param in defaults.keys() + request.keys():
            if param not in self.defaults:
                raise KeyError('unrecognized parameter "%s"' % param)

        # Copy dict first to avoid duplicate references to the same object
        self.defaults = dict(self.__class__.defaults)
        self.defaults.update(defaults)

        self.request = dict(self.__class__.request)
        self.request.update(request)

    def __str__(self, frame):
        return '<Extension "%s" defaults=%s request=%s>' \
               % (self.name, self.defaults, self.request)

    def create_hook(self, **kwargs):
        params = {}
        params.update(self.defaults)
        params.update(kwargs)
        return self.Hook(**params)

    class Hook:
        def __init__(self, **kwargs):
            for param, value in kwargs.iteritems():
                setattr(self, param, value)

        def send(self, frame):
            return frame

        def recv(self, frame):
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
    # FIXME: is 32768 (below) correct?
    defaults = {'max_window_bits': 32768, 'no_context_takeover': True}

    def __init__(self, defaults={}, request={}):
        Extension.__init__(self, defaults, request)

        mwb = self.defaults['max_window_bits']
        cto = self.defaults['no_context_takeover']

        if not isinstance(mwb, int):
            raise ValueError('"max_window_bits" must be an integer')
        elif mwb > 32768:
            raise ValueError('"max_window_bits" may not be larger than 32768')

        if cto is not False and cto is not True:
            raise ValueError('"no_context_takeover" must have no value')

    class Hook(Extension.Hook):
        def send(self, frame):
            if not frame.rsv1:
                frame.rsv1 = True
                frame.payload = self.deflate(frame.payload)

            return frame

        def recv(self, frame):
            if frame.rsv1:
                frame.rsv1 = False
                frame.payload = self.inflate(frame.payload)

            return frame

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
    defaults = {'quota': None}

    def __init__(self, defaults={}, request={}):
        Extension.__init__(self, defaults, request)

        # TODO: check "quota" value

    class Hook(Extension.Hook):
        def send(self, frame):
            raise NotImplementedError  # TODO

        def recv(self, frame):
            raise NotImplementedError  # TODO


def filter_extensions(extensions):
    """
    Remove extensions that use conflicting rsv bits and/or opcodes, with the
    first options being the most preferable.
    """
    rsv1_reserved = False
    rsv2_reserved = False
    rsv3_reserved = False
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
