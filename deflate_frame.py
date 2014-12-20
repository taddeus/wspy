import zlib

from extension import Extension
from frame import ControlFrame


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
    defaults = {'max_window_bits': zlib.MAX_WBITS, 'no_context_takeover': False}

    COMPRESSION_THRESHOLD = 64  # minimal payload size for compression

    def init(self):
        mwb = self.defaults['max_window_bits']
        cto = self.defaults['no_context_takeover']

        if not isinstance(mwb, int) or mwb < 1 or mwb > zlib.MAX_WBITS:
            raise ValueError('"max_window_bits" must be in range 1-15')

        if cto is not False and cto is not True:
            raise ValueError('"no_context_takeover" must have no value')

    class Hook(Extension.Hook):
        def init(self, extension):
            self.defl = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION,
                                         zlib.DEFLATED, -self.max_window_bits)
            other_wbits = extension.request.get('max_window_bits', zlib.MAX_WBITS)
            self.dec = zlib.decompressobj(-other_wbits)

        def send(self, frame):
            # FIXME: this does not seem to work properly on Android
            if not frame.rsv1 and not isinstance(frame, ControlFrame) and \
                   len(frame.payload) > DeflateFrame.COMPRESSION_THRESHOLD:
                frame.rsv1 = True
                frame.payload = self.deflate(frame)

            return frame

        def recv(self, frame):
            if frame.rsv1:
                if isinstance(frame, ControlFrame):
                    raise ValueError('received compressed control frame')

                frame.rsv1 = False
                frame.payload = self.inflate(frame.payload)

            return frame

        def deflate(self, frame):
            compressed = self.defl.compress(frame.payload)

            if frame.final or self.no_context_takeover:
                compressed += self.defl.flush(zlib.Z_FINISH) + '\x00'
                self.defl = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION,
                        zlib.DEFLATED, -self.max_window_bits)
            else:
                compressed += self.defl.flush(zlib.Z_SYNC_FLUSH)
                assert compressed[-4:] == '\x00\x00\xff\xff'
                compressed = compressed[:-4]

            return compressed

        def inflate(self, data):
            return self.dec.decompress(data + '\x00\x00\xff\xff') + \
                   self.dec.flush(zlib.Z_SYNC_FLUSH)


class WebkitDeflateFrame(DeflateFrame):
    name = 'x-webkit-deflate-frame'
