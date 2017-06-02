#
# Byne challenge server
#

import argparse
import logging
import protocol
import random
import sys
import zmq

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

        # Latest values sent to clients.
        # (key is the client id)
        values = dict()

        # Bind to 0MQ socket
        ctx = zmq.Context.instance()
        socket = ctx.socket(zmq.ROUTER)
        socket.bind(endpoint)
        logging.info("binded to endpoint %s" % endpoint)

        # Serve
        while True:

            # Wait for clients
            frames = socket.recv_multipart()
            if len(frames) != 3:
                logging.warning("received message with %d frames, ignoring" % len(frames))
                continue
            cid = frames[0] # client id
            efd = frames[1] # empty frame delimiter
            req = frames[2] # client message
            if len(cid) < 1:
                logging.warning("empty client identifier; ignoring")
                continue
            if len(efd) != 0:
                logging.warning("not empty frame delimiter; ignoring")
                continue
            if len(req) < 1:
                logging.warning("empty client request; ignoring")
                continue

            # Parse client request
            command = protocol.CMD_HELLO
            if len(req) != 0:
                command = ord(req[0])
            else:
                logging.warning("zero length message received from %s; assuming hello request" % cid)

            if command == protocol.CMD_HELLO:

                logging.debug("received hello request from %s" % cid)
                value = values.get(cid, 0)
                answer = ''.join([chr(command), chr(protocol.VERSION), chr(value)])
                socket.send_multipart([cid, efd, answer])
                logging.debug("sent hello reply to %s: protocol version %d, client value %d" % (cid, protocol.VERSION, value))

            elif command == protocol.CMD_GET_EVEN:

                logging.debug("received get_even request from %s" % cid)
                value = make_even_number()
                answer = ''.join([chr(command), chr(value)])
                socket.send_multipart([cid, efd, answer])
                values[cid] = value
                logging.debug("sent get_even reply to %s: value %d" % (cid, value))

            elif command == protocol.CMD_GET_ODD:

                logging.debug("received get_odd request from %s" % cid)
                value = make_odd_number()
                answer = ''.join([chr(command), chr(value)])
                socket.send_multipart([cid, efd, answer])
                values[cid] = value
                logging.debug("sent get_odd reply to %s: value %d" % (cid, value))

            elif command == protocol.CMD_ACCEPT_VALUE:

                value = 0
                if len(req) >= 2:
                    value = ord(req[1])
                    logging.debug("received accept_value request from %s: value %d" % (cid, value))
                else:
                    logging.warning("received accept_value request from %s without parameter; assuming %d" % (cid, value))
                answer = ''.join([chr(command)])
                socket.send_multipart([cid, efd, answer])
                logging.debug("sent accept_value reply to %s" % cid)

            else:

                logging.warning("unknown command %d received from %s; assuming hello request" % (command, cid))
                command = protocol.CMD_HELLO
                value = values.get(cid, 0)
                answer = ''.join([chr(command), chr(protocol.VERSION), chr(value)])
                socket.send_multipart([cid, efd, answer])
                logging.debug("sent hello reply to %s: protocol version %d, client value %d" % (cid, protocol.VERSION, value))


if __name__ == '__main__':

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Byne challenge server')
    parser.add_argument('log_file', nargs=1, help='path to log file')
    parser.add_argument('endpoint', nargs=1, help='0MQ endpoint to bind')
    args = parser.parse_args()
    log_file = args.log_file[0]
    endpoint = args.endpoint[0]

    # Start server
    Server(log_file=log_file).start(endpoint)

