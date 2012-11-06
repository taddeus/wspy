*twspy* is a standalone implementation of web sockets for Python.

- The websocket.WebSocket class upgrades a regular socket to a web socket.
- message.py contains classes that abstract messages sent over the socket.
  Sent messages are automatically converted to frames, and received frames are
  converted to messages. Fragmented messages are also supported.
- The server.Server class can be used to support multiple clients to open a
  web socket simultaneously in different threads, which is often desirable in
  web-based applications.
