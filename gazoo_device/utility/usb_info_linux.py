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

"""Gets information on all usb connected devices.

Returns a dictionary mapping a persistent address (adb or serial port) to usb
info for that address.

Note: usb_info_linux primarily relies on pyudev for full information.
It processes just adb devices and those that show up in /dev/serial/by-id
"""
import dataclasses
import re
import sys
from typing import Dict, List, Optional, Tuple

from gazoo_device.utility import usb_config
import immutabledict
import pyudev

PERSISTENT_SERIAL_PATH_FOLDER = '/dev/serial/by-id'
MOUNTED_DISK_FOLDER = '/dev/disk/by-id'
ADB_SERIAL_REGEX = r'\/dev\/disk\/by-id\/usb-Linux_File-CD_Gadget_([\da-z]+)-0:0'
ANDROID_DEVICE_PRODUCT_NAME = 'File-CD Gadget'

# Type aliases
_AddressStr = str
_AddressUsbInfoDict = Dict[_AddressStr, usb_config.UsbInfo]
_DiskInfo = Dict[str, str]
_DevPathStr = str

################################################################################
# configuration example.1:
#     Host -> Cambrionix_USB2 -+-> Pixel
#                              +-> Another serial device
#
#     Cambrionix_USB2 dev path:
#         "/devices/pci0000:00/0000:00:14.0/usb1"
#         "/1-14/1-14.4/1-14.4.1/1-14.4.1:1.0/ttyUSB0/tty/ttyUSB0"
#     Pixel dev path (no "DEVLINKS"):
#         "/devices/pci0000:00/0000:00:14.0/usb1"
#         "/1-14/1-14.2/1-14.2.1"
#     Another serial device dev path (with "DEVLINKS"):
#         "/devices/pci0000:00/0000:00:14.0/usb1"
#         "/1-14/1-14.2/1-14.2.2/1-14.2.2.1"
#
#     _USB2_HUB_IDENTIFIER_REGEX below finds the Cambrionix hub identifier.
#     (1) finds between "/" just before "ttyUSB0" which is "1-14.4.1:1.0" above.
#     (2) strip N.N:N.N at end which becomes
#         the Cambrionix hub identifier: 1-14.
#     (3) replace the hub_identifier inside _IDENTIFIER_REGEX_TEMPLATE by 1-14.
#
#     _IDENTIFIER_REGEX_TEMPLATE below finds the two digits following
#     the hub identifier in their dev path as key to look up
#     the USB2 Cambrionix port table.
#     For Pixel from "1-14.2.1" port key is "2.1" which is port number 15
#     in USB2 table.
#     For Another serial device from "1-14.2.2" port key is "2.2" which is
#     port number 14 in USB2 table.
#
# configuration example.2: Daisy chain
#     Host -> Cambrionix_USB3 -> Cambrionix_USB2 -+-> Pixel
#                                                 +-> Another serial device
#
#     Cambrionix_USB3 dev path:
#         "/devices/pci0000:00/0000:00:14.0/usb1"
#         "/1-14/1-14.5/1-14.5:1.1/tty/ttyACM0"
#     Cambrionix_USB2 dev path:
#         "/devices/pci0000:00/0000:00:14.0/usb1"
#         "/1-14/1-14.2/1-14.2.2/1-14.2.2.4/1-14.2.2.4.1/1-14.2.2.4.1:1.0"
#         "/ttyUSB0/tty/ttyUSB0"
#     Pixel dev path (no "DEVLINKS"):
#         "/devices/pci0000:00/0000:00:14.0/usb1"
#         "/1-14/1-14.2/1-14.2.2/1-14.2.2.2/1-14.2.2.2.1"
#     Another serial device dev path (with "DEVLINKS"):
#         "/devices/pci0000:00/0000:00:14.0/usb1"
#         "/1-14/1-14.2/1-14.2.2/1-14.2.2.2/1-14.2.2.2.2/1-14.2.2.2.2.1"
#
#     NOTICE: Cambrionix_USB2, Pixel and Another serial device dev path
#             get longer than non daisy chain.
#
#     _USB3_HUB_IDENTIFIER_REGEX below finds the USB3 Cambrionix hub identifier
#     which is 1-14.
#     The detail is described at _USB3_HUB_IDENTIFIER_REGEX comment.
#
#     _IDENTIFIER_REGEX_TEMPLATE below finds the two digits:2.2 following
#     the hub identifier:1-14 in Cambrionix_USB2 dev path as key to look up
#     the USB3 Cambrionix port table. From "/1-14.2.2/" port key is "2.2"
#     which is port number 7 at USB3 table. It means that port 0 of
#     Cambrionix USB2 is connected to port 7 of Cambrionix USB3.
#
#     _USB2_HUB_IDENTIFIER_REGEX below finds the USB2 Cambrionix hub identifier.
#     (1) finds between "/" just before "ttyUSB0" which is "1-14.2.2.4.1:1.0"
#         above.
#     (2) strip N.N:N.N at end which becomes
#         the USB2 Cambrionix hub identifier: 1-14.2.2.
#         Notice it is longer than configuration example.1.
#     (3) replace the hub_identifier inside _IDENTIFIER_REGEX_TEMPLATE
#         by 1-14.2.2.
#
#     _IDENTIFIER_REGEX_TEMPLATE below finds the two digits following
#     the hub identifier in their dev path as key to look up
#     the USB2 Cambrionix port table.
#     For Pixel from"1-14.2.2.2.1" port key is "2.1" which is port number 15
#     in USB2 table.
#     For Another serial device from "1-14.2.2.2.2" port key is "2.2"
#     which is port number 14 in USB2 table.
################################################################################
_USB2_HUB_IDENTIFIER_REGEX = r'''
##########################################################################
# The regexes below search for the longest "N-N.N.N.N.N.N" sequence,
# which corresponds to the USB hierarchy/path.
# RE extracts variable length hub identifier from devpath, then
# it replaces part of _IDENTIFIER_REGEX_TEMPLATE.
##########################################################################
  /                                # start by '/'

  # find hub identifier: For example,
  # '1-14' at configuration example.1
  # '1-14.2.2' at configuration example.2 for daisy chained device.
  # This sequence gets longer when daisy chain gets longer.
  (?P<hub_id>\d-\d+(?:\.\d+)*)

  # followed by '.N.N:N.N/tty' for USB2. USB3 is one digit shorter.
  \.\d+\.\d+:\d+\.\d+/tty
'''

