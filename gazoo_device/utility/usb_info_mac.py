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

"""Gets information on all usb connected devices.


Returns a dictionary mapping a persistent address (adb or serial port) to usb info
for that address.

Note: usb_info_mac primarily relies on system_profile for full information.
"""
import json
import os
import subprocess
from gazoo_device import gdm_logger
from gazoo_device.utility import usb_config

logger = gdm_logger.get_gdm_logger()

PROFILER_USB_DATA_TYPE = 'SPUSBDataType'
MAC_COMMAND = ['system_profiler', PROFILER_USB_DATA_TYPE, '-json']
FTDI = 'FTDI'
SERIAL_PATH_TEMPLATE = '/dev/tty.usbserial-{serial_num}{ftdi_line}'


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


def _convert_system_profiler_dict(device_dicts, converted_dicts, port_mapping=None):
    """Convert system profiler dict to the system agnostic form.

    Recursively walks the tree of connected USB devices.

    Args:
        device_dicts (list): dictionaries from system_profiler to convert to a generic form.
        converted_dicts (dict): converted dictionaries will be stored here.
        port_mapping (dict): mapping from USB device number (str) to Cambrionix port number (int).
    """
    for device_dict in device_dicts:
        if device_dict.get('manufacturer') == 'cambrionix':
            children = _create_device_entries_for_cambrionix(device_dict, device_dict['_name'])
            converted_dicts.update(children)
        else:
            if 'serial_num' in device_dict:
                entry = _create_device_entry(device_dict, port_mapping)
                converted_dicts.update(entry)
            _convert_system_profiler_dict(device_dict.get("_items", []),
                                          converted_dicts,
                                          port_mapping)


def _add_child_addresses(children_dicts):
    """Add child addresses to cambrionix entry and cambrionix to children."""
    child_addresses = list(children_dicts.keys())
    cambrionix_address = [key for key, value in children_dicts.items()
                          if value.product_name == usb_config.CAMBRIONIX_NAME][0]
    children_dicts[cambrionix_address].child_addresses = child_addresses
    for address in child_addresses:
        if address != cambrionix_address:
            children_dicts[address].usb_hub_address = cambrionix_address


def _create_device_entries_for_cambrionix(device_dict, cambrionix_model):
    """Converts device dict for cambrionix into individual entries for children."""
    port_mapping = usb_config.CAMBRIONIX_PORT_MAP[cambrionix_model]
    children_dicts = {}
    for entry in device_dict['_items']:
        _convert_system_profiler_dict(entry.get('_items', []),
                                      children_dicts,
                                      port_mapping)
    _add_child_addresses(children_dicts)
    return children_dicts


def _create_device_entry(device_dict, port_mapping=None):
    """Creates a standard usb_info entry for a device."""
    return_dict = {}
    address = SERIAL_PATH_TEMPLATE.format(serial_num=device_dict['serial_num'], ftdi_line='')
    usb_entry = usb_config.UsbInfo()
    usb_entry.serial_number = device_dict['serial_num']
    usb_entry.manufacturer = device_dict['manufacturer']
    usb_entry.product_id = _get_product_id(device_dict)
    usb_entry.vendor_id = _get_vendor_id(device_dict)
    # Product names are reported inconsistently between gLinuxes and Macs; either undescores or
    # spaces are used. Convert all underscores to spaces as a workaround.
    usb_entry.product_name = device_dict['_name'].replace("_", " ")
    usb_entry.usb_hub_port = _get_port_number(device_dict, port_mapping)
    if 'Media' in device_dict:  # mounted device

        if 'volumes' in device_dict['Media'][0]:
            volume = device_dict['Media'][0]['volumes'][0]
            address = '/dev/' + volume["bsd_name"]
            usb_entry.disk = address
    if usb_entry.product_name in usb_config.ANDROID_NAMES:
        usb_entry.address = usb_entry.serial_number  # android serial
        return_dict[usb_entry.address] = usb_entry
    else:
        usb_entry.address = address
        if os.path.exists(usb_entry.address):
            return_dict[usb_entry.address] = usb_entry
    return return_dict


def _get_product_id(device_dict):
    """Converts 0x1234 to 1234."""
    return device_dict['product_id'].split('x')[-1]


def _get_vendor_id(device_dict):
    """Converts '0x1234 Serial Interational' to 1234."""
    return device_dict['vendor_id'].split()[0].split('x')[-1]


def _get_port_number(device_dict, port_mapping=None):
    """Last two digits correspond to the port number.

    Args:
      device_dict (dict): device info from system profiler.
      port_mapping (dict): map of port identifiers to port numbers.

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
    # get the appropriate digits
    stripped_location_id = device_dict['location_id'].split()[0].rstrip("0")
    index = "{}.{}".format(stripped_location_id[-2], stripped_location_id[-1])
    port = port_mapping[index]
    return port


def is_cambrionix(device_dict):
    """Device dict is a cambrionix entry."""
    return device_dict['_name'] == usb_config.CAMBRIONIX_NAME
