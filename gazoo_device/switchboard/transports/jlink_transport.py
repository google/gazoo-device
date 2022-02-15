# Copyright 2022 Google LLC
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

"""J-Link transport class."""
import os.path
import sys

from gazoo_device import errors
from gazoo_device.switchboard.transports import transport_base
import intelhex
from pylink import enums
from pylink import jlink

DEFAULT_CHIP_NAME = "NRF52840_XXAA"
_JLINK_NO_DLL_ERROR = "Expected to be given a valid DLL."


class JLinkTransport(transport_base.TransportBase):
  """J-Link transport to a device."""

  def __init__(self,
               comms_address,
               chip_name=DEFAULT_CHIP_NAME,
               speed="auto",
               jlink_interface=enums.JLinkInterfaces.SWD,
               auto_reopen=True,
               open_on_start=True):
    """Initialize the J-Link transport.

    Args:
        comms_address (str): serial number of the J-Link adapter.
        chip_name (str): usually the name of the target chip to connect to.
        speed (object): connection speed, int or str.
                        Valid values: [5-12000], "auto", "adaptive".
        jlink_interface (int): interface to use. See
          pylink.enums.JLinkInterfaces.
        auto_reopen (bool): flag indicating transport should be reopened if
          unexpectedly closed.
        open_on_start (bool): flag indicating transport should be open on
          TransportProcess start.

    Raises:
        DeviceError: if the J-Link DLL (comes with the J-Link SDK) is
        missing.
        TypeError: J-Link instantiation failed.

    Note: due to license restrictions, J-Link DLL cannot be packaged into GDM.
    """
    super(JLinkTransport, self).__init__(
        auto_reopen=auto_reopen, open_on_start=open_on_start)
    self.comms_address = comms_address
    self._chip_name = chip_name
    self._speed = speed
    self._jlink_interface = jlink_interface

    try:
      self._jlink = jlink.JLink()
    except TypeError as e:
      if _JLINK_NO_DLL_ERROR in str(e):
        raise errors.DependencyUnavailableError(
            "No J-Link DLL found. Install the J-Link SDK from "
            "https://www.segger.com/downloads/jlink/#J-LinkSoftwareAndDocumentationPack. "
            f"Error: {e!r}.")
      else:
        raise

  def close(self):
    """Close the J-Link transport."""
    if hasattr(self, "_jlink") and self._jlink.opened():
      self._stop_rtt_logging()
      self._jlink.close()

  def flash(self, image_path):
    """Flash the hex image onto the device.

    Args:
        image_path (str): path to the image file to be flashed onto the device.
    """
    self._stop_rtt_logging()
    self._jlink.halt()

    image = intelhex.IntelHex(os.path.abspath(image_path))
    for segment_start, segment_end in image.segments():
      segment_size = segment_end - segment_start
      segment = image.tobinarray(start=segment_start, size=segment_size)
      self._jlink.flash_write8(segment_start, segment)

    self.reset()
    self._start_rtt_logging()

  def is_open(self):
    """Returns True if the J-Link library is open and transport is connected to the target.

    Returns:
        bool: True if transport is open, False otherwise.
    """
    return self._jlink.opened() and self._jlink.connected(
    ) and self._jlink.target_connected()

  def reset(self):
    """Reset the board by toggling the reset pin and restarting the CPU."""
    self._jlink.reset()
    self._jlink.restart()

  def _close(self):
    """Override abstract _close hook."""
    pass

  def _open(self):
    """Open the J-Link DLL and connect to the target."""
    self._jlink.open(serial_no=self.comms_address)
    self._jlink.set_tif(self._jlink_interface)
    self._jlink.connect(chip_name=self._chip_name, speed=self._speed)
    self._start_rtt_logging()

  def _read(self, size=1024, timeout=None):
    """Reads up to size bytes from the device RTT buffer.

    Args:
        size (int): maximum number of bytes to read.
        timeout (float): noop.

    Returns:
        bytes: bytes read from transport.
    """
    data = self._jlink.rtt_read(0, size)  # returns a list of int values (bytes)
    return b"".join(value.to_bytes(length=1, byteorder=sys.byteorder)
                    for value in data)

  def _start_rtt_logging(self):
    """Restart RTT logging."""
    self._jlink.rtt_start()

  def _stop_rtt_logging(self):
    """Stop RTT logging."""
    self._jlink.rtt_stop()

  def _write(self, data, timeout=None):
    """Writes the data provided into the device RTT buffer.

    Args:
        data (str): bytes to be written.
        timeout (float): noop.

    Returns:
        int: number of bytes written.
    """
    if isinstance(data, str):
      data = data.encode("utf-8", errors="replace")

    bytes_to_write = list(data)  # convert to list of int values
    return self._jlink.rtt_write(0, bytes_to_write)
