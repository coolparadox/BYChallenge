"""
Byne challenge client module

This module implements the Byne challenge client.

Example:

    $ python2 client.py CLIENT-1 odd tcp://localhost:5555 tcp://localhost:5556 60

Online help:

    $ python2 client.py --help
    usage: client.py [-h] client_id {odd,even} primary_url backup_url timeout

    Byne challenge client

    positional arguments:
      client_id    client identity
      {odd,even}   client type
      primary_url  0MQ endpoint of primary server
      backup_url   0MQ endpoint of backup server
      timeout      primary server access timeout in seconds (0 = infinite)

    optional arguments:
      -h, --help   show this help message and exit

Client identity is used to identify client when multiple clients are connected
to the server and is assumed to be unique among the set of connected clients.

Client type defines if client will request always an odd or an even value from
the server; see Byne challenge server protocol specification.

Primary url is the 0MQ endpoint of the primary server. Client connects to this
server when starts.

Backup url is the 0MQ endpoint of the backup server. Clinet connects to this
server when the communication with the primary server times out.

Timeout is the threshold delay in the communication with the primary server to
declare that the primary server is out of reach. After this time of absence of
communication with the primary server, client switches to the backup server.

When a switch to the backup server happens, it is definitive. A manual restart
is required in order the client goes back to use the primary server.

Source code: https://github.com/coolparadox/BYChallenge

Communication protocol specification:
https://github.com/coolparadox/BYChallenge/wiki/Protocol-Specification

"""

import argparse
import logging
import protocol
import Queue
import random
import sys
import threading
import time
import zmq

# Constants for access control to socket
TODO_SEND_VALUE = 0
TODO_GET_NEW_INCREMENT = 1

# Time period for incrementing value
INCREMENT_PERIOD = 0.5


class Client:
    """Byne challenge client class"""

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

    # Are we accessing the backup server?
    backup_mode = False


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


    def send_and_recv(self, request):
        """Wrapper around send() and recv()."""

        self.socket.send(request)
        if self.backup_mode:

            # Client is in backup mode; access server and hope for the best.
            return self.socket.recv()

        elif self.timeout <= 0:

            # Client is locked in primary mode; access server and hope for the best.
            return self.socket.recv()

        elif self.socket.poll(self.timeout * 1000) > 0:

            # We have something from the primary server. Yay!
            return self.socket.recv()

        else:

            # Primary server access timeout.
            sys.stderr.write('primary server access timeout; switching to backup...')

            # Stop timer threads
            self.restart_timers = False;
            time.sleep(6)

            # Clean todo queue.
            self.todo = Queue.Queue()

            # Switch to backup server.
            self.socket = zmq.Context.instance().socket(zmq.REQ)
            self.socket.setsockopt(zmq.IDENTITY, self.cid)
            self.socket.connect(self.backup_endpoint)
            self.backup_mode = True

            # Start timer threads.
            self.start_timers()

            # Repeat access to server.
            return self.send_and_recv(request)


    def start_timers(self):
        """Start internal timers."""

        self.restart_timers = True;
        threading.Timer(INCREMENT_PERIOD, self.work).start()
        threading.Timer(random.uniform(3.0, 5.0), self.queue_get_increment).start()


    def start(self, primary_endpoint, backup_endpoint, primary_timeout=0):
        """Connect to a Byne challenge server at a 0MQ endpoint"""

        self.backup_endpoint = backup_endpoint
        self.timeout = primary_timeout

        # Connect to server
        self.socket = zmq.Context.instance().socket(zmq.REQ)
        self.socket.setsockopt(zmq.IDENTITY, self.cid)
        self.socket.connect(primary_endpoint)

        # Salute server
        request = chr(protocol.CMD_HELLO)
        reply = self.send_and_recv(request)
        assert len(reply) >= 3, "unexpected hello reply length (%d)" % len(reply)
        assert ord(reply[0]) == protocol.CMD_HELLO, "unexpected server reply command: expected %d, got %d" % (protocol.CMD_HELLO, ord(reply[0]))

        # Check for protocol version
        proto_ver = ord(reply[1])
        assert proto_ver == protocol.VERSION, "cannot handle protocol version %d" % proto_ver

        # Update working value with server reply
        self.working_value = ord(reply[2])
        assert 0 <= self.working_value <= 99, "out of range value from server: %d" % self.working_value

        # Start periodic workers
        self.start_timers()

        # Loop forever
        while True:

            try:

                # Wait until there is something to do
                next_action = self.todo.get()
                if next_action == TODO_SEND_VALUE:

                    # Work value has been updated
                    # Send it to server
                    request = "".join([chr(protocol.CMD_ACCEPT_VALUE), chr(self.working_value)])
                    reply = self.send_and_recv(request)
                    assert len(reply) >= 1, "unexpected accept value reply length (%d)" % len(reply)
                    assert ord(reply[0]) == protocol.CMD_ACCEPT_VALUE, "unexpected server reply command: expected %d, got %d" % (protocol.CMD_ACCEPT_VALUE, ord(reply[0]))

                else:

                    # It's time to get a new increment value from server
                    command = protocol.CMD_GET_EVEN
                    if self.odd:
                        command = protocol.CMD_GET_ODD
                    request = ''.join([chr(command)])
                    reply = self.send_and_recv(request)
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
    parser.add_argument('primary_url', nargs=1, help='0MQ endpoint of primary server')
    parser.add_argument('backup_url', nargs=1, help='0MQ endpoint of backup server')
    parser.add_argument('timeout', nargs=1, type=int, help='primary server access timeout in seconds (0 = infinite)')
    args = parser.parse_args()
    client_id = args.client_id[0]
    client_type = args.client_type[0]
    primary_url = args.primary_url[0]
    backup_url = args.backup_url[0]
    client_timeout = args.timeout[0]
    if client_timeout < 0:
        client_timeout = 0

    # Start client
    sys.stderr.write('starting client "%s" of %s type, connecting to %s with backup %s\n' % (client_id, client_type, primary_url, backup_url))
    Client(cid=client_id, odd=(client_type=='odd')).start(primary_url, backup_url, primary_timeout=client_timeout)

