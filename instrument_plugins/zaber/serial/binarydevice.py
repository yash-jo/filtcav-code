import logging

from .binarycommand import BinaryCommand
from .unexpectedreplyerror import UnexpectedReplyError

# See https://docs.python.org/2/howto/logging.html#configuring-logging-
# for-a-library for info on why we have these two lines here.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class BinaryDevice(object):
    """A class to represent a Zaber device in the Binary protocol. It is safe
    to use in multi-threaded environments.

    Attributes:
        port: A BinarySerial object which represents the port to which
            this device is connected.
        number: The integer number of this device. 1-255.
    """
    def __init__(self, port, number):
        """
        Args:
            port: A BinarySerial object to use as a parent port.
            number: An integer between 1 and 255 which is the number of
                this device.

        Raises:
            ValueError: The device number was invalid.
        """
        if number > 255 or number < 1:
            raise ValueError("Device number must be 1-255.")
        self.number = number
        self.port = port


    def send(self, *args):
        """Sends a command to this device, then waits for a response.

        Args:
            *args: Either a single BinaryCommand, or 1-3 integers
                specifying, in order, the command number, data value,
                and message ID of the command to be sent.

        Notes:
            The ability to pass integers to this function is provided
            as a convenience to the programmer. Calling
            ``device.send(2)`` is equivalent to calling
            ``device.send(BinaryCommand(device.number, 2))``.

            Note that in the Binary protocol, devices will only reply
            once they have completed a command. Since this function
            waits for a reply from the device, this function may block
            for a long time while it waits for a response. For the same
            reason, it is important to set the timeout of this device's
            parent port to a value sufficiently high that any command
            sent will be completed within the timeout.

            Regardless of the device address specified to this function,
            the device number of the transmitted command will be
            overwritten with the number of this device.

            If the command has a message ID set, this function will return
            a reply with a message ID. It does not check whether the message
            IDs match.

        Raises:
            UnexpectedReplyError: The reply read was not sent by this
                device or the message ID of the reply (if in use) did not
                match the message ID of the command.

        Returns: A BinaryReply containing the reply received.
        """
        if len(args) == 1 and isinstance(args[0], BinaryCommand):
            command = args[0]
        elif len(args) < 4:
            command = BinaryCommand(self.number, *args)

        command.device_number = self.number
        with self.port.lock:
            self.port.write(command)
            reply = self.port.read(command.message_id is not None)

        if ((reply.device_number != self.number)
            or ((reply.message_id or 0) != (command.message_id or 0))):
            raise UnexpectedReplyError(
                "Received an unexpected reply from device number {0:d}".format(
                    reply.device_number
                ),
                reply
            )
        return reply


    def home(self):
        """Sends the "home" command (1), then waits for the device to
        reply.

        Returns: A BinaryReply containing the reply received.
        """
        return self.send(1)


    def move_abs(self, position):
        """Sends the "move absolute" command (20), then waits for the
        device to reply.

        Args:
            position: The position in microsteps to which to move.

        Returns: A BinaryReply containing the reply received.
        """
        return self.send(20, position)


    def move_rel(self, distance):
        """Sends the "move relative" command (21), then waits for the
        device to reply.

        Args:
            distance: The distance in microsteps to which to move.

        Returns: A BinaryReply containing the reply received.
        """
        return self.send(21, distance)


    def move_vel(self, speed):
        """Sends the "move at constant speed" command (22), then waits
        for the device to reply.

        Args:
            speed: An integer representing the speed at which to move.

        Notes:
            Unlike the other "move" commands, the device replies
            immediately to this command. This means that when this
            function returns, it is likely that the device is still
            moving.

        Returns: A BinaryReply containing the reply received.
        """
        return self.send(22, speed)


    def stop(self):
        """Sends the "stop" command (23), then waits for the device to
        reply.

        Returns: A BinaryReply containing the reply received.
        """
        return self.send(23)


    def get_status(self):
        """Sends the "Return Status" command (54), and returns the
        result.

        Returns:
            An integer representing a `status code`_, according to
            Zaber's Binary Protocol Manual.

        .. _status code: http://www.zaber.com/wiki/Manuals/Binary_Protoc
            ol_Manual#Return_Status_-_Cmd_54
        """
        return self.send(54).data


    def get_position(self):
        """Sends the "Return Current Position" command (60), and returns the
        result.

        Returns:
            An integer representing the device's current position, it its
            native units of measure - see the device manual for unit conversions.
        """
        return self.send(60).data
