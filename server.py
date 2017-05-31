#
# Byne challenge server
#

import zmq

# Version of communication protocol
PROTOCOL_VERSION = "1"

# Server acknowledge message
ACK = "\x64"

# Client message types
MSG_VERSION = 0     # Request of protocol version
MSG_CLIENT_ID = 1   # Provision of client identification
MSG_GET_EVEN = 2    # Request of an even number
MSG_GET_ODD = 3     # Request of an odd number
MSG_VALUE = 4       # Provision of a value

def make_even_number():
    """Produce an even pseudo random number from 0 to 99."""
    return random.randrange(0, 100, 2)

def make_odd_number():
    """Produce an odd pseudo random number from 0 to 99."""
    return random.randrange(1, 100, 2)

class Server:
    """Byne challenge server."""

    def start(self, endpoint):
        """Binds to a 0MQ endpoint and start serving."""

        # FIXME: LOG ALL MESSAGES!!

        # Bind to 0MQ socket
        ctx = zmq.Context.instance()
        socket = ctx.socket(zmq.REP)
        socket.bind(endpoint)

        # Serve
        while True:

            # Wait for a client
            msg = socket.recv()

            # Parse message
            msg_type = MSG_VERSION
            if len(msg) != 0:
                msg_type = msg[0]
            if msg_type == MSG_VERSION:

                # A client is requesting for this protocol version
                socket.send(protocol_version)

            elif msg_type == MSG_CLIENT_ID:

                # Client is identifying itself
                client_id = msg[1:]
                # FIXME: lookup client current value to return
                socket.send("\x00")

            elif msg_type == MSG_GET_EVEN:

                # Client requests an even number
                client_id = msg[1:]
                # FIXME: update client current value in map
                socket.send(make_even_number())

            elif msg_type == MSG_GET_ODD:

                # Client requests an odd number
                client_id = msg[1:]
                # FIXME: update client current value in map
                socket.send(make_odd_number())

            elif msg_type == MSG_VALUE:

                # Client sends a value
                value = msg[1]
                client_id = msg[1:]
                socket.send(ACK)

            else:

                # Unknown message type
                socket.send(ACK)

# Start server
Server().start("tcp://*:5555")

