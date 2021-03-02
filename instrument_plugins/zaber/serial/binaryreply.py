import logging
import struct

# See https://docs.python.org/2/howto/logging.html#configuring-logging-
# for-a-library for info on why we have these two lines here.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class BinaryReply(object):
    """Models a single reply in Zaber's Binary protocol.

    Attributes:
        device_number: The number of the device from which this reply
            was sent.
        command_number: The number of the command which triggered this
            reply.
        data: The data value associated with the reply.
        message_id: The message ID number, if present, otherwise None.
    """
    def __init__(self, reply, message_id=False):
        """
        Args:
            reply: A byte string of length 6 containing a binary reply
                encoded according to Zaber's Binary Protocol Manual.
            message_id: True if a message ID should be extracted from
                the reply, False if not.

        Notes:
            Because a Binary reply's message ID truncates the last byte
            of the data value of the reply, it is impossible to tell
            whether a reply contains a message ID or not. Therefore, the
            user must specify whether or not a message ID should be
            assumed to be present.

        Raises:
            TypeError: An invalid type was passed as *reply*. This may
                indicate that a unicode string was passed instead of a
                binary (ascii) string.
        """
        if isinstance(reply, bytes):
            self.device_number, self.command_number, self.data = \
                    struct.unpack("<2Bl", reply)
            if (message_id):
                # Use bitmasks to extract the message ID.
                self.message_id = (self.data & 0xFF000000) >> 24
                self.data = self.data & 0x00FFFFFF

                # Sign extend 24 to 32 bits in the message ID case.
                # If the data is more than 24 bits it will still be wrong,
                # but now negative smaller values will be right.
                if 0 != (self.data & 0x00800000):
                    self.data = (int)((self.data | 0xFF000000) - (1 << 32))
            else:
                self.message_id = None

        elif isinstance(reply, list):
            # Assume a 4th element is a message ID.
            if len(reply) > 3:
                message_id = True
            self.device_number = reply[0]
            self.command_number = reply[1]
            self.data = reply[2]
            self.message_id = reply[3] if message_id else None

        else:
            raise TypeError("BinaryReply must be passed a byte string "
                            "('bytes' type) or a list.")


    def encode(self):
        """Returns the reply as a binary string, in the form in which it
        would appear if it had been read from the serial port.

        Returns:
            A byte string of length 6 formatted according to the Binary
            Protocol Manual.
        """
        return struct.pack("<2Bl",
                           self.device_number,
                           self.command_number,
                           self.data)


    def __str__(self):
        return "[{:d}, {:d}, {:d}]".format(self.device_number,
                                           self.command_number,
                                           self.data)

