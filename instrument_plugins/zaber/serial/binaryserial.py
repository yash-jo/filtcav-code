import logging
import serial
import sys
from threading import RLock

from .binarycommand import BinaryCommand
from .binaryreply import BinaryReply
from .timeouterror import TimeoutError

# See https://docs.python.org/2/howto/logging.html#configuring-logging-
# for-a-library for info on why we have these two lines here.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class BinarySerial(object):
    """A class for interacting with Zaber devices using the Binary protocol.

    This class defines a few simple methods for writing to and reading
    from a device connected over the serial port. It is safe to use in multi-
    threaded environments.

    Attributes:
        baudrate: An integer representing the desired communication baud rate.
            Valid bauds are 115200, 57600, 38400, 19200, and 9600.
        timeout: A number representing the number of seconds to wait for input
            before timing out. Floating-point numbers can be used to specify
            times shorter than one second. A value of None can also be used to
            specify an infinite timeout. A value of 0 specifies that all reads
            and writes should be non-blocking (return immediately without
            waiting). Defaults to 5.
        lock: The threading.RLock guarding the port. Each method takes the lock
            and is therefore thread safe. However, to ensure no other threads
            access the port across multiple method calls, the caller should
            acquire the lock and release it once all methods have returned.
    """

    def __init__(self, port, baud=9600, timeout=5, inter_char_timeout=0.5):
        """Creates a new instance of the BinarySerial class.

        Args:
            port: A string containing the name of the serial port to
                which to connect.
            baud: An integer representing the baud rate at which to
                communicate over the serial port.
            timeout: A number representing the number of seconds to wait
                for a reply. Fractional numbers are accepted and can be
                used to specify times shorter than a second.
            inter_char_timeout : A number representing the number of seconds
                to wait between bytes in a reply. If your computer is bad at
                reading incoming serial data in a timely fashion, try
                increasing this value.

        Notes:
            This class will open the port immediately upon
            instantiation. This follows the pattern set by PySerial,
            which this class uses internally to perform serial
            communication.

        Raises:
            TypeError: The port argument passed was not a string.
        """
        if not isinstance(port, str):
            raise TypeError("port must be a string.")
        try:
            self._ser = serial.serial_for_url(port, do_not_open=True)
            self._ser.baudrate = baud
            self._ser.timeout = timeout
            self._ser.interCharTimeout = inter_char_timeout
            self._ser.open()
        except AttributeError:
            # serial_for_url not supported; use fallback
            self._ser = serial.Serial(port, baud, timeout=timeout,
                                      interCharTimeout=inter_char_timeout)

        self._lock = RLock()


    def write(self, *args):
        r"""Writes a command to the port.

        This function accepts either a BinaryCommand object, a set
        of integer arguments, a list of integers, or a string.
        If passed integer arguments or a list of integers, those
        integers must be in the same order as would be passed to the
        BinaryCommand constructor (ie. device number, then command
        number, then data, and then an optional message ID).

        Args:
            *args: A BinaryCommand to be sent, or between 2 and 4
                integer arguments, or a list containing between 2 and
                4 integers, or a string representing a
                properly-formatted Binary command.

        Notes:
            Passing integers or a list of integers is equivalent to
            passing a BinaryCommand with those integers as constructor
            arguments.

            For example, all of the following are equivalent::

                >>> write(BinaryCommand(1, 55, 1000))
                >>> write(1, 55, 1000)
                >>> write([1, 55, 1000])
                >>> write(struct.pack("<2Bl", 1, 55, 1000))
                >>> write('\x01\x37\xe8\x03\x00\x00')

        Raises:
            TypeError: The arguments passed to write() did not conform
                to the specification of ``*args`` above.
            ValueError: A string of length other than 6 was passed.
        """
        if len(args) == 1:
            message = args[0]
            if isinstance(message, list):
                message = BinaryCommand(*message)
        elif 1 < len(args) < 5:
            message = BinaryCommand(*args)
        else:
            raise TypeError("write() takes at least 1 and no more than 4 "
                            "arguments ({0:d} given)".format(len(args)))

        if isinstance(message, str):
            logger.debug("> %s", message)
            if len(message) != 6:
                raise ValueError("write of a string expects length 6.")

            # pyserial doesn't handle hex strings.
            if sys.version_info > (3, 0):
                data = bytes(message, "UTF-8")
            else:
                data = bytes(message)

        elif isinstance(message, BinaryCommand):
            data = message.encode()
            logger.debug("> %s", message)

        else:
            raise TypeError("write must be passed several integers, or a "
                            "string, list, or BinaryCommand.")

        with self._lock:
            self._ser.write(data)


    def read(self, message_id=False):
        """Reads six bytes from the port and returns a BinaryReply.

        Args:
            message_id: True if the response is expected to have a
                message ID. Defaults to False.

        Returns:
            A BinaryCommand containing all of the information read from
            the serial port.

        Raises:
            zaber.serial.TimeoutError: No data was read before the
                specified timeout elapsed.
        """
        with self._lock:
            reply = self._ser.read(6)

        if len(reply) != 6:
            logger.debug("< Receive timeout!")
            raise TimeoutError("read timed out.")
        parsed_reply = BinaryReply(reply, message_id)
        logger.debug("< %s", parsed_reply)
        return parsed_reply


    def flush(self):
        """Flushes the buffers of the underlying serial port."""
        with self._lock:
            self._ser.flush()


    def can_read(self):
        """Checks if enough data has been received to read a response, without blocking.

        If the return value is True, it means at least six bytes are available
        to read from the serial port, so calling read() will not block.

        Returns:
            True if a response is available to read; False otherwise.
        """
        if (hasattr(self._ser, "in_waiting")):
            return (self._ser.in_waiting >= 6)
        else:
            return (self._ser.inWaiting() >= 6)


    def open(self):
        """Opens the serial port."""
        with self._lock:
            self._ser.open()


    def close(self):
        """Closes the serial port."""
        with self._lock:
            self._ser.close()


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        with self._lock:
            self._ser.close()


    @property
    def lock(self):
        return self._lock


    @property
    def timeout(self):
        """The number of seconds to wait for input while reading.

        The ``timeout`` property accepts floating point numbers for
        fractional wait times.
        """
        with self._lock:
            return self._ser.timeout


    @timeout.setter
    def timeout(self, t):
        with self._lock:
            self._ser.timeout = t


    @property
    def baudrate(self):
        """The baud rate at which to read and write.

        The default baud rate for the Binary protocol is 9600. T-Series
        devices are only capable of communication at 9600 baud.
        A-Series devices can communicate at 115200, 57600, 38400,
        19200, and 9600 baud.

        Note that this changes the baud rate of the computer on which
        this code is running. It does not change the baud rate of
        connected devices.
        """
        with self._lock:
            return self._ser.baudrate


    @baudrate.setter
    def baudrate(self, b):
        if b not in (115200, 57600, 38400, 19200, 9600):
            raise ValueError("Invalid baud rate: {:d}. Valid baud rates are "
                             "115200, 57600, 38400, 19200, and 9600.".format(b))
        with self._lock:
            self._ser.baudrate = b
