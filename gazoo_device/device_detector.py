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

"""Detect Device."""
from __future__ import absolute_import
import os
import weakref
from gazoo_device import config
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.switchboard import communication_types


logger = gdm_logger.get_gdm_logger()


class DeviceDetector(object):
    """Class for detecting devices.

    Class scans systems for all connections, filters out known connections,
    then attempts to assign connection to right device classes and create
    entry in configs for persistent info (such as ID and serial_number)
    """

    def __init__(self, manager, log_directory,
                 supported_auxiliary_device_classes):
        """Initializes the device detector.

        Args:
            manager (Manager): instance of manager.
            log_directory (str): location of logs.
            supported_auxiliary_device_classes (list): list of auxiliary device classes.
        """
        self.manager_weakref = weakref.ref(manager)
        self.log_directory = log_directory
        self.auxiliary_classes = supported_auxiliary_device_classes
        self.persistent_configs = {
            "devices": self.manager_weakref().persistent_dict.copy(),
            "other_devices": self.manager_weakref().other_persistent_dict.copy()
        }
        self.options_configs = {
            "device_options": self.manager_weakref().options_dict.copy(),
            "other_device_options": self.manager_weakref().other_options_dict.copy()
        }
        self.known_connections = self._create_known_connections()

    def detect_all_new_devices(self, static_ips=None):
        """Finds all possible new connections and detects devices.

        Args:
          static_ips (list): static ips not otherwise detectable.

        Returns:
          tuple: dict of persistent props, dict of optional props
        """
        logger.info("\n##### Step 1/3: Detecting potential new communication addresses. #####\n")
        all_connections_dict = communication_types.detect_connections(static_ips)
        return self.detect_new_devices(all_connections_dict)

    def detect_new_devices(self, connections_dict):
        """Detects the devices for given connections.

        Args:
          connections_dict (dict): paths to connections grouped by type.

        Returns:
          tuple: persistent_configs, options_configs for all devices (new and old)

        --> Filters out known connections
        --> Determine device type
        --> Detects persistent info
        --> Updates persistent and optional configs
        --> Tracks errors and unidentified connections and Writes a summary
        """

        connections_dict = self._filter_out_known_connections(connections_dict,
                                                              self.known_connections)

        possible_device_tuples, errs, no_id_cons = self._identify_connection_device_class(
            connections_dict)
        new_names = []
        logger.info("\n##### Step 3/3: Extract Persistent Info from Detected Devices. #####\n")
        for device_class, connection in possible_device_tuples:
            try:
                name, persistent_props, optional_props = self._detect_get_info(
                    device_class, connection)
                new_names.append(name)
                self._add_to_configs(device_class, name, persistent_props, optional_props)
            except Exception as err:
                msg = "Error extracting info from {} {!r}. Err: {!r}".format(
                    device_class.DEVICE_TYPE, connection, err)
                errs.append(msg)
                no_id_cons.append(connection)

        self._print_summary(new_names, errs, no_id_cons)
        return self.persistent_configs, self.options_configs

    def _add_to_configs(self, device_class, name, persistent_props, optional_props):
        """Adds newly detect info to appropriate location in config.

        Args:
          device_class (device_class): device class
          name (str): name of device
          persistent_props (dict): dict of device's persistent props
          optional_props (dict): dict of device's optional props
        """

        if device_class in self.auxiliary_classes:
            ind = 1
            more_props = {key: None for key in config.HUB_OPTION_ATTRIBUTES}
        else:
            ind = 0
            more_props = {key: None for key in config.DEVICE_OPTION_ATTRIBUTES}

        # Add generic props to options
        optional_props.update(more_props)

        self.persistent_configs[config.DEVICES_KEYS[ind]][name] = persistent_props
        self.options_configs[config.OPTIONS_KEYS[ind]][name] = optional_props

    def _create_known_connections(self):
        """Returns all known connections.

        Returns:
           list: known connection paths.
        """
        known_connections = []

        for _, entry in self.persistent_configs['devices'].items():
            identifier = entry.get("console_port_name")
            if not identifier:
                # Use the IP address instead of the ADB port for ADB over IP
                identifier = entry.get("adb_serial").replace(":5555", "")
            known_connections.append(identifier)
        for _, entry in self.persistent_configs["other_devices"].items():
            identifier = entry.get("console_port_name")
            if not identifier:
                identifier = entry.get("hub_port_name")
            known_connections.append(identifier)

        return known_connections

    def _detect_get_info(self, device_class, connection):
        """Returns name, persistent and optional info from device communication.

        Args:
            device_class (type): device class with get_detection_info method.
            connection (str): path to path communication

        Returns:
            tuple: name, dict of persistent props, dict of options props

        Note:
           Any errors raised will be caught in parent method.
        """
        device_type = device_class.DEVICE_TYPE
        detect_file = self._get_detect_log_file(connection)
        device_config = {
            "persistent": {
                "console_port_name": connection,
                "device_type": device_type,
                "name": "\t{}_detect".format(device_type)},
            "options": {},
            "make_device_ready": "on"
        }
        logger.info(
            "Getting info from communication port {} for {}".format(
                connection,
                device_type))
        device = device_class(manager=self.manager_weakref(),
                              device_config=device_config,
                              log_directory=self.log_directory,
                              log_file_name=detect_file)
        try:
            device.make_device_ready()
            persistent_props, options_props = device.get_detection_info()
        finally:
            device.close()

        name = self._generate_name(device_type,
                                   persistent_props["serial_number"],
                                   device_class)
        persistent_props['name'] = name
        return name, persistent_props, options_props

    def _filter_out_known_connections(self, con_dict, known_cons):
        """Filters out already known connections.

        Args:
          con_dict (dict): dictionary of detected connections by type
          known_cons (list): list of known connections.

        Returns:
          dict: dictionary of unknown connections by type.
        """
        new_con_dict = {}
        for key, con_list in con_dict.items():
            new_con_dict[key] = [
                con for con in con_list
                if con.replace(u":5555", u"") not in known_cons]
            if new_con_dict[key]:
                logger.info(
                    "Found {} possible {} connections:".format(
                        len(new_con_dict[key]), key.lower().replace("_", " ")))
                logger.info(u"\t" + u"\n\t".join(new_con_dict[key]))
        return new_con_dict

    def _generate_name(self, device_type, serial_number, device_class):
        """Generates name from last four digits of serial_number.

        Args:
            device_type (str): device type.
            serial_number (str): device serial number.
            device_class (class): identifying class

        Returns:
            str: name of device

        Raises:
            RuntimeError: if serial number is too short.

        Note:
          If there is a conflict with a different device it will generate a longer name.
        """
        if len(serial_number) < 4:
            raise RuntimeError("{} serial number {} is too short.".format(
                device_type, serial_number))
        name = "{}-{}".format(device_type, serial_number[-4:].lower())

        # Check if name already exists
        if device_class in self.auxiliary_classes:
            key = "other_devices"
        else:
            key = "devices"
        if name in self.persistent_configs[key]:
            # Check if its the same device or not
            if serial_number != self.persistent_configs[key][name]["serial_number"]:
                name = "{}-{}".format(device_type, serial_number[-8:].lower())
        return name

    def _get_detect_log_file(self, address):
        name = address.replace("/", "_")
        return "{}_detect.txt".format(name)

    def _identify_connection_device_class(self, connections_dict):
        """Detects all connections' appropriate device class.

        Args:
            connections_dict (dict): dictionary of connections by communication type

        Returns:
          tuple: tuple of lists. list of (class, connection), errs, connections not id'd
        """
        possible_device_tuples = []
        errs = []
        no_id_cons = []
        logger.info("\n##### Step 2/3 Identify Device Type of Connections. #####\n")

        for key in sorted(connections_dict.keys()):
            if not connections_dict[key]:  # no connections of that type
                continue
            key_name = key.lower().replace("_", " ")
            logger.info("Identifying {} devices..".format(key_name))
            for connection in connections_dict[key]:
                detect_log = os.path.join(self.log_directory,
                                          self._get_detect_log_file(connection))
                matching_classes = detect_criteria.determine_device_class(
                    connection, key, detect_log, self.manager_weakref().create_switchboard)
                if len(matching_classes) > 1:
                    device_types = [device_class.DEVICE_TYPE for device_class in matching_classes]
                    logger.info("Warning: Multiple device classes matched connection {}."
                                " If this is not an issue with your device controller package, "
                                "open an issue against GDM. Returning {}".format(device_types,
                                                                                 device_types[0]))
                if matching_classes:
                    logger.info(
                        "\t{} is a {}.".format(
                            connection,
                            matching_classes[0].DEVICE_TYPE))
                    possible_device_tuples.append((matching_classes[0], connection))
                else:
                    logger.info(
                        "\t{} responses did not match a known device type.".format(connection))
                    no_id_cons.append(connection)
            logger.info("\t{} device_type detection complete.".format(key_name))
        return possible_device_tuples, errs, no_id_cons

    def _print_summary(self, names, errs, no_id_cons):
        """Prints summary of detection events.

        Args:
          names (list): list of detected names.
          errs (list): list of errors.
          no_id_cons (list): list of undetected connections.
        """
        logger.info("\n##### Detection Summary #####\n")
        logger.info("\t{} new devices detected:{}", len(names),
                    "\n\t\t" + "\n\t\t".join(names))
        if errs:
            logger.info("\n\t{} errors/warnings:{}",
                        len(errs),
                        "\n\t\t" + "\n\t\t".join(errs))
        if no_id_cons:
            logger.info("\n\t{} connections found but not detected:{}",
                        len(no_id_cons),
                        "\n\t\t" + "\n\t\t".join(no_id_cons))
