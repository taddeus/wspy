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

    def __str__(self):
        return '<Extension "%s" defaults=%s request=%s>' \
               % (self.name, self.defaults, self.request)

    def create_hook(self, **kwargs):
        params = {}
        params.update(self.defaults)
        params.update(kwargs)
        return self.Hook(self, **params)

    class Hook:
        def __init__(self, extension, **kwargs):
            self.extension = extension

            for param, value in kwargs.iteritems():
                setattr(self, param, value)

        def send(self, frame):
            return frame

        def recv(self, frame):
            return frame


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
