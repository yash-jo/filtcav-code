import logging

# See https://docs.python.org/2/howto/logging.html#configuring-logging-
# for-a-library for info on why we have these two lines here.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class AsciiCommand(object):
    """Models a single command in Zaber's ASCII protocol.

    Attributes:
        device_address: An integer representing the address of the
            device to which to send this command.
        axis_number: The integer number of the particular axis which
            should execute this command. An axis number of 0 specifies
            that all axes should execute the command, or that the
            command is "device scope".
        message_id: Optional. An integer to be used as a message ID.
            If a command has a message ID, then the device will send a
            reply with a matching message ID. A message_id value of
            None indicates that a message ID is not to be used.
            0 is a valid message ID.
        data: The bulk of the command. data includes a valid ASCII
            command and any parameters of that command, separated by
            spaces. A data value of "" (the empty string) is valid,
            and is often used as a "get status" command to query
            whether a device is busy or idle.
    """

    def __init__(self, *args):
        r"""
        Args:
            *args: A number of arguments beginning with 0 to 3 integers
                followed by one or more strings.

        Notes:
            For every absent integer argument to ``__init__``, any string
            argument(s) will be examined for leading integers. The first
            integer found (as an argument or as the leading part of a
            string) will set the ``device_address`` property, the second
            integer will be taken as the ``axis_number`` property, and
            the third integer found will be the ``message_id`` property.

            When a string argument contains text which can not be
            interpreted as an integer, all arguments which follow it
            are considered to be a part of the data. This is consistent
            with how ASCII commands are parsed by the Zaber device
            firmware.

            All leading '/' and trailing '\\r\\n' characters in string
            arguments are stripped when the arguments are parsed.

        Examples:
            The flexible argument structure of this constructor allows
            commands to be constructed by passing in integers followed
            by a command and its parameters, or by passing in one
            fully-formed, valid ASCII command string, or a mix of the
            two if the user desires.

            For example, all of the following constructors will create
            identical AsciiCommand objects::

                >>> AsciiCommand("/1 0 move abs 10000\r\n")
                >>> AsciiCommand("1 move abs 10000")
                >>> AsciiCommand(1, 0, "move abs 10000")
                >>> AsciiCommand(1, "move abs 10000")
                >>> AsciiCommand("1", "move abs", "10000")
                >>> AsciiCommand(1, "move abs", 10000)

        Raises:
            TypeError: An argument was passed to the constructor which
                was neither an integer nor a string.
        """
        self.data = ''
        attributes = iter(["device_address", "axis_number", "message_id"])
        for arg in args:
            if isinstance(arg, int):
                try:
                    # If self.data has got something in it,
                    # then all remaining arguments are also data.
                    if self.data:
                        raise StopIteration
                    next_attr = next(attributes)
                    setattr(self, next_attr, arg)
                except StopIteration:
                    self.data = ' '.join([self.data, str(arg)]) if self.data \
                            else str(arg)

            elif isinstance(arg, (bytes, str)):
                if isinstance(arg, bytes):
                    arg = arg.decode()

                # Trim leading '/' and trailing "\r\n".
                arg = arg.lstrip('/')
                arg = arg.rstrip('\r\n')

                tokens = arg.split(' ')
                for i, token in enumerate(tokens):
                    try:
                        # As above: if data has already been found,
                        # all remaining arguments/tokens are also data.
                        if self.data:
                            raise StopIteration
                        num = int(token)  # Is it a number?
                        next_attr = next(attributes)  # If it *is* a number...
                        setattr(self, next_attr, num)  # ...set the next attribute.
                    except (ValueError, StopIteration):
                        # If token is not a number, or if we are out of
                        # attributes, the remaining text is data.
                        data = ' '.join(tokens[i:])
                        self.data = ' '.join([self.data, data]) if self.data \
                            else data
                        break
            else:
                raise TypeError("All arguments to AsciiCommand() must be "
                                "either strings or integers. An argument of "
                                "type {0:s} was passed.".format(str(type(arg))))

        # Set remaining attributes.
        if not hasattr(self, "device_address"):
            self.device_address = 0
        if not hasattr(self, "axis_number"):
            self.axis_number = 0
        if not hasattr(self, "message_id"):
            self.message_id = None


    def encode(self):
        """Return a valid ASCII command based on this object's
        attributes.

        The string returned by this function is a fully valid command,
        formatted according to Zaber's `Ascii Protocol Manual`_.

        Returns:
            A valid, fully-formed ASCII command.
        """
        if self.message_id is not None:
            if self.data:
                return "/{0:d} {1:d} {2:d} {3:s}\r\n".format(
                    self.device_address,
                    self.axis_number,
                    self.message_id,
                    self.data
                ).encode()
            else:
                return "/{0:d} {1:d} {2:d}\r\n".format(
                    self.device_address,
                    self.axis_number,
                    self.message_id
                ).encode()

        if self.data:
            return "/{0:d} {1:d} {2:s}\r\n".format(
                self.device_address,
                self.axis_number,
                self.data
            ).encode()
        else:
            return "/{0:d} {1:d}\r\n".format(
                self.device_address,
                self.axis_number
            ).encode()


    def __str__(self):
        """Returns an encoded ASCII command, without the newline
        terminator.

        Returns:
            A string containing an otherwise-valid ASCII command,
            without the newline (ie. "\r\n") at the end of the string
            for ease of printing.
        """
        string = self.encode().rstrip(b"\r\n")
        # A little bit of type-checking for Python 2/3 compatibility.
        if not isinstance(string, str):
            string = string.decode()
        return string
