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

Note: usb_info_linux primarily relies on pyudev for full information.
It processes just adb devices and those that show up in /dev/serial/by-id
"""
import re
import sys
from gazoo_device.utility import usb_config
import pyudev

PERSISTENT_SERIAL_PATH_FOLDER = '/dev/serial/by-id'
MOUNTED_DISK_FOLDER = '/dev/disk/by-id'
ADB_SERIAL_REGEX = r"\/dev\/disk\/by-id\/usb-Linux_File-CD_Gadget_([\da-z]+)-0:0"
IDENTIFIER_REGEX = r"\d-\d(?:\.\d?)+(\d\.\d):\d\.\d"
ANDROID_DEVICE_PRODUCT_NAME = "File-CD Gadget"

# These vendor's mounted drives show up as multiple usb connections.
# We use the one with the symlink.
REPEAT_VENDORS = ["FTDI", "cambrionix", "Linux", "Nest", "Android"]


def get_address_to_usb_info_dict():
    """Returns a dict of address to the usb information.

    Returns:
       dict: dictionary of address to UsbInfo instance for each usb device attached.
    """
    udev_devices = get_pyudev_list_of_devices()
    relevant_devices = [device for device in udev_devices
                        if device.get('ID_BUS') == 'usb']
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
    for cam_address, model in model_dict.items():
        port_mapping = usb_config.CAMBRIONIX_PORT_MAP[model]
        for child_address in address_to_usb_info_dict[cam_address].child_addresses:
            if child_address in address_to_usb_info_dict:
                child_entry = address_to_usb_info_dict[child_address]
                child_entry.usb_hub_address = cam_address
                child_entry.usb_hub_port = _get_cambrionix_port_number(
                    location_dict[child_address],
                    port_mapping)


def _add_disk_info(address_to_usb_info_dict, disk_info):
    """Add disk path to the entries that have them."""
    for entry in address_to_usb_info_dict.values():
        serial = entry.serial_number
        if serial in disk_info:
            entry.disk = disk_info[serial]


def _get_address(udev_device):
    """Gets the serial port symlink under '/dev/serial/by-id', mounted drives, or adb serial."""
    devlinks_str = udev_device.get('DEVLINKS', "")
    paths = devlinks_str.split()
    if not devlinks_str:  # Get mounted drives without corresponding symlinks
        if udev_device.get('ID_VENDOR') not in REPEAT_VENDORS:
            return udev_device.get('DEVNAME')

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
    return parent.get("ID_MODEL")


def _get_cambrionix_port_number(dev_path, port_mapping):
    """Get port from dev path.

    Args:
        dev_path (str): udev device dev path.
        port_mapping (dict): dict of port identifiers to port numbers.
    Returns:
       int: port number or None if not found
    Note:
        Port identifier is the last two digits before the ':'
        So for "/devices/pci0000:00/0000:00:1a.0/usb1/"
               "1-1/1-1.5/1-1.5.4/1-1.5.4.3/1-1.5.4.3:1.3/"
               "ttyUSB42/tty/ttyUSB42"
        "1-1.5.4.3:1.3" is the relevant number.
        '1.3' indicates the FTDI interface
        '4.3' indicates the Cambrionix port
        1 - 1.5 indicates the parent usb.
    """
    match = re.search(IDENTIFIER_REGEX, dev_path)
    if match:
        port_identifier = match.group(1)
        if port_identifier in port_mapping:
            return port_mapping[port_identifier]
    return None


def _get_child_addresses(udev_device):
    """Get the addresses for the relevant children of the udev device."""
    all_children = _get_cambrionix_udev_children(udev_device)
    relevant_children = [device for device in all_children
                         if device.get('DEVLINKS') and _get_address(device)]
    if udev_device in relevant_children:
        relevant_children.remove(udev_device)
    grand_children = []
    for child_device in relevant_children:  # Remove children of other cambrionixes
        if _get_product_name(child_device) == usb_config.CAMBRIONIX_NAME:
            grand_children += _get_cambrionix_udev_children(child_device)
            grand_children.remove(child_device)
    return [_get_address(child) for child in relevant_children if child not in grand_children]


def _get_disk_info():
    """Returns a dictionary of disk paths to serial numbers."""
    devices = get_pyudev_list_of_devices(subsystem='block')
    mounted_info = {device.get('ID_SERIAL_SHORT', ""): device.get('DEVNAME')
                    for device in devices}
    return mounted_info


def _get_product_name(udev_device):
    """Gets the product name in a system agnostic way."""
    model = udev_device.get('ID_MODEL', '').replace("_", " ")
    if model == ANDROID_DEVICE_PRODUCT_NAME:  # Actually an Android device.
        model = "Android"
    return model


def _process_udev_device(udev_device):
    """Convert pyudev dict to the system agnostic form."""
    model = None
    dev_path = udev_device.get('DEVPATH', "")

    entry = usb_config.UsbInfo()
    address = _get_address(udev_device)
    if not address:
        return '', {}, None, None
    entry.address = address
    entry.product_id = udev_device.get('ID_MODEL_ID', "")
    entry.vendor_id = udev_device.get('ID_VENDOR_ID', "")
    entry.ftdi_interface = int(udev_device.get('ID_USB_INTERFACE_NUM', 0))
    entry.manufacturer = udev_device.get('ID_VENDOR', "")
    entry.serial_number = udev_device.get('ID_SERIAL_SHORT', "")
    entry.product_name = _get_product_name(udev_device)
    if entry.product_name == usb_config.CAMBRIONIX_NAME:
        entry.child_addresses = _get_child_addresses(udev_device)
        model = _get_cambrionix_model(udev_device)
    return address, entry, dev_path, model


def _get_cambrionix_udev_children(udev_device):
    """Gets all the udev devices representing a cambrionix's children."""
    return list(udev_device.parent.parent.parent.parent.parent.children)
