import logging
import serial
from threading import RLock

from .asciicommand import AsciiCommand
from .asciireply import AsciiReply
from .timeouterror import TimeoutError

# See https://docs.python.org/2/howto/logging.html#configuring-logging-
# for-a-library for info on why we have these two lines here.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class AsciiSerial(object):
    """A class for interacting with Zaber devices using the ASCII protocol. It
    is safe to use in multi-threaded environments.

    Attributes:
        baudrate: An integer representing the desired communication
            baud rate. Valid bauds are 115200, 57600, 38400, 19200, and
            9600.
        timeout: A number representing the number of seconds to wait
            for input before timing out. Floating-point numbers can be
            used to specify times shorter than one second. A value of
            None can also be used to specify an infinite timeout. A
            value of 0 specifies that all reads and writes should be
            non-blocking (return immediately without waiting). Defaults
            to 5.
        lock: The threading.RLock guarding the port. Each method takes the lock
            and is therefore thread safe. However, to ensure no other threads
            access the port across multiple method calls, the caller should
            acquire the lock.
    """
    def __init__(self, port, baud=115200, timeout=5, inter_char_timeout=0.5):
        """
        Args:
            port: A string containing the name or URL of the serial port to
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
            When *port* is not None, this constructor immediately
            opens the serial port. There is no need to call open()
            after creating this object, unless you passed None as
            *port*.

        Raises:
            ValueError: An invalid baud rate was specified.
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


    def write(self, command):
        """Writes a command to the serial port.

        Args:
            command: A string or AsciiCommand representing a command
                to be sent.
        """
        if isinstance(command, (str, bytes)):
            command = AsciiCommand(command)

        if not isinstance(command, AsciiCommand):
            raise TypeError("write must be passed a string or AsciiCommand.")

        logger.debug("> %s", command)

        # From "Porting Python 2 Code to Python 3":
        # "...when you receive text in binary data, you should
        # immediately decode it. And if your code needs to send text as
        # binary data then encode it as late as possible.
        # This allows your code to work with only [unicode] text
        # internally and thus eliminates having to keep track of what
        # type of data you are working with."
        # See https://docs.python.org/3/howto/pyporting.html#text-versu
        # s-binary-data
        with self._lock:
            self._ser.write(command.encode())


    def read(self):
        """Reads a reply from the serial port.

        Raises:
            zaber.serial.TimeoutError: The duration specified by *timeout*
                elapsed before a full reply could be read.
            ValueError: The reply read could not be parsed and is
                invalid.

        Returns:
            An `AsciiReply` containing the reply received.
        """
        with self._lock:
            line = self._ser.readline()

        if not line:
            logger.debug("< Receive timeout!")
            raise TimeoutError("read timed out.")

        decoded_line = line.decode()
        logger.debug("< %s", decoded_line.rstrip("\r\n"))
        return AsciiReply(decoded_line)


    def can_read(self):
        """Checks if any data has been received by the port, without blocking.

        If the return value is True, it means some data is available but
        it does not guarantee there is enough to read a complete reply; it's
        still possible for the next read call to block waiting for data, and
        it's still possible to time out if transmission was interrupted.

        Returns:
            True if data is available to read; False otherwise.
        """
        if (hasattr(self._ser, "in_waiting")):
            return (self._ser.in_waiting > 0)
        else:
            return (self._ser.inWaiting() > 0)


    def flush(self):
        """Flushes the buffers of the underlying serial port."""
        with self._lock:
            self._ser.flush()


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
            self.close()


    @property
    def lock(self):
        return self._lock


    @property
    def timeout(self):
        with self._lock:
            return self._ser.timeout


    @timeout.setter
    def timeout(self, t):
        with self._lock:
            self._ser.timeout = t


    @property
    def baudrate(self):
        with self._lock:
            return self._ser.baudrate


    @baudrate.setter
    def baudrate(self, b):
        with self._lock:
            if b not in (115200, 57600, 38400, 19200, 9600):
                raise ValueError(
                    "Invalid baud rate: {:d}. Valid baud rates are 115200, "
                    "57600, 38400, 19200, and 9600.".format(b)
                )
            self._ser.baudrate = b
