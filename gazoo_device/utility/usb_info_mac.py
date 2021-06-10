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

"""Gets information on all usb connected devices.


Returns a dictionary mapping a persistent address (adb or serial port) to usb
info for that address.

Note: usb_info_mac primarily relies on system_profile for full information.
"""
import copy
import json
import os
import subprocess
from typing import Dict, List, Any, Optional
from gazoo_device import gdm_logger
from gazoo_device.utility import usb_config
from serial.tools import list_ports

_DeviceDictType = Dict[str, Any]
_UsbInfoDict = Dict[str, usb_config.UsbInfo]
logger = gdm_logger.get_logger()

PROFILER_USB_DATA_TYPE = 'SPUSBDataType'
MAC_COMMAND = ['system_profiler', PROFILER_USB_DATA_TYPE, '-json']


def get_address_to_usb_info_dict():
  """Returns a standard address to usb info dict for mac.

  Returns:
      dict: of address to UsbInfo instance.

  Raises:
      RuntimeError: if system_profiler does not produce the correct output.
  """
  with open(os.devnull, 'w') as devnull:
    output = subprocess.check_output(MAC_COMMAND, stderr=devnull)
  output_dict = json.loads(output)
  usb_connections = output_dict[PROFILER_USB_DATA_TYPE]
  usb_info_dict = {}
  _convert_system_profiler_dict(usb_connections, usb_info_dict)
  return usb_info_dict


def _convert_system_profiler_dict(
    device_dicts: List[_DeviceDictType],
    converted_dicts: _UsbInfoDict,
    port_mapping: Optional[Dict[str, int]] = None,
    parent_device_dict: Optional[Dict[str, str]] = None) -> None:
  """Convert system profiler dict to the system agnostic form.

  Recursively walks the tree of connected USB devices.

  Args:
      device_dicts: dictionaries from system_profiler to convert to a
        generic form.
      converted_dicts: converted dictionaries will be stored here.
      port_mapping: mapping from USB device number (str) to Cambrionix
        port number (int).
      parent_device_dict: dictionary of parent hub (Cambrionix).
  """
  for device_dict in device_dicts:
    if (device_dict.get('manufacturer') == 'cambrionix' and
        device_dict.get('_name') in usb_config.CAMBRIONIX_PORT_MAP and
        _get_vendor_product_id(device_dict) not in
        usb_config.CAMBRIONIX_VENDOR_PRODUCT_ID):
      children = _create_device_entries_for_cambrionix(device_dict,
                                                       device_dict['_name'])
      converted_dicts.update(children)
    else:
      if 'serial_num' in device_dict:
        entry = _create_device_entry(
            device_dict, port_mapping, parent_device_dict)
        converted_dicts.update(entry)
      _convert_system_profiler_dict(
          device_dict.get('_items', []),
          converted_dicts,
          port_mapping,
          parent_device_dict)


def _add_child_addresses(children_dicts):
  """Add child addresses to cambrionix entry and cambrionix to children."""
  child_addresses = list(children_dicts.keys())
  cambrionix_address = [
      key for key, value in children_dicts.items()
      if value.product_name in usb_config.CAMBRIONIX_NAMES
  ][0]
  children_dicts[cambrionix_address].child_addresses = child_addresses
  for address in child_addresses:
    if address != cambrionix_address:
      children_dicts[address].usb_hub_address = cambrionix_address


def _create_device_entries_for_cambrionix(device_dict, cambrionix_model):
  """Converts device dict for cambrionix into individual entries for children."""
  port_mapping = usb_config.CAMBRIONIX_PORT_MAP[cambrionix_model]
  children_dicts = {}
  # Typically the entries are in a _items list, however at least for the
  # PS15-USB3 hub the cambrionix device is directly in the 'entry'
  for entry in device_dict.get('_items', []):
    if '_items' in entry:
      entry_device_dict = entry.get('_items')
    else:
      entry_device_dict = [entry]
    _convert_system_profiler_dict(
        entry_device_dict,
        children_dicts,
        port_mapping,
        device_dict)
  if children_dicts:
    _add_child_addresses(children_dicts)
  return children_dicts


