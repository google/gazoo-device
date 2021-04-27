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

"""Utility module for usb information."""
import re
import sys
from gazoo_device.utility import usb_config
from gazoo_device.utility import usb_info_linux
from gazoo_device.utility import usb_info_mac


def find_matching_connections(match_criteria):
  """Returns usb_info instances for connections that match criteria.

  Args:
      match_criteria (dict): dictionary of match criteria.

  Returns:
      list: list of UsbInfo instances that match criteria.

  Raises:
      ValueError: if match criteria contains bad key(s).

  Note:
    Connections first excluded and then included.
    If there is no include regex, all instances that dont match exclude_regex
    are included.

    Dictionary entry: {"<key>": {
                          "include_regex": "<regex>",
                          "exclude_regex": "<regex>""}
                      }
  """
  instances = get_address_to_usb_info_dict().values()
  allowed_keys = usb_config.UsbInfo.get_properties()
  bad_keys = [key for key in match_criteria.keys() if key not in allowed_keys]
  if bad_keys:
    raise ValueError("The keys {} are not allowed. Possible keys: {}".format(
        bad_keys, allowed_keys))
  for attr, entry in match_criteria.items():
    if entry.get("exclude_regex"):
      instances = [
          instance for instance in instances
          if not re.search(entry["exclude_regex"], str(getattr(instance, attr)))
      ]
    if entry.get("include_regex"):
      instances = [
          instance for instance in instances
          if re.search(entry["include_regex"], str(getattr(instance, attr)))
      ]
  return instances


def get_address_to_usb_info_dict():
  """Gets a dictionary of usb devices with all relevent information."""
  if sys.platform == "darwin":
    module = usb_info_mac
  else:
    module = usb_info_linux
  return module.get_address_to_usb_info_dict()


def get_all_serial_connections():
  """Returns a list of all serial connections."""
  usb_info = get_address_to_usb_info_dict()
  return [
      key for key, entry in usb_info.items()
      if entry.product_name not in usb_config.ANDROID_NAMES
  ]


def get_device_info(address):
  """Gets the usb info of a specific device.

  Args:
      address (str): serial path or adb serial.

  Returns:
      object: usb_info instance encoding information for that specific address.
  """
  address_to_info_dict = get_address_to_usb_info_dict()
  if address in address_to_info_dict:
    return address_to_info_dict[address]

  return usb_config.UsbInfo()


def get_vendor_number_from_path(address):
  """Returns the vendor number for the address provided.

  Args:
      address (str): address to find matching vendor id for.

  Raises:
      ValueError: if address not found.

  Returns:
      str: vendor number (e.g. "4012") from address.
  """
  usb_info_inst = get_device_info(address)
  return usb_info_inst.vendor_id


def get_ftdi_interface_from_path(address):
  """Returns the FTDI interface embedded in address provided.

  Args:
      address (str): Address to extract interface from.

  Raises:
      ValueError: if FTDI interface can't be obtained from address.

  Returns:
      str: Interface (e.g. "if02") from address.
  """
  usb_info_inst = get_device_info(address)
  return usb_info_inst.ftdi_interface


def get_product_name_from_path(address):
  """Returns the product name for address provided.

  Args:
      address (str): Address to extract FTDI name from.

  Raises:
      ValueError: if product name can't be obtained from address.

  Returns:
      str: product name from address.
  """
  usb_info_inst = get_device_info(address)
  return usb_info_inst.product_name


def get_other_ftdi_line(address, ftdi_interface):
  """Gets a path to the corresponding ftdi line for that address.

  Args:
     address (str): address for an ftdi based serial.
     ftdi_interface (int): number of the ftdi interface to switch to.

  Returns:
     str: address for other ftdi line.

  Raises:
      ValueError: if a matching ftdi line is not found.
  """
  serial_number = get_serial_number_from_path(address)
  devices = find_matching_connections({
      "serial_number": {
          "include_regex": serial_number
      },
      "ftdi_interface": {
          "include_regex": str(ftdi_interface)
      }
  })
  if devices:
    return devices[0].address
  raise ValueError("No connection found with {} and ftdi interface {}".format(
      serial_number, ftdi_interface))


def get_serial_number_from_path(address):
  """Returns the serial number embedded in address provided.

  Args:
      address (str): Address to extract serial number from.

  Raises:
      ValueError: if FTDI serial number can't be obtained from address.

  Returns:
      str: Serial number from address.
  """
  usb_info_inst = get_device_info(address)
  return usb_info_inst.serial_number


def get_usb_hub_info(device_address):
  """Gets the usb hub information for each communication address of the device.

  Args:
      device_address (str): communication address for device.

  Returns:
      dictionary: keys for usb hub name and port for usb connections.
  """
  usb_info = {}
  usb_info["device_usb_hub_name"] = get_usb_hub_address_from_address(
      device_address)
  usb_info["device_usb_port"] = get_usb_hub_port_from_address(device_address)
  return usb_info


def get_usb_hub_address_from_address(address):
  """Returns the communication address for usb hub the device is connected to.

  Args:
      address (str): communication address of device.

  Returns:
      str: communication address of the usb hub.
      None: if no associated usb hub.
  """
  usb_info_inst = get_device_info(address)
  return usb_info_inst.usb_hub_address


def get_usb_hub_address_from_serial_number(serial_number):
  """Returns the communication address for usb hub the device is connected to.

  Args:
      serial_number (str): device serial_number to associate with port number.

  Returns:
      str: communication address of the usb hub.
      None: if no associated usb hub.
  """
  devices = find_matching_connections(
      {"serial_number": {
          "include_regex": serial_number
      }})
  if devices:
    return devices[0].usb_hub_address
  return None


def get_usb_hub_port_from_address(address):
  """Returns the usb hub port number associated with an address.

  Args:
      address (str): communication Address to associate with port number.

  Returns:
      int: Port number of the usb hub the usb address is attached to.
      None: if no associated port.
  """
  usb_info_inst = get_device_info(address)
  return usb_info_inst.usb_hub_port


def get_usb_hub_port_from_serial_number(serial_number):
  """Returns the usb hub port number associated with an address.

  Args:
      serial_number (str): device serial_number to associate with port number.

  Returns:
      int: Port number of the usb hub the device is attached to.
      None: if no associated port.
  """
  devices = find_matching_connections(
      {"serial_number": {
          "include_regex": serial_number
      }})
  if devices:
    return devices[0].usb_hub_port
  return None