################################################################################
# configuration example.3:
#     Host -> Cambrionix_USB3 -+-> Pixel
#                              +-> Another serial device
#
#     Cambrionix_USB3 dev path:
#         "/devices/pci0000:00/0000:00:14.0/usb1"
#         "/1-14/1-14.5/1-14.5:1.1/tty/ttyACM0"
#     Pixel dev path (no "DEVLINKS"):
#         "/devices/pci0000:00/0000:00:14.0/usb1/1-14/1-14.2/1-14.2.3"
#     Another serial device dev path (with "DEVLINKS"):
#         "/devices/pci0000:00/0000:00:14.0/usb1/1-14/1-14.2/1-14.2.4"
#         "/1-14.2.4.1"
#
#     _USB3_HUB_IDENTIFIER_REGEX below finds the Cambrionix hub identifier.
#     (1) finds between "/" just before "tty" which is "1-14.5:1.1" above.
#         Notice one digit shorter than Cambrionix USB2.
#     (2) strip N:N.N at end which becomes the Cambrionix hub identifier: 1-14.
#         Notice one digit shorter than Cambrionix USB2.
#     (3) replace the hub_identifier inside _IDENTIFIER_REGEX_TEMPLATE by 1-14.
#
#     _IDENTIFIER_REGEX_TEMPLATE below finds the two digits following
#     the hub identifier in their dev path as key to look up
#     the USB3 Cambrionix port table.
#     For Pixel from "1-14.2.3" port key is "2.3" which is port number 15
#     in USB3 table.
#     For Another serial device from "1-14.2.4" port key is "2.4"
#     which is port number 14 in USB3 table.
#
# configuration example.4: Daisy chain
#     Host -> Cambrionix_USB2 -> Cambrionix_USB3 -+-> Pixel
#                                                 +-> Another serial device
#
#     Cambrionix_USB2 dev path:
#         "/devices/pci0000:00/0000:00:14.0/usb1"
#         "/1-14/1-14.4/1-14.4.1/1-14.4.1:1.0/ttyUSB0/tty/ttyUSB0"
#     Cambrionix_USB3 dev path:
#         "/devices/pci0000:00/0000:00:14.0/usb1"
#         "/1-14/1-14.1/1-14.1.4/1-14.1.4.5/1-14.1.4.5:1.1/tty/ttyACM0"
#     Pixel dev path (no "DEVLINKS"):
#         "/devices/pci0000:00/0000:00:14.0/usb1"
#         "/1-14/1-14.1/1-14.1.4/1-14.1.4.2/1-14.1.4.2.3"
#     Another serial device dev path (with "DEVLINKS"):
#         "/devices/pci0000:00/0000:00:14.0/usb1"
#         "/1-14/1-14.1/1-14.1.4/1-14.1.4.2/1-14.1.4.2.4/1-14.1.4.2.4.1"
#
#     NOTICE: Cambrionix_USB3, Pixel and Another serial device dev path
#             get longer than configuration example.3.
#
#     _USB2_HUB_IDENTIFIER_REGEX below finds the USB2 Cambrionix hub identifier
#     which is 1-14.
#     The detail is described at _USB2_HUB_IDENTIFIER_REGEX comment.
#
#     _IDENTIFIER_REGEX_TEMPLATE below finds the two digits:2.2 following
#     the hub identifier:1-14 in Cambrionix_USB3 dev path as key to look up
#     the USB2 Cambrionix port table. From "/1-14.1.4/" port key is "1.4"
#     which is port number 7 at USB2 table. It means that port 0 of
#     Cambrionix USB3 is connected to port 7 of Cambrionix USB2.
#
#     _USB3_HUB_IDENTIFIER_REGEX below finds the USB3 Cambrionix hub identifier.
#     (1) finds between "/" just before "tty" which is "1-14.1.4.5:1.1"
#         above.
#     (2) strip N:N.N at end which becomes
#         the USB3 Cambrionix hub identifier: 1-14.1.4.
#         Notice it is longer than configuration example.3.
#     (3) replace the hub_identifier inside _IDENTIFIER_REGEX_TEMPLATE
#         by 1-14.1.4.
#
#     _IDENTIFIER_REGEX_TEMPLATE below finds the two digits following
#     the hub identifier in their dev path as key to look up
#     the USB3 Cambrionix port table.
#     For Pixel from "1-14.1.4.2.3" port key is "2.3" which is port number 15
#     in USB3 table.
#     For Another serial device from "1-14.1.4.2.4" port key is "2.4"
#     which is port number 14 in USB3 table.
################################################################################
_USB3_HUB_IDENTIFIER_REGEX = r'''
##########################################################################
# The regexes below search for the longest "N-N.N.N.N.N.N" sequence,
# which corresponds to the USB hierarchy/path.
# RE extracts variable length hub identifier from devpath, then
# it replaces part of _IDENTIFIER_REGEX_TEMPLATE.
##########################################################################
  /                                # start by '/'

  # find hub identifier: For example,
  # '1-14' at configuration example.3
  # '1-14.1.4' at configuration example.4 for daisy chained device.
  # This sequence gets longer when daisy chain gets longer.
  (?P<hub_id>\d-\d+(?:\.\d+)*)

  # followed by '.N:N.N/tty' for USB3. USB2 is one digit longer.
  \.\d+:\d+\.\d+/tty
'''

