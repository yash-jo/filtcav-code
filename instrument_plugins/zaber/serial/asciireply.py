import logging
import re

# See https://docs.python.org/2/howto/logging.html#configuring-logging-
# for-a-library for info on why we have these two lines here.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class AsciiReply(object):
    """Models a single reply in Zaber's ASCII protocol.

    Attributes:
        message_type: A string of length 1 containing either '@', '!',
            or '#', depending on whether the message type was a
            "reply", "alert", or "info", respectively. Most messages
            received from Zaber devices are of type "reply", or '@'.
        device_address: An integer between 1 and 99 representing the
            address of the device from which the reply was sent.
        axis_number: An integer between 0 and 9 representing the axis
            from which the reply was sent. An axis number of 0
            represents a reply received from the device as a whole.
        message_id: An integer between 0 and 255 if present, or None
            otherwise.
        reply_flag: A string of length two, containing either "OK" or
            "RJ", depending on whether the command was accepted or
            rejected by the device. Value will be None for device replies
            that do not have a reply flag, such as info and alert messages.
        device_status: A string of length 4, containing either "BUSY"
            or "IDLE", depending on whether the device is moving or
            stationary.
        warning_flag: A string of length 2, usually "--". If it is not
            "--", it will be one of the two-letter warning flags
            described in the `Warning Flags section`_ of the Ascii
            Protocol Manual.
        data: A string containing the response data.
        checksum: A string of length 2 containing two characters
            representing a hexadecimal checksum, or None if a checksum
            was not found in the reply.

    .. _Warning Flags section: http://www.zaber.com/wiki/Manuals/ASCII_
        Protocol_Manual#Warning_Flags
    """

    def __init__(self, reply_string):
        """
        Args:
            reply_string: A string in one of the formats described in
                Zaber's `Ascii Protocol Manual`_. It will be parsed by
                this constructor in order to populate the attributes of
                the new AsciiReply.

        Raises:
            ValueError: The string could not be parsed.

        .. _Ascii Protocol Manual: http://www.zaber.com/wiki/Manuals/AS
            CII_Protocol_Manual
        """
        reply_string = reply_string.strip("\r\n")

        if len(reply_string) < 5:
            raise ValueError("Reply string too short to be a valid reply.")

        # CHECK CHECKSUM
        # Any message type could have a checksum.
        if reply_string[-3] == ':':
            self.checksum = reply_string[-2:]
            reply_string = reply_string[:-3]
            # Test checksum
            sum = 0
            for ch in reply_string[1:]:
                try:
                    sum += ord(ch)
                except TypeError:
                    sum += ch  # bytes() elements are ints.
            # Truncate to last byte and XOR + 1, as per the LRC.
            # Convert to HEX but keep only last 2 digits, left padded by 0's
            correct_checksum = "{:02X}".format(((sum & 0xFF) ^ 0xFF) + 1)[-2:]
            if self.checksum != correct_checksum:
                raise ValueError(
                    "Checksum incorrect. Found {:s}, expected {:s}. Possible "
                    "data corruption detected.".format(self.checksum,
                                                       correct_checksum)
                )
        else:
            self.checksum = None

        # SET ATTRIBUTES
        self.message_type = reply_string[0]
        self.device_address = None
        self.axis_number = None
        self.message_id = None
        self.reply_flag = None
        self.device_status = None
        self.warning_flag = None
        self.data = None

        # @ is the "Reply" type
        if ('@' == self.message_type):
            match = re.match("@(\d+)\s(\d+)\s(?:(\d+)\s)?(\S+)\s(\S+)\s(\S+)\s(.+)", reply_string)
            if (not match):
                raise ValueError("Failed to parse reply: {}".format(reply_string))

            self.device_address = int(match.group(1))
            self.axis_number = int(match.group(2))
            if (match.group(3) is not None):
                self.message_id = int(match.group(3))
            self.reply_flag = match.group(4)
            self.device_status = match.group(5)
            self.warning_flag = match.group(6)
            self.data = match.group(7) or ""


        # # is the "Info" type
        elif ('#' == self.message_type):
            match = re.match("#(\d+)\s(\d+)\s(?:(\d+)\s)?(.*)", reply_string)
            if (not match):
                raise ValueError("Failed to parse info message: {}".format(reply_string))

            self.device_address = int(match.group(1))
            self.axis_number = int(match.group(2))
            if (match.group(3) is not None):
                self.message_id = int(match.group(3))
            self.data = match.group(4) or ""


        # ! is the "Alert" type
        elif ('!' == self.message_type):
            match = re.match("!(\d+)\s(\d+)\s(\S+)\s(\S+)(?:\s(.*))?", reply_string)
            if (not match):
                raise ValueError("Failed to parse alert: {}".format(reply_string))

            self.device_address = int(match.group(1))
            self.axis_number = int(match.group(2))
            self.device_status = match.group(3)
            self.warning_flag = match.group(4)
            self.data = match.group(5) or ""

        else:
            raise ValueError("Invalid response type: {}".format(self.message_type))


    def encode(self):
        """Encodes the AsciiReply's attributes back into a valid string
        resembling the string which would have created the AsciiReply.

        Returns:
            A string in the format described in Zaber's `Ascii Protocol
            Manual`_.

        .. _Ascii Protocol Manual: http://www.zaber.com/wiki/Manuals/AS
            CII_Protocol_Manual
        """
        retstr = ""
        if self.message_type == '@':
            if self.message_id is None:
                retstr = "@{:02d} {:d} {:s} {:s} {:s} {:s}".format(
                    self.device_address,
                    self.axis_number,
                    self.reply_flag,
                    self.device_status,
                    self.warning_flag,
                    self.data
                )
            else:
                retstr = "@{:02d} {:d} {:02d} {:s} {:s} {:s} {:s}".format(
                    self.device_address,
                    self.axis_number,
                    self.message_id,
                    self.reply_flag,
                    self.device_status,
                    self.warning_flag,
                    self.data
                )

        elif self.message_type == '#':
            if self.message_id is None:
                retstr = "#{:02d} {:d} {:s}".format(self.device_address,
                                                    self.axis_number,
                                                    self.data)
            else:
                retstr = "#{:02d} {:d} {:02d} {:s}".format(self.device_address,
                                                           self.axis_number,
                                                           self.message_id,
                                                           self.data)

        elif self.message_type == '!':
            if self.message_id is None:
                retstr = "!{:02d} {:d} {:s} {:s}".format(self.device_address,
                                                         self.axis_number,
                                                         self.device_status,
                                                         self.warning_flag)
            else:
                retstr = "!{:02d} {:d} {:02d} {:s} {:s}".format(
                    self.device_address,
                    self.axis_number,
                    self.message_id,
                    self.device_status,
                    self.warning_flag
                )

        if self.checksum is not None:
            return "{:s}:{:s}\r\n".format(retstr, self.checksum)
        else:
            return "{:s}\r\n".format(retstr)


    def __str__(self):
        """Returns a reply string resembling the string which would have
        created this AsciiReply.

        Returns:
            The same string as is returned by encode().
        """
        return self.encode()

