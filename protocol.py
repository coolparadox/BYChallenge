"""
Byne challenge protocol contants.

This is common code used by server and client.

Source code: https://github.com/coolparadox/BYChallenge

Communication protocol specification:
https://github.com/coolparadox/BYChallenge/wiki/Protocol-Specification

"""

# Communication protocol commands, see protocol specification at
# https://github.com/coolparadox/BYChallenge/wiki/Protocol-Specification
CMD_HELLO = 0x00
CMD_GET_EVEN = 0x01
CMD_GET_ODD = 0x02
CMD_ACCEPT_VALUE = 0x03

# Version of communication protocol
VERSION = 1