# The purpose of _IDENTIFIER_REGEX_TEMPLATE is find the port key:N.N from
# child dev path. Two of these numbers (each 'N' above) can be used to
# look up the physical port number from CAMBRIONIX_PORT_MAP.
# The format is N.N appearing after hub_identifier.
# See the comment at _USB2_HUB_IDENTIFIER_REGEX and _USB3_HUB_IDENTIFIER_REGEX
# for the detail.
_IDENTIFIER_REGEX_TEMPLATE = r'''
  /                          # start by '/'
  {hub_identifier}           # this part is replaced before RE starts.
  \.                         # followed by '.'
  (?P<port_id>\d+\.\d+)      # N.N is a key to search CAMBRIONIX_PORT_MAP
  (?:/|$)                    # end by '/' or end of string.
'''


@dataclasses.dataclass(frozen=True)
class _UsbPathRegex:
  parent_hub_re: str
  child_template_re: str

_CAMBRIONIX_REGEX = immutabledict.immutabledict({
    'PP8S':
        _UsbPathRegex(_USB2_HUB_IDENTIFIER_REGEX,
                      _IDENTIFIER_REGEX_TEMPLATE),
    'PP15S':
        _UsbPathRegex(_USB2_HUB_IDENTIFIER_REGEX,
                      _IDENTIFIER_REGEX_TEMPLATE),
    'PS15-USB3':
        _UsbPathRegex(_USB3_HUB_IDENTIFIER_REGEX,
                      _IDENTIFIER_REGEX_TEMPLATE),
    'SuperSync15':
        _UsbPathRegex(_USB3_HUB_IDENTIFIER_REGEX,
                      _IDENTIFIER_REGEX_TEMPLATE),
    'U16S':
        _UsbPathRegex(_USB2_HUB_IDENTIFIER_REGEX,
                      _IDENTIFIER_REGEX_TEMPLATE),
})

