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
import time
import zmq

# Identity of this client
cid = "client"

# Current value to be worked on
working_value = 0

# Increment amount of working_value
increment_amount = 1

# Access control to socket
todo = Queue.Queue()

# Constants for access control to socket
TODO_SEND_VALUE = 0
TODO_GET_NEW_INCREMENT = 1

# Time period for incrementing value
INCREMENT_PERIOD = 0.5

# Globals that control switch to / from backup server
primary_endpoint = ''
backup_endpoint = ''
current_endpoint = ''
restart_timers = True;
socket = zmq.Context().socket(zmq.REQ)

def stop_timers():
    """Stop internal timers."""

    global restart_timers;

    restart_timers = False;
    time.sleep(6);


def start_timers():
    """Start internal timers."""

    global restart_timers;

    restart_timers = True;
    threading.Timer(INCREMENT_PERIOD, work).start()
    threading.Timer(random.uniform(3.0, 5.0), queue_get_increment).start()

def connect_to(server):
    """Connect to server"""

    global socket
    global working_value
    global cid

    sys.stderr.write('connecting to "%s"...\n' % server)

    # Connect to server
    socket.setsockopt(zmq.IDENTITY, cid)
    socket.connect(current_endpoint)

    # Salute server
    request = chr(protocol.CMD_HELLO)
    socket.send(request)
    reply = socket.recv()
    assert len(reply) >= 3, "unexpected hello reply length (%d)" % len(reply)
    assert ord(reply[0]) == protocol.CMD_HELLO, "unexpected server reply command: expected %d, got %d" % (protocol.CMD_HELLO, ord(reply[0]))

    # Check for protocol version
    proto_ver = ord(reply[1])
    assert proto_ver == protocol.VERSION, "cannot handle protocol version %d" % proto_ver

    # Update working value with server reply
    working_value = ord(reply[2])
    assert 0 <= working_value <= 99, "out of range value from server: %d" % working_value


def switch_server():
    """Disconnect from current server and connect to the other."""

    global primary_endpoint
    global backup_endpoint
    global current_endpoint
    global socket
    global todo

    # Stop working
    stop_timers()

    # Clear todo queue
    try:
        while True:
            todo.get_nowait()
    except Queue.Empty:
        pass

    # Disconnect from current server
    socket.disconnect(current_endpoint);
    socket = zmq.Context().socket(zmq.REQ)

    # Connect to other server
    if current_endpoint == primary_endpoint:
        current_endpoint = backup_endpoint
    else:
        current_endpoint = primary_endpoint
    connect_to(current_endpoint)

    # Back to work
    start_timers()


def work():
    """Increment working_value by increment_amount."""

    global working_value
    global increment_amount
    global todo
    global restart_timers

    # Restart timer
    if restart_timers:
        threading.Timer(INCREMENT_PERIOD, work).start()

    # Calculate new working value.
    # Apply automatic turn in order to keep it between 0 and 99.
    new_value = working_value + increment_amount
    if new_value > 99:
        new_value = new_value - 100

    # Update work value
    working_value = new_value

    # Notify for sending to server
    todo.put(TODO_SEND_VALUE)


def queue_get_increment():
    """Notify for getting a new increment value from server."""

    global todo
    global restart_timers

    # Detect server heartbeat failure
    if todo.qsize() > 50:
        sys.stderr.write('server "%s" is lost!\n' % current_endpoint)
        switch_server()
        return

    # Restart timer
    if restart_timers:
        threading.Timer(random.uniform(3.0, 5.0), queue_get_increment).start()

    # Notify
    todo.put(TODO_GET_NEW_INCREMENT)


class Client:
    """Byne challenge client."""

    # Does this client request odd numbers from server?
    odd = True

    def __init__(self, odd = True, cid = "client"):
        self.cid = cid
        self.odd = odd

    def start(self, primary, backup):
        """Connect to a Byne challenge server at a 0MQ endpoint"""

        global working_value
        global increment_amount
        global todo
        global primary_endpoint
        global backup_endpoint
        global current_endpoint
        global cid

        # Setup globals
        primary_endpoint = primary
        backup_endpoint = backup
        current_endpoint = primary_endpoint

        # Connect to server
        connect_to(current_endpoint)

        # Start working
        start_timers();

        # Loop forever
        while True:

            # Wait until there is something to do
            next_action = todo.get()
            if next_action == TODO_SEND_VALUE:

                # Work value has been updated
                # Send it to server
                request = "".join([chr(protocol.CMD_ACCEPT_VALUE), chr(working_value)])
                try:
                    reply = send_and_recv(request)
                    assert len(reply) >= 1, "unexpected accept value reply length (%d)" % len(reply)
                    assert ord(reply[0]) == protocol.CMD_ACCEPT_VALUE, "unexpected server reply command: expected %d, got %d" % (protocol.CMD_ACCEPT_VALUE, ord(reply[0]))
                except zmq.ZMQError:
                    # This may happen when switching server
                    pass

            else:

                # It's time to get a new increment value from server
                command = protocol.CMD_GET_EVEN
                if self.odd:
                    command = protocol.CMD_GET_ODD
                request = ''.join([chr(command)])
                try:
                    reply = send_and_recv(request)
                    assert len(reply) >= 2, "unexpected get value reply length (%d)" % len(reply)
                    assert ord(reply[0]) == command, "unexpected server reply command: expected %d, got %d" % (command, ord(reply[0]))
                    increment_amount = ord(reply[1])
                except zmq.ZMQError:
                    # This may happen when switching server
                    pass


def send_and_recv(request):

    global socket

    socket.send(request)
    return socket.recv()


if __name__ == '__main__':

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Byne challenge client')
    parser.add_argument('client_id', nargs=1, help='client identity')
    parser.add_argument('client_type', nargs=1, help='client type', choices=['odd', 'even'])
    parser.add_argument('primary_server', nargs=1, help='0MQ endpoint of primary server')
    parser.add_argument('backup_server', nargs=1, help='0MQ endpoint of backup server')
    args = parser.parse_args()
    client_id = args.client_id[0]
    client_type = args.client_type[0]
    primary_server = args.primary_server[0]
    backup_server = args.backup_server[0]

    # Start client
    sys.stderr.write('starting client "%s" of %s type\n' % (client_id, client_type))
    Client(cid=client_id, odd=(client_type=='odd')).start(primary_server, backup_server)

