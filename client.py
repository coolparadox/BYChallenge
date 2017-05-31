#
# Byne challenge client
#

import time
import zmq

# FIXME: hardcoded client identification
CLIENT_ID = "\x00\x01"

# Current value to be worked on
current_value = 0

class Client:
    """Byne challenge client."""

    def start(self, endpoint):
        """Connect to a Byne challenge server at a 0MQ endpoint"""

        global current_value

        # FIXME: error handling
        # FIXME: logging

        # Connect to server
        ctx = zmq.Context()
        socket = ctx.socket(zmq.REQ)
        socket.connect(endpoint)

        # FIXME: check protocol version

        # Send identification
        # FIXME: share message type constants with server code
        socket.send("\x01" + CLIENT_ID)

        # Receive value
        msg = socket.recv()
        current_value = ord(msg[0])

        # Value incrementation infinite loop
        while True:

            # FIXME: this loop takes longer than 500ms to be executed. Setup an alarm?
            time.sleep(0.5)
            #time.sleep(random.uniform(3, 5))
            # FIXME: incrementation amount
            current_value = current_value + 1
            if current_value > 99:
                current_value = 0
            socket.send(''.join([chr(4), chr(current_value)]))
            msg = socket.recv()

# Start client
Client().start("tcp://localhost:5555")