# These vendor's mounted drives show up as multiple usb connections.
# We use the one with the symlink.
REPEAT_VENDORS = [
    'FTDI',
    'cambrionix',
    'Linux',
    'Android',
]


def get_address_to_usb_info_dict() -> _AddressUsbInfoDict:
  """Returns a dict of address to the usb information."""
  udev_devices = get_pyudev_list_of_devices()
  relevant_devices = [
      device for device in udev_devices
      if device.properties.get('ID_BUS') == 'usb'
  ]
  address_to_usb_info_dict = {}
  location_dict = {}
  model_dict = {}
  address_device_list = []
  for device in relevant_devices:
    address, entry, dev_path, model = _process_udev_device(device)
    if address:  # remove devices that don't have good addresses
      address_device_list.append((address, device))
      address_to_usb_info_dict[address] = entry
      if dev_path:
        location_dict[address] = dev_path
      if model:
        model_dict[address] = model
  disk_info = _get_disk_info()
  _add_disk_info(address_to_usb_info_dict, disk_info)
  _add_cambrionix_ports(address_to_usb_info_dict, location_dict, model_dict,
                        address_device_list)
  return address_to_usb_info_dict


def get_pyudev_list_of_devices(
    subsystem: Optional[str] = None,
    devtype: Optional[str] = None
) -> List[pyudev.Device]:
  """Wrapper around pyudev.list_devices.

  Args:
    subsystem: maps to pyudev.Context().list_devices arg.
    devtype: maps to pyudev.Context().list_devices arg DEVTYPE.

  Returns:
    a list of pyudev devices.

  Raises:
    RuntimeError: if platform is not linux.
  """
  args = {}
  if subsystem:
    args['subsystem'] = subsystem
  if devtype:
    args['DEVTYPE'] = devtype
  if sys.platform == 'darwin':
    raise RuntimeError('This method is only supported on linux.')
  context = pyudev.Context()
  return list(context.list_devices(**args))


def _add_cambrionix_ports(
    address_to_usb_info_dict: _AddressUsbInfoDict,
    location_dict: Dict[_AddressStr, _DevPathStr],
    model_dict: Dict[_AddressStr, str],
    address_device_list: List[tuple[_AddressStr, pyudev.Device]]
) -> None:
  """Add cambrionix port number and parent address to each cambrionix child.

  (1) add children address of connected devices to cambrionix hub device.
  (2) add cambrionix port number and parent address to each cambrionix child.

  Args:
    address_to_usb_info_dict: Dictionary to look up the entry by address.
    location_dict: Dictionary to look up the dev_path by address.
    model_dict: Dictionary to look up the model by address.
    address_device_list: List of address and udev_device used to
        fill out child_addresses of Cambrionix hub device.
  """
  for address, udev_device in address_device_list:
    entry = address_to_usb_info_dict[address]
    if entry.product_name in usb_config.CAMBRIONIX_NAMES:
      entry.child_addresses = _get_child_addresses(udev_device,
                                                   address_to_usb_info_dict)
  for hub_address, model in model_dict.items():
    for child_address in address_to_usb_info_dict[hub_address].child_addresses:
      if child_address in address_to_usb_info_dict:
        child_entry = address_to_usb_info_dict[child_address]
        child_entry.usb_hub_address = hub_address
        child_entry.usb_hub_port = _get_cambrionix_port_number(
            hub_address, model, child_address, location_dict)


def _add_disk_info(
    address_to_usb_info_dict: _AddressUsbInfoDict,
    disk_info: _DiskInfo
) -> None:
  """Add disk path to the entries that have them.

  Args:
      address_to_usb_info_dict: Dictionary to look up the entry by address.
      disk_info: disk info
  """
  for entry in address_to_usb_info_dict.values():
    serial = entry.serial_number
    if serial in disk_info:
      entry.disk = disk_info[serial]


