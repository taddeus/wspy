from extension import Extension


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
