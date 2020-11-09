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

"""USB port map utility."""

from __future__ import absolute_import
import weakref

from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.auxiliary_devices import cambrionix
from gazoo_device.utility import usb_utils


logger = gdm_logger.get_gdm_logger()

# The PRODUCT_DEVICE_MAP is a dictionary with 'vendor_id/product_id' as the key
# and 'description' and 'type' in the values dict. The description includes
# the device_type in GDM as applicable.
# Example entry: {"1234/5678: {"description": "FooDevice", "type": "USB"}
PRODUCT_DEVICE_MAP = {}

# List of device types with a single serial connection.
SINGLE_CONNECTION_LIST = []


HUB_DEVICES_COLUMN_HEADER = "    Issue         Mode    Discovered                Configured"
OTHER_DEVICES_COLUMN_HEADER = "    Issue         Mode    Discovered"
OTHER_DEVICES_HEADER = "Other devices"


# Conflict types that port-map will test for and report.
USB_HUB_CONFLICT = "usb hub conflict"
USB_PORT_CONFLICT = "usb port conflict"
MISSING_USB_HUB = "missing usb hub"
MISSING_USB_PORT = "missing usb port"
NOT_DISCOVERED_CONFLICT = "not discovered"
NOT_DETECTED_CONFLICT = "not detected"


def _initialize_default_device(device):
    """Set values to the default for a device dictionary.

    Args:
        device (dict): The dictionary to be initialized with the default device data.
    """
    device['detected_devices'] = []
    device['device_type'] = None
    device['address'] = ''
    device['usb_hub_address'] = ''
    device['usb_hub_port'] = ''
    device['type'] = None
    device['serial_number'] = None
    device['conflict_types'] = []
    device['known_device'] = False
    device['description'] = '-'
    device['ftdi_interface'] = 0


def _identify_device(usb_info_inst):
    """Identify a udev usb device object and gather information about it.

    Args:
        usb_info_inst (UsbInfo): usb_info instance with usb information.

    Returns:
        dict: A dict containing device properties with the following keys:
            'description' (required): description of the Gazoo device, or contents of ID_SERIAL
                                if device not recognized.
            'name' (optional): GDM device name of the device, if recognized.
            'path_id' (required): the first part of the device id path.
            'part_id' (optional): the last part of the device id path.
    """
    product = "{}/{}".format(usb_info_inst.vendor_id, usb_info_inst.product_id)
    device_map_entry = PRODUCT_DEVICE_MAP.get(product)
    device_data = {}
    _initialize_default_device(device_data)
    if device_map_entry:
        device_data['known_device'] = True
        if 'device_type' in device_map_entry:
            id_suffix = usb_info_inst.serial_number[-4:].lower()
            device_data['name'] = "{}-{}".format(device_map_entry['device_type'], id_suffix)

        if 'type' in device_map_entry:
            device_data['type'] = device_map_entry['type']

        device_data['description'] = device_map_entry['description']
    else:
        device_data['description'] = usb_info_inst.serial_number

    device_data['serial_number'] = usb_info_inst.serial_number
    device_data['address'] = usb_info_inst.address
    device_data['usb_hub_address'] = usb_info_inst.usb_hub_address
    device_data['usb_hub_port'] = usb_info_inst.usb_hub_port
    device_data['ftdi_interface'] = usb_info_inst.ftdi_interface
    return device_data


def _get_usb_hub_map(device_info_list):
    """Creates a map of usb hub addresses to device_infos by port.

    Args:
        device_info_list (list): list of known usb_connections dicts.

    Returns:
       dict: map of usb hub addresses to device_infos by port
    """
    map_usb_hub_ports = {}
    for device_info in device_info_list:
        hub_address = device_info['usb_hub_address']
        port = device_info['usb_hub_port']
        if hub_address:
            if hub_address not in map_usb_hub_ports:
                map_usb_hub_ports[hub_address] = {}
            if not map_usb_hub_ports[hub_address].get(port) or device_info[
                    'ftdi_interface'] == 2:
                map_usb_hub_ports[hub_address][port] = device_info
    return map_usb_hub_ports


