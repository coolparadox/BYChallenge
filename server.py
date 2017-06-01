#
# Byne challenge server
#

import logging
import random
import zmq

# Communication protocol commands, see protocol specification at
# https://github.com/coolparadox/BYChallenge/wiki/Protocol-Specification
CMD_HELLO = 0x00
CMD_GET_EVEN = 0x01
CMD_GET_ODD = 0x02
CMD_ACCEPT_VALUE = 0x03

# Version of communication protocol
PROTOCOL_VERSION = 1

def make_even_number():
    """Produce an even pseudo random number from 0 to 99."""
    return random.randrange(0, 100, 2)

def make_odd_number():
    """Produce an odd pseudo random number from 0 to 99."""
    return random.randrange(1, 100, 2)

class Server:
    """Byne challenge server."""

    def __init__(self, log_file):

        logging.basicConfig(filename=log_file, level=logging.DEBUG)
        logging.info('Byne challenge server instantiated.')

    def start(self, endpoint):
        """Binds to a 0MQ endpoint and start serving."""

        # Bind to 0MQ socket
        ctx = zmq.Context.instance()
        socket = ctx.socket(zmq.REP)
        socket.bind(endpoint)
        logging.info("binded to endpoint %s" % endpoint)

        # Serve
        while True:

            # Wait for a request
            msg = socket.recv()

            # FIXME: identify client
            client_id = 0

            # Parse message
            command = CMD_HELLO
            if len(msg) != 0:
                command = ord(msg[0])
            else:
                logging.warning("zero length message received from %s; assuming hello request" % client_id)

            if command == CMD_HELLO:

                logging.debug("received hello request from %s" % client_id)
                # FIXME: lookup client current value
                client_value = 0
                answer = ''.join([chr(commmand), chr(PROTOCOL_VERSION), chr(client_value)])
                socket.send(answer)
                logging.debug("sent hello reply to %s: protocol version %d, client value %d" % (client_id, PROTOCOL_VERSION, client_value))

            elif command == CMD_GET_EVEN:

                logging.debug("received get_even request from %s" % client_id)
                value = make_even_number()
                answer = ''.join([chr(command), chr(value)])
                socket.send(answer)
                logging.debug("sent get_even reply to %s: value %d" % (client_id, value))

            elif command == CMD_GET_ODD:

                logging.debug("received get_odd request from %s" % client_id)
                value = make_odd_number()
                answer = ''.join([chr(command), chr(value)])
                socket.send(answer)
                logging.debug("sent get_odd reply to %s: value %d" % (client_id, value))

            elif command == CMD_ACCEPT_VALUE:

                value = 0
                if len(msg) >= 2:
                    value = ord(msg[1])
                    logging.debug("received accept_value request from %s: value %d" % (client_id, value))
                else:
                    logging.warning("received accept_value request from %s without parameter; assuming %d" % (client_id, value))
                answer = ''.join([chr(command)])
                socket.send(answer)
                logging.debug("sent accept_value reply to %s" % client_id)

            else:

                logging.warning("unknown command %d received from %s; assuming hello request" % (command, client_id))
                # FIXME: lookup client current value
                answer = ''.join([chr(CMD_HELLO), chr(PROTOCOL_VERSION), chr(0)])
                socket.send(answer)

# Start server
Server('/tmp/server.log').start("tcp://*:5555")