def _create_device_entry(
    device_dict: _DeviceDictType,
    port_mapping: Optional[Dict[str, int]] = None,
    parent_device_dict: Optional[_DeviceDictType] = None) -> _UsbInfoDict:
  """Creates a standard usb_info entry for a device.

  Args:
   device_dict: device info from system profiler.
   port_mapping: map of port identifiers to port numbers.
   parent_device_dict: dictionary of parent hub (Cambrionix).

  Returns:
    dict: UsbInfo dictionary entries stored by address as the key.
  """
  return_dict = {}
  usb_entry = usb_config.UsbInfo()
  usb_entry.serial_number = device_dict['serial_num']
  usb_entry.manufacturer = device_dict.get('manufacturer', '')  # can be empty
  usb_entry.product_id = _get_product_id(device_dict)
  usb_entry.vendor_id = _get_vendor_id(device_dict)
  # Product names are reported inconsistently between gLinuxes and Macs; either
  # undescores or spaces are used. Convert all underscores to spaces as a
  # workaround.
  usb_entry.product_name = device_dict['_name'].replace('_', ' ')
  usb_entry.usb_hub_port = _get_port_number(
      device_dict, port_mapping, parent_device_dict)
  address = _get_entry_address(usb_entry.serial_number)
  if 'Media' in device_dict:  # mounted device

    if 'volumes' in device_dict['Media'][0]:
      volume = device_dict['Media'][0]['volumes'][0]
      address = '/dev/' + volume['bsd_name']
      usb_entry.disk = address
  if usb_entry.product_name in usb_config.ANDROID_NAMES:
    usb_entry.address = usb_entry.serial_number  # android serial
    return_dict[usb_entry.address] = usb_entry
  else:
    usb_entry.address = address
    if os.path.exists(usb_entry.address):
      return_dict[usb_entry.address] = usb_entry
  return return_dict


def _get_entry_address(device_serial: str) -> str:
  """Returns serial port path given device serial number."""
  comports = list_ports.comports()
  for com_port in comports:
    if com_port.serial_number == device_serial:
      return com_port.device.replace('/cu.', '/tty.')
  return ''


def _get_product_id(device_dict):
  """Converts 0x1234 to 1234."""
  return device_dict['product_id'].split('x')[-1]


def _get_vendor_id(device_dict):
  """Converts '0x1234 Serial Interational' to 1234."""
  return device_dict['vendor_id'].split()[0].split('x')[-1]


def _get_vendor_product_id(device_dict):
  """Returns a string with '<vendor_id>/<product_id>'."""
  return f'{_get_vendor_id(device_dict)}/{_get_product_id(device_dict)}'


def _get_port_number(
    device_dict: _DeviceDictType,
    port_mapping: Optional[Dict[str, int]] = None,
    parent_device_dict: Optional[_DeviceDictType] = None) -> Optional[int]:
  """Last two digits correspond to the port number.

  Args:
    device_dict: device info from system profiler.
    port_mapping: map of port identifiers to port numbers.
    parent_device_dict: dictionary of parent hub (Cambrionix).

  Returns:
     int: port number or None if no cambrionix port applicable..

  Examples:
      "0x14443000 / 10" -> port identifier is "43" -> port 5 on PP15S.
      "0x14313400" -> port identifier is "34" -> port 8 on PP15S.
  """
  if not port_mapping:  # not connected to a usb hub
    return None
  if is_cambrionix(device_dict):
    return None
  if parent_device_dict:
    index = _get_cambrionix_port_using_parent_hub(
        device_dict, parent_device_dict)
  else:
    # get the appropriate digits
    stripped_location_id = _rstrip_location_id(device_dict)
    index = '{}.{}'.format(stripped_location_id[-2], stripped_location_id[-1])
  port = port_mapping[index]
  return port


def _get_cambrionix_port_using_parent_hub(
    device_dict: _DeviceDictType,
    parent_device_dict: _DeviceDictType) -> str:
  """Returns device Cambrionix port using the parent (Cambrionix) dict.

  Args:
    device_dict: device info from system profiler.
    parent_device_dict: dictionary of parent hub (Cambrionix).

  Returns:
     str: Cambrionix port number in port_map dict format.

  Examples:
     Device:                       Location ID:
     Cambrionix                  = 0x146  <--- length = 5
     Child Cambrionix Hub        = 0x1464  <--- length = 6
                                        ^--- location_id[5]
     Child Device                = 0x14642
                                        ^--- (4.2 = port 1)
     Generic Hub                 = 0x14643
                                        ^--- (4.3 = port 2)
     Child Device of Generic Hub = 0x146431
                                        ^--- (4.3 = port 2)
  """
  first_loc_id_idx = len(_rstrip_location_id(parent_device_dict))
  second_loc_id_idx = first_loc_id_idx + 1
  device_loc_id = _rstrip_location_id(device_dict)
  return '{}.{}'.format(device_loc_id[first_loc_id_idx],
                        device_loc_id[second_loc_id_idx])


def is_cambrionix(device_dict):
  """Device dict is a cambrionix entry."""
  return device_dict.get('_name') in usb_config.CAMBRIONIX_NAMES


def _rstrip_location_id(device_dict):
  """Strips location_id down to base hex value with no trailing zeroes."""
  return device_dict['location_id'].split()[0].rstrip('0')