def _discover_cambrionix_devices(manager, cambrionix_info_list, device_info_list):
    """Discover all of the devices that are connected to a cambrionix.

    For each Cambrionix that is in the cambrionix_info_list, this function will use the devices
    in the device list to create port_list with information about each device that is connected
    to the Cambrionix USB hub.

    Args:
        manager (Manager): instance of Manager class
        cambrionix_info_list (list): list of devices for Cambrionix USB hubs
        device_info_list (list): list of devices for devices that have been detected

    Note:
        See the _identify_device function for more information on the device_data dicts that
        are used for the cambrionix_info_list and device_info_list.
    """
    device_config = {}
    map_usb_hub_ports = _get_usb_hub_map(device_info_list)
    for cambrionix_info in cambrionix_info_list:
        cambrionix_info['is_supported_hub'] = False
        try:
            device_config = {
                "persistent": {
                    "console_port_name": cambrionix_info['address'],
                    "name": "{}".format(cambrionix_info['name']),
                    "serial_number": cambrionix_info['serial_number']},
                "options": {},
                "make_device_ready": "on",
                "log_name_prefix": "port-map"
            }
            # Create the hub object. We don't use manager here since this is used
            # for hubs that have not been detected.
            cambrionix_inst = cambrionix.Cambrionix(manager=manager,
                                                    device_config=device_config,
                                                    log_file_name=None,
                                                    log_directory=manager.log_directory)
            cambrionix_inst.get_detection_info()  # populate undetected ones.
        except (KeyError, errors.GazooDeviceError):
            cambrionix_info['port_list'] = []
            cambrionix_info['port_count'] = 0
            continue

        try:
            cambrionix_info['port_count'] = cambrionix_inst.total_ports
            cambrionix_info['port_list'] = [None] * (cambrionix_info['port_count'] + 1)
            port_map = map_usb_hub_ports.get(cambrionix_info['address'], {})
            for port, device_info in port_map.items():
                cambrionix_info['port_list'][port] = device_info
            cambrionix_info['is_supported_hub'] = True
            cambrionix_info['port_modes'] = cambrionix_inst.switch_power.get_all_ports_mode()
        finally:
            cambrionix_inst.close()


