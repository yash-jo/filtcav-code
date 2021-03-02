import logging
import struct

# See https://docs.python.org/2/howto/logging.html#configuring-logging-
# for-a-library for info on why we have these two lines here.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class BinaryCommand(object):
    """Models a single command in Zaber's Binary protocol.

    Attributes:
        device_number: An integer representing the number (*a.k.a.*
            address) of the device to which to send the command. A
            device number of 0 indicates the command should be executed
            by all devices. 0-255.
        command_number: An integer representing the command to be sent
            to the device. Command numbers are listed in Zaber's
            `Binary Protocol Manual`_. 0-255.
        data: The data value to be transmitted with the command.
        message_id: The `message ID`_ of the command. 0-255, or None if
            not present.

    .. _Binary Protocol Manual: http://www.zaber.com/wiki/Manuals/Binary
        _Protocol_Manual#Quick_Command_Reference
    .. _message ID: http://www.zaber.com/wiki/Manuals/Binary_Protocol_Ma
        nual#Set_Message_Id_Mode_-_Cmd_102
    """
    def __init__(self, device_number, command_number, data=0,
                 message_id=None):
        """
        Args:
            device_number: An integer specifying the number of the
                target device to which to send this command. 0-255.
            command_number: An integer specifying the command to be
                sent. 0-255.
            data: An optional integer containing the data value to be
                sent with the command. When omitted, *data* will be set
                to 0.
            message_id: An optional integer specifying a message ID to
                give to the message. 0-255, or None if no message ID is
                to be used.

        Raises:
            ValueError: An invalid value was passed.
        """
        if device_number < 0 or command_number < 0:
            raise ValueError(
                "Device and command number must be between 0 and 255."
            )
        self.device_number = device_number
        self.command_number = command_number
        self.data = data
        if message_id is not None and (message_id < 0 or message_id > 255):
            raise ValueError("Message ID must be between 0 and 255.")
        self.message_id = message_id


    def encode(self):
        """Encodes a 6-byte byte string to be transmitted to a device.

        Returns:
            A byte string of length 6, formatted according to Zaber's
            `Binary Protocol Manual`_.
        """
        packed = struct.pack("<2Bl",
                             self.device_number,
                             self.command_number,
                             self.data)
        if self.message_id is not None:
            packed = packed[:5] + struct.pack("B", self.message_id)
        return packed


    def __str__(self):
        return "[{:d}, {:d}, {:d}]".format(self.device_number,
                                           self.command_number,
                                           self.data)

