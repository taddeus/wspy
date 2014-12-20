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

        self.init()

    def __str__(self):
        return '<Extension "%s" defaults=%s request=%s>' \
               % (self.name, self.defaults, self.request)

    def init(self):
        return NotImplemented

    def create_hook(self, **kwargs):
        params = {}
        params.update(self.defaults)
        params.update(kwargs)
        hook = self.Hook(**params)
        hook.init(self)
        return hook

    class Hook:
        def __init__(self, **kwargs):
            for param, value in kwargs.iteritems():
                setattr(self, param, value)

        def init(self, extension):
            return NotImplemented

        def send(self, frame):
            return frame

        def recv(self, frame):
            return frame


def extension_conflicts(ext, existing):
    rsv1_reserved = False
    rsv2_reserved = False
    rsv3_reserved = False
    reserved_opcodes = []

    for e in existing:
        rsv1_reserved |= e.rsv1
        rsv2_reserved |= e.rsv2
        rsv3_reserved |= e.rsv3
        reserved_opcodes.extend(e.opcodes)

    return ext.rsv1 and rsv1_reserved \
            or ext.rsv2 and rsv2_reserved \
            or ext.rsv3 and rsv3_reserved \
            or len(set(ext.opcodes) & set(reserved_opcodes))