class UsbPortMap(object):
    """Class for discovering USB information for connected devices, and printing a port-map."""

    def __init__(self, manager):
        """Initialize the USB port map instance by discovering devices and USB hubs.

        Args:
            manager (Manager):  instance of Manager class
        """
        self.manager_weakref = weakref.ref(manager)
        self.cambrionix_info_list = []
        self.device_info_list = []
        for usb_info_inst in usb_utils.get_address_to_usb_info_dict().values():
            device_info = _identify_device(usb_info_inst)
            if device_info:
                if 'cambrionix' in device_info.get('name', ''):
                    self.cambrionix_info_list.append(device_info)
                else:
                    self.device_info_list.append(device_info)

        _discover_cambrionix_devices(self.manager_weakref(),
                                     self.cambrionix_info_list,
                                     self.device_info_list)

        # remove devices associated with a cambrionix from the device list
        self.device_info_list = [device_info for device_info in self.device_info_list
                                 if not device_info['usb_hub_address']]

        # use what has been detected to add to what was discovered
        gdm_config = self.manager_weakref()._devices
        self._correlate_discovered_and_detected(gdm_config)
        self._get_detected_device_information(gdm_config)
        self._get_power_state_information()
        self._check_for_conflicts(gdm_config)

    def get_port_map(self):
        """Get a dictionary containing the port map information for the discovered devices.

        Returns:
            list: A list of dictionaries. Each entry in the list will be a hub or a device.
                  A hub will have a list of devices by port number, and a device will have the
                  port-map fields for that device, similar to what is printed by print_port_map.
        """
        port_map = []
        for cambrionix_info in self.cambrionix_info_list:
            port_map.append(self._get_hub_and_device_information(cambrionix_info))

        for device_info in self.device_info_list:
            other_info = self._get_other_device_information(device_info)
            if other_info:
                port_map.append(other_info)

        return port_map

    def print_port_map(self):
        """Print the port map based on what was discovered when the UsbPortMap object was created.
        """
        port_map = self.get_port_map()

        # Print the information for each hub in the port map
        for hub_or_device in port_map:
            if hub_or_device['hub_device']:
                hub_header_printed = False
                if 'port_list' not in hub_or_device:
                    continue
                for port, single in enumerate(hub_or_device['port_list']):
                    if port == 0 or not single:
                        continue
                    if not hub_header_printed:
                        hub_header_printed = True
                        if hub_or_device['is_detected']:
                            logger.info("\n{}".format(hub_or_device['hub_name']))
                        else:
                            logger.info("\n{} - Undetected".format(hub_or_device['hub_name']))
                        logger.info('-' * len(hub_or_device['hub_name']))
                        logger.info("\n{}\n".format(HUB_DEVICES_COLUMN_HEADER))

                    logger.info("{:>2}: {:13} {:7} {:25} {}".format(
                        port,
                        single['Issue'],
                        single['Mode'],
                        single['Discovered'],
                        single['Configured']))

        # Now that the hubs have been printed, loop through and print single devices
        other_header_printed = False
        for hub_or_device in port_map:
            if not hub_or_device['hub_device']:
                if not other_header_printed:
                    other_header_printed = True
                    logger.info("\n{}".format(OTHER_DEVICES_HEADER))
                    logger.info('-' * len(OTHER_DEVICES_HEADER))
                    logger.info("\n{}\n".format(OTHER_DEVICES_COLUMN_HEADER))

                logger.info("    {:13} Sync    {}".format(hub_or_device['Issue'],
                                                          hub_or_device['Discovered']))

    def _get_hub_and_device_information(self, hub):
        """Get information for all devices connected to a known USB hub.

        Args:
            hub (dict): A dictionary containing the information for the USB hub
        Returns:
            dict: A dictionary containing just the port map information for the hub, similar
                  to what is printed for print_port_map.
        """
        hub_dict = {}
        hub_dict['hub_name'] = hub['name']
        hub_dict['hub_device'] = True
        hub_dict['is_detected'] = hub['is_detected']
        if not hub['is_supported_hub']:
            hub_dict['port_count'] = 0
            hub_dict['port_list'] = []
            return hub_dict

        hub_dict['port_list'] = [None] * (hub['port_count'] + 1)
        hub_dict['port_count'] = hub['port_count']

        for port, device in enumerate(hub['port_list']):
            if port == 0:
                continue
            if device:
                # Based on the information on data in device, determine what will be printed
                mode_string = 'N/A'
                if 'port_mode' in device:
                    mode_string = device['port_mode']
                device_string = device['description']
                if 'gdm_config_name' in device:
                    device_string = device['gdm_config_name']
                if device['type']:
                    device_string += " " + device['type']
                configured_devices = ",".join(device['detected_devices'])
                issue_string = ""
                if configured_devices:
                    if len(device['detected_devices']) > 1:
                        issue_string = "Conflict"
                    if 'gdm_config_name' in device and \
                            device['gdm_config_name'] not in configured_devices:
                        issue_string = "Conflict"
                elif 'gdm_config_name' in device:
                    issue_string = "NotConfigured"
                if not issue_string and NOT_DETECTED_CONFLICT in device['conflict_types']:
                    issue_string = "Undetected"

                hub_dict['port_list'][port] = {}
                hub_dict['port_list'][port]['Issue'] = issue_string
                hub_dict['port_list'][port]['Mode'] = mode_string
                hub_dict['port_list'][port]['Discovered'] = device_string
                hub_dict['port_list'][port]['Configured'] = configured_devices
            else:
                logger.info("{:>2}: -".format(port))

        return hub_dict

    def _get_other_device_information(self, device):
        """Get the device information for a single device that is not associated with a USB hub.

        Args:
            device (dict): A dictionary containing information for a single device.
        Returns:
            dict: A dictionary containing device information for port-map or None.
        """
        if not device['known_device']:
            return None

        device_string = device['description']
        if 'gdm_config_name' in device:
            device_string = device['gdm_config_name']
        if device['type']:
            device_string += " " + device['type']
        issue_string = ""
        if USB_PORT_CONFLICT in device['conflict_types']:
            issue_string = "Conflict"
        if USB_HUB_CONFLICT in device['conflict_types']:
            issue_string = "Conflict"
        if NOT_DETECTED_CONFLICT in device['conflict_types']:
            issue_string = "Undetected"

        device_dict = {}
        device_dict['hub_device'] = False
        device_dict['Issue'] = issue_string
        device_dict['Mode'] = 'Sync'
        device_dict['Discovered'] = device_string
        device_dict['Configured'] = ''
        return device_dict

    def _check_known_devices(self,
                             device,
                             serial_numbers,
                             addresses):
        """Checks if usb connection matches a known device.

        Args:
            device (dict): A dictionary containing information about an individual device.
            serial_numbers (dict): The devices from GDM config with a configured serial number.
            addresses (dict): The devices from GDM config with a configured address.
        """
        if device:
            if device['address'] in addresses:
                device['gdm_config_name'] = addresses[device['address']]
            elif device['serial_number'] in serial_numbers:
                device['gdm_config_name'] = serial_numbers[device['serial_number']]
                del serial_numbers[device['serial_number']]

    def _correlate_discovered_and_detected(self, gdm_config):
        """Use the GDM config for detected devices to identify the discovered devices.

        Args:
            gdm_config (dict): a dictionary containing the devices detected by GDM.
        """
        serial_numbers = {}
        addresses = {}
        for name in gdm_config:
            if 'serial_number' in gdm_config[name]['persistent']:
                serial_numbers[gdm_config[name]['persistent']['serial_number']] = name
            if 'console_port_name' in gdm_config[name]['persistent']:
                addresses[gdm_config[name]['persistent']['console_port_name']] = name
        other_devices = self.manager_weakref().other_devices

        for cambrionix_info in self.cambrionix_info_list:
            cambrionix_info['is_detected'] = False
            if cambrionix_info['name'] in other_devices:
                cambrionix_info['is_detected'] = True

            for device_info in cambrionix_info['port_list']:
                self._check_known_devices(device_info,
                                          serial_numbers,
                                          addresses)

        for device_info in self.device_info_list:
            self._check_known_devices(device_info,
                                      serial_numbers,
                                      addresses)

        missing_device_info_list = []
        for number in serial_numbers:
            if serial_numbers[number] not in missing_device_info_list:
                missing_device_info_list.append(serial_numbers[number])

        for number in addresses:
            if addresses[number] not in missing_device_info_list:
                missing_device_info_list.append(addresses[number])

        # Some devices have a single connection, but may have an entry in more that one list.
        # For example, some devices will have a serial number and an adb serial number.
        # Iterate over the discovered devices and remove the extra entry so that they are not
        # reported as a missing device.
        for cambrionix_info in self.cambrionix_info_list:
            for device in cambrionix_info['port_list']:
                if not device:
                    continue

                if ('gdm_config_name' in device and
                        gdm_config[device['gdm_config_name']]['persistent']['device_type'] in
                        SINGLE_CONNECTION_LIST):
                    if device['gdm_config_name'] in missing_device_info_list:
                        missing_device_info_list.remove(device['gdm_config_name'])

        for device in self.device_info_list:
            if ('gdm_config_name' in device and
                    gdm_config[device['gdm_config_name']]['persistent']['device_type'] in
                    SINGLE_CONNECTION_LIST):
                missing_device_info_list.remove(device['gdm_config_name'])

        self.missing_devices = missing_device_info_list

    def _check_for_conflicts(self, gdm_config):
        """Use the GDM config for detected devices to add information or look for conflicts.

        Args:
            gdm_config (dict): a dictionary containing the devices detected by GDM
        """
        # Look for conflicts for devices that were discovered and are connected to a cambrionix
        for cambrionix_info in self.cambrionix_info_list:
            for index, device in enumerate(cambrionix_info['port_list']):
                if not device:
                    continue

                if device['known_device'] and 'gdm_config_name' not in device:
                    device['conflict_types'].append(NOT_DETECTED_CONFLICT)

                if 'gdm_config_name' in device:
                    device_id = device['gdm_config_name']
                    usb_hub_name, usb_port = self._get_usb_hub_info(device['type'],
                                                                    device_id,
                                                                    gdm_config)
                    if usb_hub_name and usb_hub_name != cambrionix_info['name']:
                        device['configured_hub'] = usb_hub_name
                        device['conflict_types'].append(USB_HUB_CONFLICT)

                    if usb_port and usb_port != str(index):
                        device['configured_port'] = usb_port
                        device['conflict_types'].append(USB_PORT_CONFLICT)

                    if device['type'] == 'USB':
                        if not usb_hub_name:
                            device['conflict_types'].append(MISSING_USB_HUB)
                        if not usb_port:
                            device['conflict_types'].append(MISSING_USB_PORT)

        # Look for conflicts for devices that were discovered and are not connected to a
        # cambrionix.
        for device in self.device_info_list:
            if device['known_device'] and 'gdm_config_name' not in device:
                device['conflict_types'].append(NOT_DETECTED_CONFLICT)
            if 'gdm_config_name' in device:
                device_id = device['gdm_config_name']
                usb_hub_name, usb_port = self._get_usb_hub_info(device['type'],
                                                                device_id,
                                                                gdm_config)
                if usb_hub_name:
                    device['conflict_types'].append(USB_HUB_CONFLICT)
                if usb_port:
                    device['conflict_types'].append(USB_PORT_CONFLICT)

    def _get_usb_hub_info(self,
                          connection_type,  # pylint: disable=unused-argument
                          device_id,
                          gdm_config):
        """Get the configured USB port for the specified device.

        Args:
            connection_type (str): no-op.
            device_id (str): the GDM name for a device.
            gdm_config (dict): a dictionary containing the devices detected by GDM.

        Returns:
            tuple: usb_hub_name, usb_port number. None if they are not set.
        """
        usb_hub_name = gdm_config[device_id]['persistent'].get('device_usb_hub_name')
        if not usb_hub_name:
            usb_hub_name = gdm_config[device_id]['options'].get('usb_hub')
        usb_port = gdm_config[device_id]['persistent'].get('device_usb_port')
        if not usb_port:
            usb_port = gdm_config[device_id]['options'].get('usb_port')
        return usb_hub_name, usb_port

    def _get_detected_device_information(self, gdm_config):
        """Use the GDM config for detected devices to add information to the device dictionary.

        Args:
            gdm_config (dict): a dictionary containing the devices detected by GDM
        """
        cambrionix_lookup = {}
        for index, cambrionix_info in enumerate(self.cambrionix_info_list):
            # usb_hub_name could be the cambrionix device name or the serial port path.
            cambrionix_lookup[cambrionix_info['address']] = index
            cambrionix_lookup[cambrionix_info['name']] = index

        # Add the detected device to the device at cambrionix/port if there is a mismatch
        for gdm_device in gdm_config:
            device_usb_hub_info = self._get_usb_hub_info('usb', gdm_device, gdm_config)
            for usb_hub_name, usb_port in [device_usb_hub_info]:
                if usb_hub_name and usb_port and usb_hub_name in cambrionix_lookup:
                    hub_index = cambrionix_lookup[usb_hub_name]
                    port_num = int(usb_port)
                    if port_num < len(self.cambrionix_info_list[hub_index]['port_list']):
                        if not self.cambrionix_info_list[hub_index]['port_list'][port_num]:
                            self.cambrionix_info_list[hub_index]['port_list'][port_num] = {}
                            device = self.cambrionix_info_list[hub_index]['port_list'][port_num]
                            _initialize_default_device(device)
                            device['conflict_types'].append(NOT_DISCOVERED_CONFLICT)
                            device['detected_devices'].append(gdm_device)
                        else:
                            device = self.cambrionix_info_list[hub_index]['port_list'][port_num]
                            device['detected_devices'].append(gdm_device)
                            if device.get('gdm_config_name') != gdm_device:
                                device['conflict_types'].append(NOT_DISCOVERED_CONFLICT)

    def _get_power_state_information(self):
        """For devices connected to a Cambrionix USB hub, get the power state mode.

        Note:
            This method should be called after _discover_cambrionix_devices. This method uses the
            the port state in the cambrionix device that is set by _discover_cambrionix_devices.
        """
        for cambrionix_info in self.cambrionix_info_list:
            if not cambrionix_info['is_supported_hub']:
                continue
            for index, device in enumerate(cambrionix_info['port_list']):
                if index == 0:
                    continue
                if not device:
                    cambrionix_info['port_list'][index] = {}
                    device = cambrionix_info['port_list'][index]
                    _initialize_default_device(device)

                device['port_mode'] = cambrionix_info['port_modes'][index]
