# Copyright 2021 Google LLC
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

"""Transport based on the websocket protocol.

NOTE: the WebSocket protocol is NOT the same thing as a TCP/IP socket.
The WebSocket protocol is an application layer (layer 7) protocol.
    See https://tools.ietf.org/html/rfc6455.
TCP socket is a transport layer (layer 4) protocol.
    For a transport based on a TCP socket, see tcp_transport.py.
"""
import traceback

from gazoo_device import gdm_logger
from gazoo_device.switchboard import transport_properties
from gazoo_device.switchboard.transports import tcp_transport
from gazoo_device.switchboard.transports import transport_base
import websocket

logger = gdm_logger.get_logger(__file__)


class WebSocketTransport(transport_base.TransportBase):
  """WebSocket-based transport."""

  def __init__(self,
               comms_address,
               connect_timeout=tcp_transport.CONNECT_TIMEOUT,
               auto_reopen=False,
               open_on_start=True):
    """Initialize the WebSocketTransport.

    Args:
        comms_address (str): websocket URL to connect to (ws://...)
        connect_timeout (float): timeout on the socket instance before
          attempting connect.
        auto_reopen (bool): flag indicating transport should be reopened if
          unexpectedly closed.
        open_on_start (bool): flag indicating transport should be open on
          TransportProcess start.
    """
    super(WebSocketTransport, self).__init__(auto_reopen, open_on_start)
    self._properties.update({
        transport_properties.CONNECT_TIMEOUT: connect_timeout,
        transport_properties.WEBSOCKET_URL: comms_address
    })
    self.comms_address = comms_address
    self._websocket = None

  def is_open(self):
    """Returns True if websocket has been created and is not closed.

    Returns:
        bool: True if _websocket is not None
    """
    return hasattr(self, "_websocket") and self._websocket is not None

  def _open(self):
    """Opens or reopens the websocket connection using the current property values.

    Raises:
        Exception: if connection could not be established.
    """
    self._websocket = websocket.create_connection(
        self._properties[transport_properties.WEBSOCKET_URL],
        self._properties[transport_properties.CONNECT_TIMEOUT])

  def _close(self):
    """Closes the websocket connection."""
    self._websocket.close()
    self._websocket = None

  def _read(self, size=None, timeout=None):
    """Receives data from the websocket.

    Args:
        size (int): not used.
        timeout (float): maximum seconds to wait to read bytes or
          indefinitely if timeout=None. Default: None

    Returns:
        str: bytes read from transport
             or "" if no bytes were read
             or "" if an Exception occurred (including timeout)
    """
    self._websocket.settimeout(timeout)
    try:
      read_bytes = self._websocket.recv()
      return read_bytes
    except websocket.WebSocketTimeoutException:
      # Note: timeouts should not be logged. Otherwise, transport processes will flood
      # the logs with timeout exceptions (because they keep trying to read in infinite loop)
      return ""
    except Exception:
      logger.debug(
          "_read() from websocket with URL {} failed due to an error.".format(
              self._properties[transport_properties.WEBSOCKET_URL]))
      logger.debug(traceback.format_exc())
      return ""

  def _write(self, data, timeout=None):
    """Writes the data to the websocket.

    Args:
        data (str): bytes to be written out within timeout seconds
        timeout (float): maximum seconds to wait to write bytes or
          indefinitely if timeout=None. Default: None

    Returns:
        int: number of bytes written (0 if any Exception occurs, including
        timeout)
    """
    self._websocket.settimeout(timeout)
    try:
      bytes_sent = self._websocket.send(data)
      return bytes_sent
    except websocket.WebSocketTimeoutException:
      # Note: timeouts should not be logged. Otherwise, transport processes will flood
      # the logs with timeout exceptions (because they keep trying to read in infinite loop)
      return 0
    except Exception:
      logger.debug(
          "_write() to websocket with URL {} failed due to an error.".format(
              self._properties[transport_properties.WEBSOCKET_URL]))
      logger.debug(traceback.format_exc())
      return 0
