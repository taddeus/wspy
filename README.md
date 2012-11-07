**twspy** is a standalone implementation of web sockets for Python, defined by
[RFC 6455](http://tools.ietf.org/html/rfc6455).

- The `websocket` class upgrades a regular socket to a web socket. A websocket
  instance is a single end point of a connection. A `websocket` instance sends
  and receives frames (`Frame` instances) as opposed to bytes (which are
  sent/received in a regular socket).

- A `Connection` instance represents a connection between two end points, based
  on a `websocket` instance. A connection handles control frames properly, and
  sends/receives messages (`Message` instances, which are higher-level than
  frames). Messages are automatically converted to frames, and received frames
  are converted to messages. Fragmented messages (messages consisting of
  multiple frames) are also supported.
