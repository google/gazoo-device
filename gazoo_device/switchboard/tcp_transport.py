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

"""TcpTransport is used for connection-oriented transmissions.

TcpTransport is responsible for delivering data to the appropriate application process
on the host computer. A host and port number are combined to create a network socket (an
identification address of a process-to-process communication). The socket can
then used by an application to handle a data stream for various needs.

TcpTransport implements the standard GDM transport interface (TransportBase).
"""

from __future__ import absolute_import
import socket
import six
from gazoo_device.switchboard import transport_properties
from gazoo_device.switchboard import transport_base

CONNECT_TIMEOUT = 10.0  # in secs


def check_port(port):
    """Verifies port value given is valid.

    Args:
        port (int): port number to verify

    Raises:
        ValueError: if port number provided is invalid

    Returns:
        int: port number
    """

    if port < 0 or port > 65535:
        raise ValueError("Port {} out of range".format(port))
    return port


def check_host(host):
    """Verifies host given is valid.

    Args:
        host (str): Either IP Address or hostname to verify

    Raises:
        ValueError: if ip address provided is invalid

    Returns:
        str: host
    """

    try:  # Valid ip address?
        socket.inet_pton(socket.AF_INET, host)
    except socket.error:
        try:  # Valid hostname?
            socket.getaddrinfo(host, None)
        except socket.error:
            raise ValueError("Host Address {} not valid".format(host))
    return host


class TcpTransport(transport_base.TransportBase):
    """Transport to communicate to ISA3 boxes."""

    def __init__(self,
                 comms_address,
                 args,
                 connect_timeout=CONNECT_TIMEOUT,
                 auto_reopen=False,
                 open_on_start=False):
        """Initialize the TcpTransport object with the given TCP properties.

        Args:
            comms_address (str): hostname or IP address of the device to connect to.
            args (str): The port to communicate to.
            connect_timeout (float): timeout on the socket instance before attempting connect.
            auto_reopen (bool): flag indicating transport should be reopened if
                                unexpectedly closed.
            open_on_start (bool): flag indicating transport should be open on
                                  TransportProcess start.

        Raises:
            ValueError: host not valid or port out of range
        """
        self.comms_address = comms_address
        port = int(args)
        super(TcpTransport, self).__init__(auto_reopen, open_on_start)
        self._properties.update({
            transport_properties.HOST: comms_address,
            transport_properties.PORT: int(args),
            transport_properties.CONNECT_TIMEOUT: connect_timeout,
        })
        check_host(comms_address)
        check_port(port)
        self._socket = None

    def is_open(self):
        """Returns True if tcp socket has been created.

        Returns:
            bool: True if _socket is not None
        """
        return hasattr(self, "_socket") and self._socket is not None

    def _open(self):
        """Opens or reopens the tcp connection using the current property values.

        Raises:
            IOError: if host and port do not resolve
        """
        self._socket = socket.create_connection(
            (self._properties[transport_properties.HOST],
             self._properties[transport_properties.PORT]),
            self._properties[transport_properties.CONNECT_TIMEOUT])

    def _close(self):
        """Closes the TCP connection."""
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()
        self._socket = None

    def _read(self, size=1, timeout=None):
        """Returns bytes read up to max_bytes within timeout in seconds specified.

        Args:
            size (int): maximum number of bytes to read within timeout seconds
            timeout (float): maximum seconds to wait to read bytes or indefinitely
                             if timeout=None. Default: None

        Returns:
            str: bytes read from transport
                 or "" if no bytes were read
                 or "" if timeout was reached
        """
        try:
            self._socket.settimeout(timeout)
            read_bytes = self._socket.recv(size)
            return "" if read_bytes is None else read_bytes
        except socket.timeout:
            return ""

    def _write(self, data, timeout=None):
        """Writes the command provided to the TCP socket.

        Args:
            data (str): bytes to be written out within timeout seconds
            timeout (float): maximum seconds to wait to write bytes or indefinitely
                             if timeout=None. Default: None

        Returns:
            int: number of bytes written or None if no bytes were written
        """
        if isinstance(data, six.text_type):
            data = data.encode("utf-8", errors="replace")

        self._socket.settimeout(timeout)
        self._socket.sendall(data)
        return len(data)
