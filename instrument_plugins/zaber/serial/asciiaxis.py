import logging

from .asciicommand import AsciiCommand
from .timeouterror import TimeoutError

# See https://docs.python.org/2/howto/logging.html#configuring-logging-
# for-a-library for info on why we have these two lines here.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class AsciiAxis(object):
    """Represents one axis of an ASCII device. It is safe to use in multi-
    threaded environments.

    Attributes:
        parent: An AsciiDevice which represents the device which has
            this axis.
        number: The number of this axis. 1-9.
    """

    def __init__(self, device, number):
        """
        Args:
            device: An AsciiDevice which is the parent of this axis.
            number: The number of this axis. Must be 1-9.

        Raises:
            ValueError: The axis number was not between 1 and 9.
        """
        if number < 1 or number > 9:
            raise ValueError("Axis number must be between 1 and 9.")
        self.number = number
        self.parent = device


    def send(self, message):
        """Sends a message to the axis and then waits for a reply.

        Args:
            message: A string or AsciiCommand object containing a
                command to be sent to this axis.

        Notes:
            Regardless of the device address or axis number supplied in
            (or omitted from) the message passed to this function, this
            function will always send the command to only this axis.

            Though this is intended to make sending commands to a
            particular axis easier by allowing the user to pass in a
            "global command" (ie. one whose target device and axis are
            both 0), this can result in some unexpected behaviour. For
            example, if the user tries to call send() with an
            AsciiCommand which has a different target axis number than
            the number of this axis, they may be surprised to find that
            the command was sent to this axis rather than the one
            originally specified in the AsciiCommand.

        Examples:
            Since send() will automatically set (or overwrite) the
            target axis and device address of the message, all of the
            following calls to send() will result in identical ASCII
            messages being sent to the serial port::

                >>> axis.send("home")
                >>> axis.send(AsciiCommand("home"))
                >>> axis.send("0 0 home")
                >>> axis.send("4 8 home")
                >>> axis.send(AsciiCommand(1, 4, "home"))

        Raises:
            UnexpectedReplyError: The reply received was not sent by the
                expected device and axis.

        Returns: An AsciiReply object containing the reply received.
        """
        if isinstance(message, (str, bytes)):
            message = AsciiCommand(message)

        # Always send the AsciiCommand to *this* axis.
        message.axis_number = self.number

        reply = self.parent.send(message)
        if reply.axis_number != self.number:
            raise UnexpectedReplyError(
                "Received a reply from an unexpected axis: axis {}".format(
                    reply.axis_number
                ),
                reply
            )
        return reply


    def home(self):
        """Sends the "home" command, then polls the axis until it is
        idle.

        Raises:
            UnexpectedReplyError: The reply received was not sent by the
                expected device and axis.

        Returns: An AsciiReply object containing the first reply
            received.
        """
        reply = self.send("home")
        self.poll_until_idle()
        return reply


    def move_abs(self, position, blocking=True):
        """Sends the "move abs" command to the axis to move it to the
        specified position, then polls the axis until it is idle.

        Args:
            position: An integer representing the position in
                microsteps to which to move the axis.
            blocking: An optional boolean, True by default. If set to
                False, this function will return immediately after
                receiving a reply from the device, and it will not poll
                the device further.

        Raises:
            UnexpectedReplyError: The reply received was not sent by the
                expected device and axis.

        Returns: An AsciiReply object containing the first reply
            received.
        """
        reply = self.send("move abs {0:d}".format(position))
        if blocking:
            self.poll_until_idle()
        return reply


    def move_rel(self, distance, blocking=True):
        """Sends the "move rel" command to the axis to move it by the
        specified distance, then polls the axis until it is idle.

        Args:
            distance: An integer representing the number of microsteps
                by which to move the axis.
            blocking: An optional boolean, True by default. If set to
                False, this function will return immediately after
                receiving a reply from the device, and it will not poll
                the device further.

        Raises:
            UnexpectedReplyError: The reply received was not sent by the
                expected device and axis.

        Returns: An AsciiReply object containing the first reply
            received.
        """
        reply = self.send("move rel {0:d}".format(distance))
        if blocking:
            self.poll_until_idle()
        return reply


    def move_vel(self, speed, blocking=False):
        """Sends the "move vel" command to make the axis move at the
        specified speed.

        Args:
            speed: An integer representing the speed at which to move
                the axis.
            blocking: An optional boolean, False by default. If set to
                True, this function will poll the device repeatedly
                until it reports that the axis is idle.

        Notes:
            Unlike the other two move commands, move_vel() does not by
            default poll the axis until it is idle. move_vel() will
            return immediately after receiving a response from the
            device unless the "blocking" argument is set to True.

        Raises:
            UnexpectedReplyError: The reply received was not sent by the
                expected device and axis.

        Returns: An AsciiReply object containing the first reply
            received.
        """
        reply = self.send("move vel {0:d}".format(speed))
        if blocking:
            self.poll_until_idle()
        return reply


    def stop(self):
        """Sends the "stop" command to the axis.

        Notes:
            The stop command can be used to pre-empt any movement
            command in order to stop the axis early.

        Raises:
            UnexpectedReplyError: The reply received was not sent by the
                expected device and axis.

        Returns: An AsciiReply object containing the first reply
            received.
        """
        reply = self.send("stop")
        self.poll_until_idle()
        return reply


    def get_status(self):
        """Queries the axis for its status and returns the result.

        Raises:
            UnexpectedReplyError: The reply received was not sent by the
                expected device and axis.

        Returns:
            A string containing either "BUSY" or "IDLE", depending on
            the response received from the axis.
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
        """
        return int(self.send("get pos").data)


    def poll_until_idle(self):
        """Polls the axis and blocks until the device reports that the
        axis is idle.

        Raises:
            UnexpectedReplyError: The reply received was not sent by the
                expected device and axis.

        Returns: An AsciiReply object containing the last reply
            received.
        """
        return self.parent.poll_until_idle(self.number)

