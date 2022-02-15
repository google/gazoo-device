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
import re
import sys

from gazoo_device.utility import usb_config
import pyudev


PERSISTENT_SERIAL_PATH_FOLDER = '/dev/serial/by-id'
MOUNTED_DISK_FOLDER = '/dev/disk/by-id'
ADB_SERIAL_REGEX = r'\/dev\/disk\/by-id\/usb-Linux_File-CD_Gadget_([\da-z]+)-0:0'
HUB_IDENTIFIER_REGEX = r'\d-\d(?:\.\d?)+/(\d-(?:\d\.)+)\d\.\d:\d\.\d'
USB3_HUB_IDENTIFIER_REGEX = r'\d-\d(?:\.\d?)+/(\d-(?:\d\.)+)\d:\d\.\d'
IDENTIFIER_REGEX_TEMPLATE = r'\d-\d(?:\.\d?)+/{hub}(\d\.\d)(?:\.\d)*:\d\.\d'
ANDROID_DEVICE_PRODUCT_NAME = 'File-CD Gadget'

# These vendor's mounted drives show up as multiple usb connections.
# We use the one with the symlink.
REPEAT_VENDORS = [
    'FTDI',
    'cambrionix',
    'Linux',
    'Android',
]


def get_address_to_usb_info_dict():
  """Returns a dict of address to the usb information.

  Returns:
     dict: dictionary of address to UsbInfo instance for each usb device
     attached.
  """
  udev_devices = get_pyudev_list_of_devices()
  relevant_devices = [
      device for device in udev_devices
      if device.properties.get('ID_BUS') == 'usb'
  ]
  address_to_usb_info_dict = {}
  location_dict = {}
  model_dict = {}
  for device in relevant_devices:
    address, entry, dev_path, model = _process_udev_device(device)
    if address:  # remove devices that don't have good addresses
      address_to_usb_info_dict[address] = entry
      if dev_path:
        location_dict[address] = dev_path
      if model:
        model_dict[address] = model
  disk_info = _get_disk_info()
  _add_disk_info(address_to_usb_info_dict, disk_info)
  _add_cambrionix_ports(address_to_usb_info_dict, location_dict, model_dict)
  return address_to_usb_info_dict


def get_pyudev_list_of_devices(subsystem=None, devtype=None):
  """Wrapper around pyudev.list_devices.

  Args:
    subsystem (str): maps to pyudev.Context().list_devices arg.
    devtype (str): maps to pyudev.Context().list_devices arg DEVTYPE.

  Returns:
    list: a list of pyudev devices.

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


def _add_cambrionix_ports(address_to_usb_info_dict, location_dict, model_dict):
  """Add cambrionix port number and parent address to each cambrionix child."""
  for hub_address, model in model_dict.items():
    for child_address in address_to_usb_info_dict[hub_address].child_addresses:
      if child_address in address_to_usb_info_dict:
        child_entry = address_to_usb_info_dict[child_address]
        child_entry.usb_hub_address = hub_address
        child_entry.usb_hub_port = _get_cambrionix_port_number(
            hub_address, model, child_address, location_dict)


def _add_disk_info(address_to_usb_info_dict, disk_info):
  """Add disk path to the entries that have them."""
  for entry in address_to_usb_info_dict.values():
    serial = entry.serial_number
    if serial in disk_info:
      entry.disk = disk_info[serial]


def _get_address(udev_device):
  """Gets the serial port symlink under '/dev/serial/by-id', mounted drives, or adb serial."""
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


def _get_cambrionix_model(udev_device):
  """Gets the model of the cambrionix."""
  parent = udev_device.parent.parent.parent.parent
  if udev_device.properties.get('ID_MODEL') in usb_config.CAMBRIONIX_PORT_MAP:
    return udev_device.properties.get('ID_MODEL')
  else:
    return parent.properties.get('ID_MODEL')


def _get_cambrionix_port_number(hub_address,
                                hub_model,
                                child_address,
                                location_dict):
  """Get port from dev path.

  Args:
    hub_address (str): Address for the Cambrionix hub.
    hub_model (str): Model for the Cambrionix hub.
    child_address (str): Address for a child device connected to the hub.
    location_dict (dict): Dictionary to look up the dev_path by address.

  Returns:
    int: Port number or None if not found.

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
  if 'USB3' in hub_model:
    hub_id_regex = USB3_HUB_IDENTIFIER_REGEX
  else:
    hub_id_regex = HUB_IDENTIFIER_REGEX
  hub_match = re.search(hub_id_regex, location_dict[hub_address])
  if hub_match:
    parent_identifier = hub_match.group(1).replace('.', r'\.')
    identifier_regex = IDENTIFIER_REGEX_TEMPLATE.format(hub=parent_identifier)
    match = re.search(identifier_regex, location_dict[child_address])
    if match:
      port_mapping = usb_config.CAMBRIONIX_PORT_MAP[hub_model]
      return port_mapping.get(match.group(1))
  return None


def _get_child_addresses(udev_device):
  """Get the addresses for the relevant children of the udev device."""
  all_children = _get_cambrionix_udev_children(udev_device)
  relevant_children = [
      device for device in all_children
      if device.properties.get('DEVLINKS') and _get_address(device)
  ]
  if udev_device in relevant_children:
    relevant_children.remove(udev_device)
  grand_children = []
  for child_device in relevant_children:
    # Remove children of other cambrionixes
    if _get_product_name(child_device) in usb_config.CAMBRIONIX_NAMES:
      grand_children += _get_cambrionix_udev_children(child_device)
      grand_children.remove(child_device)
  return [
      _get_address(child)
      for child in relevant_children
      if child not in grand_children
  ]


def _get_disk_info():
  """Returns a dictionary of disk paths to serial numbers."""
  devices = get_pyudev_list_of_devices(subsystem='block')
  mounted_info = {
      device.properties.get('ID_SERIAL_SHORT', ''):
          device.properties.get('DEVNAME')
      for device in devices
  }
  return mounted_info


def _get_product_name(udev_device):
  """Gets the product name in a system agnostic way."""
  model = udev_device.properties.get('ID_MODEL', '').replace('_', ' ')
  if model == ANDROID_DEVICE_PRODUCT_NAME:  # Actually an Android device.
    model = 'Android'
  return model


def _process_udev_device(udev_device):
  """Convert pyudev dict to the system agnostic form."""
  model = None
  dev_path = udev_device.properties.get('DEVPATH', '')

  entry = usb_config.UsbInfo()
  address = _get_address(udev_device)
  if not address:
    return '', {}, None, None
  entry.address = address
  entry.product_id = udev_device.properties.get('ID_MODEL_ID', '')
  entry.vendor_id = udev_device.properties.get('ID_VENDOR_ID', '')
  entry.ftdi_interface = int(
      udev_device.properties.get('ID_USB_INTERFACE_NUM', 0))
  entry.manufacturer = udev_device.properties.get('ID_VENDOR', '')
  entry.serial_number = udev_device.properties.get('ID_SERIAL_SHORT', '')
  entry.product_name = _get_product_name(udev_device)
  if entry.product_name in usb_config.CAMBRIONIX_NAMES:
    entry.child_addresses = _get_child_addresses(udev_device)
    model = _get_cambrionix_model(udev_device)
  return address, entry, dev_path, model


def _get_cambrionix_udev_children(udev_device):
  """Gets all the udev devices representing a cambrionix's children."""
  return list(udev_device.parent.parent.parent.parent.parent.children)
