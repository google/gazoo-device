# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Defines a serial port transport by wrapping the Pyserial interface.

TcpTransport implements the standard GDM transport interface (TransportBase).
"""
from __future__ import absolute_import
import fcntl
import os
import serial
import time

from gazoo_device import gdm_logger
from gazoo_device.switchboard import transport_properties as props
from gazoo_device.switchboard import transport_base
import six


logger = gdm_logger.get_gdm_logger()
DEFAULT_BAUDRATE = 115200
REOPEN_TIMEOUT = 20


class SerialTransport(transport_base.TransportBase):
    """Communication transport for serial port."""

    def __init__(self,
                 comms_address,
                 baudrate=DEFAULT_BAUDRATE,
                 bytesize=serial.EIGHTBITS,
                 parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE,
                 use_high_baudrate_flow_control=False,
                 auto_reopen=False,
                 open_on_start=True):
        """Initialize the SerialTransport object with the given serial properties.

        Args:
            comms_address (str): the path to the serial device to use
            baudrate (int): the initial baudrate serial property to use
            bytesize (int): the initial byte size serial property to use
            parity (str): the initial parity serial property to use
            stopbits (int): the initial stop bits serial property to use
            use_high_baudrate_flow_control (bool): whether to send control characters (XOFF, XON)
                                                   before & after writing to prevent
                                                   buffer issues at high baud rate (> 115200).
            auto_reopen (bool): flag indicating transport should be reopened if
                                unexpectedly closed.
            open_on_start (bool): flag indicating transport should be open on
                                  TransportProcess start.
        """
        super(SerialTransport, self).__init__(auto_reopen, open_on_start)
        self._max_read_errors = 3
        self._properties.update({
            props.BAUDRATE: baudrate,
            props.BYTESIZE: bytesize,
            props.PARITY: parity,
            props.STOPBITS: stopbits,
            props.XONXOFF: False,
            props.RTSCTS: False,
            props.DSRDTR: False,
            props.EXCLUSIVE: True,
            props.READ_REOPEN: True,
            props.USE_HIGH_BAUDRATE_FLOW_CONTROL: use_high_baudrate_flow_control
        })
        self.comms_address = comms_address
        self._read_errors = 0
        self._serial = serial.Serial()
        self._serial.port = comms_address

    def is_open(self):
        """Returns True if transport is currently open.

        Returns:
            bool: True if transport is currently open, False otherwise.
        """

        return hasattr(self, "_serial") and self._serial.isOpen()

    def _open(self):
        """Opens or reopens the serial port using the current property values.

        Raises:
            SerialException: if serial port path or properties are invalid.
        """

        self._serial.baudrate = self._properties[props.BAUDRATE]
        self._serial.bytesize = self._properties[props.BYTESIZE]
        self._serial.parity = self._properties[props.PARITY]
        self._serial.stopbits = self._properties[props.STOPBITS]
        self._serial.xonxoff = self._properties[props.XONXOFF]
        self._serial.rtscts = self._properties[props.RTSCTS]
        self._serial.dsrdtr = self._properties[props.DSRDTR]
        self._serial.exclusive = self._properties[props.EXCLUSIVE]
        self._serial.timeout = None
        self._serial.write_timeout = None
        self._serial.open()
        # Prevent inheritance of file descriptors to exec'd child processes [NEP-1852]
        fd = self._serial.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

    def _close(self):
        """Closes the serial port."""
        # Prevent holding on to the exclusive lock [NEP-2473]
        fcntl.flock(self._serial.fileno(), fcntl.LOCK_UN)
        self._serial.close()

    def _read(self, size=1, timeout=None):
        """Returns bytes read up to max_bytes within timeout in seconds specified.

        Args:
            size (int): maximum number of bytes to read within timeout seconds
            timeout (float): maximum seconds to wait to read bytes or indefinitely
                             if timeout=None. Default: None

        Raises:
            SerialException: when read or open raises one

        Returns:
            str: bytes read from transport or None if no bytes were read
        """
        self._serial.timeout = timeout
        try:
            in_waiting = self._serial.in_waiting
            if in_waiting > 3072:
                logger.warning("Serial port input buffer size exceeds 3072 bytes. "
                               "Data will be lost if buffer size exceeds 4095 bytes. \n"
                               "Input buffer size: {}".format(in_waiting))
            result = self._serial.read(size=size)
            if self._read_errors:
                self._read_errors -= 1
        except serial.SerialException as err:
            self._read_errors += 1
            no_data = "read but returned no data" in repr(err)
            read_reopen = self._properties[props.READ_REOPEN]
            if self._read_errors > self._max_read_errors or not no_data or not read_reopen:
                raise
            logger.warn("Recovering from read returned no data, try {}/{}".
                        format(self._read_errors, self._max_read_errors))
            # Close and reopen the serial port to fix no data serial port errors
            self.close()
            end_time = time.time() + REOPEN_TIMEOUT
            while not os.path.exists(self._serial.port) and time.time() < end_time:
                time.sleep(0.001)
            self.open()
            # Recursively try again up to max_read_error attempts
            result = self._read(size=size, timeout=timeout)
        return result

    def _write(self, data, timeout=None):
        """Writes data provided within timeout in seconds specified.

        Args:
            data (str): bytes to be written out within timeout seconds
            timeout (float): maximum seconds to wait to write bytes or indefinitely
                             if timeout=None. Default: None

        Raises:
            SerialTimeoutException: in case timeout != None and timeout is exceeded
                                    when writing to device.

        Returns:
            int: number of bytes written or None if no bytes were written

        Note:
            If the data provided is unicode it will be encoded into UTF-8
            compatible bytes before being written to the serial port.
        """
        if isinstance(data, six.text_type):
            data = data.encode("utf-8", errors="replace")

        # Whether to use flow control to prevent buffer issues at high baudrate
        use_flow_control = (self._properties[props.BAUDRATE] > DEFAULT_BAUDRATE
                            and self._properties[props.USE_HIGH_BAUDRATE_FLOW_CONTROL])

        if use_flow_control:
            self.send_xoff()

        self._serial.write_timeout = timeout
        bytes_written = self._serial.write(data)

        if use_flow_control:
            self.send_xon()

        return bytes_written

    def set_property(self, key, value):
        """Sets the property specified to the value provided.

        Args:
            key (str): of the property to set
            value (object): of the property to set

        Raises:
            KeyError: when key property doesn't exist
        """
        super(SerialTransport, self).set_property(key, value)

        # Propagate property if device is already open
        if self._serial.isOpen():
            if key == props.BAUDRATE:
                self._serial.baudrate = value
            if key == props.BYTESIZE:
                self._serial.bytesize = value
            if key == props.PARITY:
                self._serial.parity = value
            if key == props.STOPBITS:
                self._serial.stopbits = value
            if key == props.XONXOFF:
                self._serial.xonxoff = value
            if key == props.RTSCTS:
                self._serial.rtscts = value
            if key == props.DSRDTR:
                self._serial.dsrdtr = value
            if key == props.EXCLUSIVE:
                self._serial.exclusive = value

    def flush_buffers(self):
        """Flushes all buffers on the serial device. Used during baudrate switching.

        Args: None

        Raises:
            SerialException: when pyserial fails to flush the buffers.

        Returns: None
        """
        self._serial.flush()
        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()

    def send_xon(self):
        """Sends flow control XON byte.

        Args: None

        Raises:
            SerialException: when pyserial fails to send the XON byte.

        Returns: None
        """
        self._serial.set_input_flow_control(enable=True)

    def send_xoff(self):
        """Sends flow control XOFF byte.

        Args: None

        Raises:
            SerialException: when pyserial fails to send the XOFF byte.

        Returns: None
        """
        self._serial.set_input_flow_control(enable=False)

    def send_break_byte(self):
        """Sends break byte (Ctrl-C). Not to be confused by the UART "break condition".

        Args: None

        Raises:
            SerialException: when pyserial fails to send the break byte.

        Returns: None
        """
        self._serial.write(six.b('\x03'))