def _get_address(udev_device: pyudev.Device) -> str:
  """Gets the serial port symlink under '/dev/serial/by-id', mounted drives, or adb serial.

  Args:
      udev_device: udev device.

  Returns:
      the serial port symlink under '/dev/serial/by-id', mounted drives,
          or adb serial.
          if symlink is not found and is not known path, return ''.
  """
  devlinks_str = udev_device.properties.get('DEVLINKS', '')
  paths = devlinks_str.split()
  if not devlinks_str:  # Get mounted drives without corresponding symlinks
    if udev_device.properties.get('ID_VENDOR') not in REPEAT_VENDORS:
      return udev_device.properties.get('DEVNAME')

  for path in paths:
    if PERSISTENT_SERIAL_PATH_FOLDER in path:
      return path
    if MOUNTED_DISK_FOLDER in path:
      match = re.match(ADB_SERIAL_REGEX, path)
      if match:
        return match.group(1)
      return path

  return ''


def _get_cambrionix_model(udev_device: pyudev.Device) -> str:
  """Gets the model of the cambrionix.

  Args:
      udev_device: udev device.

  Returns:
      the model of the cambrionix
  """
  parent = udev_device.parent.parent.parent.parent
  if udev_device.properties.get('ID_MODEL') in usb_config.CAMBRIONIX_PORT_MAP:
    return udev_device.properties.get('ID_MODEL')
  else:
    return parent.properties.get('ID_MODEL')


def _get_cambrionix_port_number(
    hub_address: _AddressStr,
    hub_model: str,
    child_address: _AddressStr,
    location_dict: Dict[_AddressStr, _DevPathStr]
) -> Optional[int]:
  """Get port number from dev path.

  Args:
    hub_address: Address for the parent Cambrionix hub.
    hub_model: Model for the parent Cambrionix hub.
    child_address: Address for a child device connected to the hub.
    location_dict: Dictionary to look up the dev_path by address.

  Returns:
    Port number or None if not found.

  Note:
    The port number is determined by first finding the Cambionix (or parent)
    identifier. The parent identifier can vary in length, but is found using
    the hub dev path by looking between the '/' and the last one or two digits
    (depending on hub model) before the ':' ("/<parent_identifier>n.n:n.n").
    For children, the two digits following the parent identifier in their
    dev path are used to look up the Cambrionix port.

    Example:
      hub dev path:
        "/devices/pci0000:00/0000:00:14.0/usb1/1-4/1-4.1/1-4.1.2/1-4.1.2.4/"
        "1-4.1.2.4.1/1-4.1.2.4.1:1.0/ttyUSB4/tty/ttyUSB4"
      From the hub dev path "1-4.1.2.4.1:1.0" is used to find that the parent
      identifier is "1-4.1.2".
      child dev path:
        "/devices/pci0000:00/0000:00:14.0/usb1/1-4/1-4.1/1-4.1.2/1-4.1.2.3/"
        "1-4.1.2.3.4/1-4.1.2.3.4:1.2/ttyUSB2/tty/ttyUSB2"
          "1-4.1.2.3.4:1.2" is the relevant number.
          "1-4.1.2" is the parent identifier.
          "3.4" is the child identifier used to look up the port number.
          "1.2" indicates the FTDI interface.
      child dev path (hub device):
        "/devices/pci0000:00/0000:00:14.0/usb1/1-4/1-4.1/1-4.1.2/1-4.1.2.4/"
        "1-4.1.2.4.2/1-4.1.2.4.2.1/1-4.1.2.4.2.1:1.0/tty/ttyACM1"
          "1-4.1.2.4.2.1:1.0" is the relevant number.
          "1-4.1.2" is the parent identifier.
          "4.2" is the child identifier used to look up the port number.
          "1:" is the hub device identifier
          "1.0" indicates the FTDI interface.
  """
############################################################################
#
# Port finding flow:
#
# Model
#   |
#   |
#   +---> _CAMBRIONIX_REGEX dict
#   |        |
#   |        |                              search hub identifier
#   |        +---> parent_hub_re -----------------------+
#   |        |                                          |
#   |        |                                          V
#   |        |                       hub dev path "...<hub>............"
#   |        |                                          |
#   |        |                                          V
#   |        |          +-------------------------------+
#   |        |          |
#   |        |          |
#   |        |          | insert into child_template_re
#   |        |          |
#   |        |          |
#   |        V          V                              search child identifier
#   |        +---> child_template_re ------------------------------+
#   |                                                              |
#   |                                                              V
#   |                                child dev path "..<hub>...<child>......"
#   |                                                              |
#   V                                                              V
#   +--------+-----------------------------------------------------+
#            |
#            V
#     CAMBRIONIX_PORT_MAP
#            |
#            V
#        port number
#
############################################################################
  hub_id_regex = _CAMBRIONIX_REGEX[hub_model].parent_hub_re
  hub_match = re.search(hub_id_regex, location_dict[hub_address], re.VERBOSE)
  if hub_match:
    parent_hub_identifier = hub_match.group('hub_id').replace('.', r'\.')
    template_re = _CAMBRIONIX_REGEX[hub_model].child_template_re
    identifier_regex = template_re.format(hub_identifier=parent_hub_identifier)
    port_match = re.search(identifier_regex, location_dict[child_address],
                           re.VERBOSE)
    if port_match:
      port_mapping = usb_config.CAMBRIONIX_PORT_MAP[hub_model]
      return port_mapping.get(port_match.group('port_id'))  # port number
  return None


