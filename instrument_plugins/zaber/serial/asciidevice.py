import logging
import time

from .asciiaxis import AsciiAxis
from .asciicommand import AsciiCommand
from .unexpectedreplyerror import UnexpectedReplyError

# See https://docs.python.org/2/howto/logging.html#configuring-logging-
# for-a-library for info on why we have these two lines here.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class AsciiDevice(object):
    """Represents an ASCII device. It is safe to use in multi-threaded
    environments.

    Attributes:
        port: The port to which this device is connected.
        address: The address of this device. 1-99.
    """

    def __init__(self, port, address):
        """
        Args:
            port: An AsciiSerial object representing the port to which
                this device is connected.
            address: An integer representing the address of this
                device. It must be between 1-99.

        Raises:
            ValueError: The address was not between 1 and 99.
        """
        if address < 1 or address > 99:
            raise ValueError("Address must be between 1 and 99.")
        self.address = address
        self.port = port


    def axis(self, number):
        """Returns an AsciiAxis with this device as a parent and the
        number specified.

        Args:
            number: The number of the axis. 1-9.

        Notes:
            This function will always return a *new* AsciiAxis instance.
            If you are working extensively with axes, you may want to
            create just one set of AsciiAxis objects by directly using
            the AsciiAxis constructor instead of this function to avoid
            creating lots and lots of objects.

        Returns:
            A new AsciiAxis instance to represent the axis specified.
        """
        return AsciiAxis(self, number)


    def send(self, message):
        r"""Sends a message to the device, then waits for a reply.

        Args:
            message: A string or AsciiCommand representing the message
                to be sent to the device.

        Notes:
            Regardless of the device address specified in the message,
            this function will always send the message to this device.
            The axis number will be preserved.

            This behaviour is intended to prevent the user from
            accidentally sending a message to all devices instead of
            just one. For example, if ``device1`` is an AsciiDevice
            with an address of 1, device1.send("home") will send the
            ASCII string "/1 0 home\\r\\n", instead of sending the
            command "globally" with "/0 0 home\\r\\n".

        Raises:
            UnexpectedReplyError: The reply received was not sent by
                the expected device.

        Returns:
            An AsciiReply containing the reply received.
        """
        if isinstance(message, (str, bytes)):
            message = AsciiCommand(message)

        # Always send an AsciiCommand to *this* device.
        message.device_address = self.address

        with self.port.lock:
            # Write and read to the port while holding the lock
            # to ensure we get the correct response.
            self.port.write(message)
            reply = self.port.read()

        if (reply.device_address != self.address or
                reply.axis_number != message.axis_number or
                reply.message_id != message.message_id):
            raise UnexpectedReplyError(
                "Received an unexpected reply from device with address {0:d}, "
                "axis {1:d}".format(reply.device_address, reply.axis_number),
                reply
            )
        return reply


    def poll_until_idle(self, axis_number=0):
        """Polls the device's status, blocking until it is idle.

        Args:
            axis_number: An optional integer specifying a particular
                axis whose status to poll. axis_number must be between
                0 and 9. If provided, the device will only report the
                busy status of the axis specified. When omitted, the
                device will report itself as busy if any axis is moving.

        Raises:
            UnexpectedReplyError: The reply received was not sent by
                the expected device.

        Returns:
            An AsciiReply containing the last reply received.
        """
        while True:
            reply = self.send(AsciiCommand(self.address, axis_number, ""))
            if reply.device_status == "IDLE":
                break
            time.sleep(0.05)
        return reply


    def home(self):
        """Sends the "home" command, then polls the device until it is
        idle.

        Returns:
            An AsciiReply containing the first reply received.
        """
        reply = self.send("home")
        self.poll_until_idle()
        return reply


    def move_abs(self, position, blocking=True):
        """Sends the "move abs" command to the device to move it to the
        specified position, then polls the device until it is idle.

        Args:
            position: An integer representing the position in
                microsteps to which to move the device.
            blocking: An optional boolean, True by default. If set to
                False, this function will return immediately after
                receiving a reply from the device and it will not poll
                the device further.

        Raises:
            UnexpectedReplyError: The reply received was not sent by
                the expected device.

        Returns:
            An AsciiReply containing the first reply received.
        """
        reply = self.send("move abs {0:d}".format(position))
        if blocking:
            self.poll_until_idle()
        return reply


    def move_rel(self, distance, blocking=True):
        """Sends the "move rel" command to the device to move it by the
        specified distance, then polls the device until it is idle.

        Args:
            distance: An integer representing the number of microsteps
                by which to move the device.
            blocking: An optional boolean, True by default. If set to
                False, this function will return immediately after
                receiving a reply from the device, and it will not poll
                the device further.

        Raises:
            UnexpectedReplyError: The reply received was not sent by
                the expected device.

        Returns:
            An AsciiReply containing the first reply received.
        """
        reply = self.send("move rel {0:d}".format(distance))
        if blocking:
            self.poll_until_idle()
        return reply


    def move_vel(self, speed, blocking=False):
        """Sends the "move vel" command to make the device move at the
        specified speed.

        Args:
            speed: An integer representing the speed at which to move
                the device.
            blocking: An optional boolean, False by default. If set to
                True, this function will poll the device repeatedly
                until it reports that it is idle.

        Notes:
            Unlike the other two move commands, move_vel() does not by
            default poll the device until it is idle. move_vel() will
            return immediately after receiving a response from the
            device unless the "blocking" argument is set to True.

        Raises:
            UnexpectedReplyError: The reply received was not sent by
                the expected device.

        Returns:
            An AsciiReply containing the first reply received.
        """
        reply = self.send("move vel {0:d}".format(speed))
        if blocking:
            self.poll_until_idle()
        return reply


    def stop(self):
        """Sends the "stop" command to the device.

        Notes:
            The stop command can be used to pre-empt any movement
            command in order to stop the device early.

        Raises:
            UnexpectedReplyError: The reply received was not sent by
                the expected device.

        Returns:
            An AsciiReply containing the first reply received.
        """
        reply = self.send("stop")
        self.poll_until_idle()
        return reply


    def get_status(self):
        """Queries the device for its status and returns the result.

        Raises:
            UnexpectedReplyError: The reply received was not sent by
                the expected device.

        Returns:
            A string containing either "BUSY" or "IDLE", depending on
            the response received from the device.
        """
        return self.send("").device_status


    def get_position(self):
        """Queries the axis for its position and returns the result.

        Raises:
            UnexpectedReplyError: The reply received was not sent by the
                expected device and axis.

        Returns:
            A number representing the current device position in its native
            units of measure. See the device manual for unit conversions.
            If this command is used on a multi-axis device, the return value
            is the position of the first axis.
        """
        data = self.send("get pos").data
        if (" " in data):
            data = data.split(" ")[0]

        return int(data)

