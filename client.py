#
# Byne challenge client
#

import argparse
import logging
import protocol
import random
import Queue
import sys
import threading
import zmq

# Constants for access control to socket
TODO_SEND_VALUE = 0
TODO_GET_NEW_INCREMENT = 1

# Time period for incrementing value
INCREMENT_PERIOD = 0.5


class Client:
    """Byne challenge client."""

    # Identity of this client
    cid = "client"

    # Does this client request odd numbers from server?
    odd = True

    # Current value to be worked on
    working_value = 0

    # Increment amount of working_value
    increment_amount = 1

    # Access control to socket
    todo = Queue.Queue()

    # Timers should be restarted?
    restart_timers = True;

    def __init__(self, odd = True, cid = "client"):
        self.cid = cid
        self.odd = odd

    def work(self):
        """Increment working_value by increment_amount."""

        # Restart timer
        if self.restart_timers:
            threading.Timer(INCREMENT_PERIOD, self.work).start()

        # Calculate new working value.
        # Apply automatic turn in order to keep it between 0 and 99.
        new_value = self.working_value + self.increment_amount
        if new_value > 99:
            new_value = new_value - 100

        # Update work value
        self.working_value = new_value

        # Notify for sending to server
        self.todo.put(TODO_SEND_VALUE)


    def queue_get_increment(self):
        """Notify for getting a new increment value from server."""

        # Restart timer
        if self.restart_timers:
            threading.Timer(random.uniform(3.0, 5.0), self.queue_get_increment).start()

        # Notify
        self.todo.put(TODO_GET_NEW_INCREMENT)

    def send_and_recv(self, socket, request):
        """Wrapper around send() and recv()."""

        socket.send(request)
        return socket.recv()

    def start(self, endpoint):
        """Connect to a Byne challenge server at a 0MQ endpoint"""

        # Connect to server
        ctx = zmq.Context()
        socket = ctx.socket(zmq.REQ)
        socket.setsockopt(zmq.IDENTITY, self.cid)
        socket.connect(endpoint)

        # Salute server
        request = chr(protocol.CMD_HELLO)
        reply = self.send_and_recv(socket, request)
        assert len(reply) >= 3, "unexpected hello reply length (%d)" % len(reply)
        assert ord(reply[0]) == protocol.CMD_HELLO, "unexpected server reply command: expected %d, got %d" % (protocol.CMD_HELLO, ord(reply[0]))

        # Check for protocol version
        proto_ver = ord(reply[1])
        assert proto_ver == protocol.VERSION, "cannot handle protocol version %d" % proto_ver

        # Update working value with server reply
        self.working_value = ord(reply[2])
        assert 0 <= self.working_value <= 99, "out of range value from server: %d" % self.working_value

        # Start timer for incrementing value
        threading.Timer(INCREMENT_PERIOD, self.work).start()

        # Start increment update timer
        threading.Timer(random.uniform(3.0, 5.0), self.queue_get_increment).start()

        # Loop forever
        while True:

            try:

                # Wait until there is something to do
                next_action = self.todo.get()
                if next_action == TODO_SEND_VALUE:

                    # Work value has been updated
                    # Send it to server
                    request = "".join([chr(protocol.CMD_ACCEPT_VALUE), chr(self.working_value)])
                    reply = self.send_and_recv(socket, request)
                    assert len(reply) >= 1, "unexpected accept value reply length (%d)" % len(reply)
                    assert ord(reply[0]) == protocol.CMD_ACCEPT_VALUE, "unexpected server reply command: expected %d, got %d" % (protocol.CMD_ACCEPT_VALUE, ord(reply[0]))

                else:

                    # It's time to get a new increment value from server
                    command = protocol.CMD_GET_EVEN
                    if self.odd:
                        command = protocol.CMD_GET_ODD
                    request = ''.join([chr(command)])
                    reply = self.send_and_recv(socket, request)
                    assert len(reply) >= 2, "unexpected get value reply length (%d)" % len(reply)
                    assert ord(reply[0]) == command, "unexpected server reply command: expected %d, got %d" % (command, ord(reply[0]))
                    self.increment_amount = ord(reply[1])

            except KeyboardInterrupt, SystemExit:

                # Stop timers
                self.restart_timers = False
                raise


if __name__ == '__main__':

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Byne challenge client')
    parser.add_argument('client_id', nargs=1, help='client identity')
    parser.add_argument('client_type', nargs=1, help='client type', choices=['odd', 'even'])
    parser.add_argument('server_url', nargs=1, help='0MQ endpoint to connect')
    args = parser.parse_args()
    client_id = args.client_id[0]
    client_type = args.client_type[0]
    server_url = args.server_url[0]

    # Start client
    sys.stderr.write('starting client "%s" of %s type, connecting to %s\n' % (client_id, client_type, server_url))
    Client(cid=client_id, odd=(client_type=='odd')).start(server_url)

