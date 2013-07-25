class SocketClosed(Exception):
    def __init__(self, code=None, reason=''):
        self.code = code
        self.reason = reason

    @property
    def message(self):
        return ('' if self.code is None else '[%d] ' % self.code) + self.reason


class HandshakeError(Exception):
    pass


class PingError(Exception):
    pass
