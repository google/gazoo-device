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

"""Classes and variables to share across usb_info modules."""
import inspect

ANDROID_NAMES = ("Android", "Pixel")
CAMBRIONIX_NAMES = ("FT230X Basic UART", "PS15-USB3")
CAMBRIONIX_VENDOR_PRODUCT_ID = ("0403/6015", "2cd9/0021")

CAMBRIONIX_PORT_MAP = {
    "PP8S": {
        "1.1": 1,
        "1.2": 2,
        "1.3": 3,
        "1.4": 4,
        "2.1": 8,
        "2.2": 7,
        "2.3": 6,
        "2.4": 5
    },
    "PP15S": {
        "1.1": 4,
        "1.2": 5,
        "1.3": 6,
        "1.4": 7,
        "2.1": 15,
        "2.2": 14,
        "2.3": 13,
        "2.4": 12,
        "3.1": 11,
        "3.2": 10,
        "3.3": 9,
        "3.4": 8,
        "4.2": 1,
        "4.3": 2,
        "4.4": 3
    },
    "PS15-USB3": {
        "1.1": 1,
        "1.2": 2,
        "1.3": 9,
        "1.4": 8,
        "2.1": 6,
        "2.2": 7,
        "2.3": 15,
        "2.4": 14,
        "3.1": 3,
        "3.2": 4,
        "3.3": 11,
        "3.4": 10,
        "4.1": 5,
        "4.3": 13,
        "4.4": 12
    },
    "U16S": {
        "2": 1,
        "5": 2,
        "4.1": 4,
        "4.2": 3,
        "4.3": 5,
        "4.4": 6,
        "4.5": 8,
        "4.6": 7,
        "4.7": 9,
        "7.1": 11,
        "7.2": 13,
        "7.3": 14,
        "7.4": 15,
        "7.5": 16,
        "7.6": 10,
        "7.7": 12
    }
}


class UsbInfo(object):
  """Class for storing all info about usb devices in a system agnostic way."""
  _address = None
  _child_addresses = []
  _ftdi_interface = 0
  _manufacturer = None
  _disk = None
  _product_id = None
  _product_name = None
  _serial_number = None
  _usb_hub_port = None
  _usb_hub_address = None
  _vendor_id = None

  def __init__(self, **kwargs):
    for key, value in kwargs.items():
      if not hasattr(self, key):
        raise ValueError("{} is not an arg. Choose from {}".format(
            key, self.get_properties()))
      setattr(self, "_" + key, value)

  def __repr__(self):
    a_dict = {}
    for attr in self.get_properties():
      a_dict[attr] = getattr(self, attr)
    return str(a_dict)

  @classmethod
  def get_properties(cls):
    """Returns all the public properties."""
    return [
        name for name, value in inspect.getmembers(cls)
        if isinstance(value, property) and not name.startswith("_")
    ]

  @property
  def address(self):
    """Address of device, persistent serial port path or adb serial."""
    return self._address

  @address.setter
  def address(self, a_string):
    self._address = a_string

  @property
  def child_addresses(self):
    """If cambrionix, list of addresses that are attached to cambrionix."""
    return self._child_addresses

  @child_addresses.setter
  def child_addresses(self, a_list):
    self._child_addresses = a_list

  @property
  def disk(self):
    """When volume is available, this is the disk link."""
    return self._disk

  @disk.setter
  def disk(self, a_string):
    self._disk = a_string

  @property
  def ftdi_interface(self):
    """Int 0 through 3 representing the ftdi interface."""
    return self._ftdi_interface

  @ftdi_interface.setter
  def ftdi_interface(self, a_number):
    self._ftdi_interface = a_number

  @property
  def manufacturer(self):
    """String that is the manufacturer's name."""
    return self._manufacturer

  @manufacturer.setter
  def manufacturer(self, a_string):
    self._manufacturer = a_string

  @property
  def product_id(self):
    """Product ID in 4 digit form. IE 1201."""
    return self._product_id

  @product_id.setter
  def product_id(self, a_string):
    self._product_id = a_string

  @property
  def product_name(self):
    """Product Name as a string.
    """
    return self._product_name

  @product_name.setter
  def product_name(self, a_string):
    self._product_name = a_string

  @property
  def serial_number(self):
    """Serial number of the connection.

    This could be an FTDI cable or a device.
    """
    return self._serial_number

  @serial_number.setter
  def serial_number(self, a_string):
    self._serial_number = a_string

  @property
  def usb_hub_port(self):
    """Number of the usb port the connection is on, if applicable."""
    return self._usb_hub_port

  @usb_hub_port.setter
  def usb_hub_port(self, a_number):
    self._usb_hub_port = a_number

  @property
  def usb_hub_address(self):
    """Number of the usb port the connection is on, if applicable."""
    return self._usb_hub_address

  @usb_hub_address.setter
  def usb_hub_address(self, a_string):
    self._usb_hub_address = a_string

  @property
  def vendor_id(self):
    """Product ID in 4 digit form. IE 1301."""
    return self._vendor_id

  @vendor_id.setter
  def vendor_id(self, a_string):
    self._vendor_id = a_string