def _get_child_addresses(
    udev_device: pyudev.Device,
    address_to_usb_info_dict: _AddressUsbInfoDict
) -> List[_AddressStr]:
  """Get the addresses for the relevant children of the udev device.

  Args:
      udev_device: udev device of Cambrionix hub
      address_to_usb_info_dict: dictionary of address to UsbInfo instance
          for each usb device attached.

  Returns:
      a list of the addresses for the relevant children of
          the udev device.
  """
  all_children_devices = _get_cambrionix_udev_children(udev_device)
  relevant_children_devices = [
      child_device for child_device in all_children_devices
      if child_device != udev_device and
      _get_address(child_device) in address_to_usb_info_dict
  ]
  grand_children_devices = []
  for child_device in relevant_children_devices:
    # Remove children of other cambrionixes
    if _get_product_name(child_device) in usb_config.CAMBRIONIX_NAMES:
      grand_children_devices += _get_cambrionix_udev_children(child_device)
      grand_children_devices.remove(child_device)
  return [
      _get_address(child_device)
      for child_device in relevant_children_devices
      if child_device not in grand_children_devices
  ]


def _get_disk_info() -> Dict[str, str]:
  """Returns a dictionary of disk paths to serial numbers."""
  devices = get_pyudev_list_of_devices(subsystem='block')
  mounted_info = {
      device.properties.get('ID_SERIAL_SHORT', ''):
          device.properties.get('DEVNAME')
      for device in devices
  }
  return mounted_info


def _get_product_name(udev_device: pyudev.Device) -> str:
  """Returns the product name in a system agnostic way.

  Args:
      udev_device: udev device.
  """
  model = udev_device.properties.get('ID_MODEL', '').replace('_', ' ')
  if model == ANDROID_DEVICE_PRODUCT_NAME:  # Actually an Android device.
    model = 'Android'
  return model


def _process_udev_device(
    udev_device: pyudev.Device
) -> Tuple[_AddressStr, usb_config.UsbInfo, _DevPathStr, str]:
  """Get (address, UsbInfo, dev_path, model) from udev_device.

  Args:
      udev_device: udev device.

  Returns:
      tuple: (address, UsbInfo, dev_path, model)
      If address is invalid, return ('', UsbInfo, '', '') and
      the caller should ignore the returned tupple.
  """
  model = ''
  dev_path = udev_device.properties.get('DEVPATH', '')

  entry = usb_config.UsbInfo()
  address = _get_address(udev_device)
  if not address:
    return '', entry, '', ''
  entry.address = address
  entry.product_id = udev_device.properties.get('ID_MODEL_ID', '')
  entry.vendor_id = udev_device.properties.get('ID_VENDOR_ID', '')
  entry.ftdi_interface = int(
      udev_device.properties.get('ID_USB_INTERFACE_NUM', 0))
  entry.manufacturer = udev_device.properties.get('ID_VENDOR', '')
  entry.serial_number = udev_device.properties.get('ID_SERIAL_SHORT', '')
  entry.product_name = _get_product_name(udev_device)
  if entry.product_name in usb_config.CAMBRIONIX_NAMES:
    model = _get_cambrionix_model(udev_device)
  return address, entry, dev_path, model


def _get_cambrionix_udev_children(
    udev_device: pyudev.Device
) -> List[pyudev.Device]:
  """Gets all the udev devices representing a cambrionix's children.

  Args:
      udev_device: Cambrionix hub device.

  Returns:
      list of all the udev devices representing a cambrionix's children.

  Raises:
      NotImplementedError: if product name is not known.
  """
  product_name = _get_product_name(udev_device)
  if product_name in usb_config.CAMBRIONIX_NAMES_USB2:
    return list(udev_device.parent.parent.parent.parent.parent.children)
  if product_name in usb_config.CAMBRIONIX_NAMES_USB3:
    return list(udev_device.parent.parent.parent.parent.children)
  raise NotImplementedError(
      f'Unknown product name: {product_name} is found.')
