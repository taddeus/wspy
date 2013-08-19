About
=====

*twspy* is a standalone implementation of web sockets for Python, defined by
[RFC 6455](http://tools.ietf.org/html/rfc6455). The incentive for creating this
library is the absence of a layered implementation of web sockets outside the
scope of web servers such as Apache or Nginx. *twspy* does not require any
third-party programs or libraries outside Python's standard library. It
provides low-level access to sockets, as well as high-level functionalities to
easily set up a web server. Thus, it is both suited for quick server
programming, as well as for more demanding applications that require low-level
control over each frame being sent/received.

Her is a quick overview of the features in this library:
- Upgrading regular sockets to web sockets.
- Building custom frames.
- Messages, which are higher-level than frames (see "Basic usage").
- Connections, which hide the handling of control frames and automatically
  concatenate fragmented messages to individual payloads.
- HTTP authentication during handshake.
- An extendible server implementation.
- Secure sockets using SSL certificates (for 'wss://...' URL's).
- The possibility to add extensions to the web socket protocol. An included
  implementation is [deflate-frame](http://tools.ietf.org/html/draft-tyoshino-hybi-websocket-perframe-deflate-06).


Basic usage
===========

- The `websocket` class upgrades a regular socket to a web socket. A
  `websocket` instance is a single end point of a connection. A `websocket`
  instance sends and receives frames (`Frame` instances) as opposed to bytes
  (which are sent/received in a regular socket).

  Server example:

        import twspy, socket
        sock = twspy.websocket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 8000))
        sock.listen()

        client = sock.accept()
        client.send(twspy.Frame(twspy.OPCODE_TEXT, 'Hello, Client!'))
        frame = client.recv()

  Client example:

        import twspy
        sock = twspy.websocket(location='/my/path')
        sock.connect(('', 8000))
        sock.send(twspy.Frame(twspy.OPCODE_TEXT, 'Hello, Server!'))

- A `Connection` instance represents a connection between two end points, based
  on a `websocket` instance. A connection handles control frames properly, and
  sends/receives messages (`Message` instances, which are higher-level than
  frames). Messages are automatically converted to frames, and received frames
  are converted to messages. Fragmented messages (messages consisting of
  multiple frames) are also supported.

  Example of an echo server (sends back what it receives):

        import twspy

        class EchoConnection(twspy.Connection):
            def onopen(self):
                print 'Connection opened at %s:%d' % self.sock.getpeername()

            def onmessage(self, message):
                print 'Received message "%s"' % message.payload
                self.send(twspy.TextMessage(message.payload))

            def onclose(self, message):
                print 'Connection closed'

        server = twspy.websocket()
        server.bind(('', 8000))
        server.listen()

        while True:
            client, addr = server.accept()
            EchoConnection(client).receive_forever()

  There are two types of messages: `TextMessage`s and `BinaryMessage`s. A
  `TextMessage` uses frames with opcode `OPCODE_TEXT`, and encodes its payload
  using UTF-8 encoding. A `BinaryMessage` just sends its payload as raw data.
  I recommend using `TextMessage` by default, and `BinaryMessage` only when
  necessary.

  **Note:** For browser clients, you will probably want to use JSON encoding.
  This could, for example, be implemented as follows:

        import twspy, json

        def msg(**data):
            return twspy.TextMessage(json.dumps(data))

        # create some connection `conn`...

        conn.send(msg(foo='Hello, World!'))


- The built-in `Server` implementation is very basic. It starts a new thread
  with a `Connection.receive_forever()` loop for each client that connects. It
  also handles client crashes properly. By default, a `Server` instance only
  logs every event using Python's `logging` module. To create a custom server,
  The `Server` class should be extended and its event handlers overwritten. The
  event handlers are named identically to the `Connection` event handlers, but
  they also receive an additional `client` argument. This argument is a
  modified `Connection` instance, so you can invoke `send()` and `recv()`.

  For example, the `EchoConnection` example above can be rewritten to:

        import twspy

        class EchoServer(twspy.Server):
            def onopen(self, client):
                print 'Client %s connected' % client

            def onmessage(self, client, message):
                print 'Received message "%s"' % message.payload
                client.send(twspy.TextMessage(message.payload))

            def onclose(self, client):
                print 'Client %s disconnected' % client

        EchoServer(('', 8000)).run()

  The server can be stopped by typing CTRL-C in the command line. The
  `KeyboardInterrupt` raised when this happens is caught by the server.


Extensions
==========

TODO
