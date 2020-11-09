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

"""Queries sent to devices of each type to determine whether they are a particular device type."""
import copy
import enum
import functools
import logging
import re
import requests
import subprocess

from gazoo_device import gdm_logger
from gazoo_device.utility import host_utils
from gazoo_device.utility import http_utils
from gazoo_device.utility import usb_utils
from gazoo_device.utility import supported_classes
logger = gdm_logger.get_gdm_logger()

FMT = "<%(asctime)s> GDM-M: %(message)s"

ADB_COMMANDS = {
}

DOCKER_COMMANDS = {
    "PRODUCT_NAME": "docker ps --filter id={} --format {{{{.Names}}}}"
}

SSH_COMMANDS = {
    "UNIFI_PRODUCT_NAME": "mca-cli-op info",
    "DLI_PRODUCT_NAME": "http://{address}/restapi/config/=brand_name/",
    "RPI_PRODUCT_NAME": "cat /proc/device-tree/model",
}


@functools.total_ordering
class QueryEnum(enum.Enum):
    """Allows comparison of enum properties for sorting purposes."""

    def __lt__(self, other):
        return self.name < other.name  # pylint: disable=comparison-with-callable


class ADB_QUERY(QueryEnum):
    pass


class DOCKER_QUERY(QueryEnum):
    product_name = "product_name"


class GENERIC_QUERY(QueryEnum):
    always_true = "always_true"


class SERIAL_QUERY(QueryEnum):
    product_name = "usb info product_name"


class SSH_QUERY(QueryEnum):
    """Query names for detection for SshComms Devices."""
    is_dli = "is_dli_power_switch"
    is_rpi = "is_raspberry_pi"
    is_unifi = "is_unifi_switch"


def docker_product_name_query(address, detect_logger):
    """Gets product name from docker device.

    Args:
        address (str): communication_address
        detect_logger (Logger): logs device interactions.
    Returns:
        str: product_name or empty
    """
    try:
        name = subprocess.check_output(DOCKER_COMMANDS["PRODUCT_NAME"].format(address).split())
        name = name.decode()
    except subprocess.CalledProcessError as err:
        detect_logger.info("docker_product_name_query failure: " + repr(err))
        return ""
    detect_logger.info("docker_product_name_query response: {}".format(name))
    return name


def always_true_query(address, detect_logger):    # pylint: disable=unused-argument
    """Used when there is just one type of device for a communication type."""
    detect_logger.info("always_true_query response: True")
    return True


def is_dli_query(address, detect_logger):
    """Determines if address belongs to dli power switch.

    Args:
        address (str): ip_address
        detect_logger (Logger): logs device interactions.
    Returns:
        bool: whether or not Power Switch in response
    """
    try:
        response = http_utils.send_http_get(
            SSH_COMMANDS["DLI_PRODUCT_NAME"].format(address=address),
            auth=requests.auth.HTTPDigestAuth("admin", "1234"),
            headers={"Accept": "application/json"},
            valid_return_codes=[200, 206, 207],
            timeout=1)
        name = response.text
    except RuntimeError as err:
        detect_logger.info("is_dli_query failure: " + repr(err))
        return False
    detect_logger.info("is_dli_query response: {!r}".format(name))
    return "Power Switch" in name


def is_rpi_query(address, detect_logger):
    """Determines if address belongs to raspberry pi.

    Args:
        address (str): ip_address
        detect_logger (Logger): logs device interactions.
    Returns:
        bool: whether or not Raspberry Pi in response
    """
    try:
        name = host_utils.ssh_command(
            address,
            command=SSH_COMMANDS["RPI_PRODUCT_NAME"],
            user="pi",
            ssh_key_type="raspbian")
    except RuntimeError as err:
        detect_logger.info("is_rpi_query failure: " + repr(err))
        return False
    detect_logger.info("is_rpi_query response: {!r}".format(name))
    return "Raspberry Pi" in name


def is_unifi_query(address, detect_logger):
    """Determines if address belongs to unifi poe switch.

    Args:
        address (str): ip_address
        detect_logger (Logger): logs device interactions.
    Returns:
        bool: whether or not USW in response
    """
    try:
        product_name = host_utils.ssh_command(address,
                                              SSH_COMMANDS["UNIFI_PRODUCT_NAME"],
                                              user="admin",
                                              ssh_key_type="unifi_switch")
    except RuntimeError as err:
        detect_logger.info("is_unifi_query failure: " + repr(err))
        return False
    detect_logger.info("is_unifi_query response: {!r}".format(product_name))
    return "USW" in product_name


def usb_product_name_query(address, detect_logger):
    """Gets product name from usb_info.

    Args:
        address (str): communication_address
        detect_logger (Logger): logs device interactions.
    Returns:
        str: product_name or empty
    """
    product_name = usb_utils.get_product_name_from_path(address).lower()
    detect_logger.info("usb_product_name_query response: {}".format(product_name))
    return product_name


ADB_QUERY_DICT = {
}

DOCKER_QUERY_DICT = {
    DOCKER_QUERY.product_name: docker_product_name_query
}

GENERIC_QUERY_DICT = {
    GENERIC_QUERY.always_true: always_true_query
}

SERIAL_QUERY_DICT = {
    SERIAL_QUERY.product_name: usb_product_name_query
}

SSH_QUERY_DICT = {
    SSH_QUERY.is_dli: is_dli_query,
    SSH_QUERY.is_rpi: is_rpi_query,
    SSH_QUERY.is_unifi: is_unifi_query,

}


DETECT_DICTIONARY = {
    "AdbComms": ADB_QUERY_DICT,
    "DockerComms": DOCKER_QUERY_DICT,
    "SerialComms": SERIAL_QUERY_DICT,
    "SshComms": SSH_QUERY_DICT,
    "YepkitComms": GENERIC_QUERY_DICT
}


def determine_device_class(address, communication_type, log_file_path, create_switchboard_func):
    """Returns the device class(es) that matches the address' responses.

    Compares the device_classes DETECT_MATCH_CRITERIA to the device responses.

    Args:
        address (str): communication_address.
        communication_type (str): category of communication.
        log_file_path (str): local path to write log messages to.
        create_switchboard_func (func): function to create a switchboard.

    Returns:
        list: classes where the device responses match the detect criteria.
    """
    detect_logger = _setup_logger(log_file_path)
    try:
        device_classes = get_communication_type_classes(communication_type)
        return find_matching_device_class(
            address, communication_type, detect_logger, create_switchboard_func, device_classes)
    finally:
        file_handler = detect_logger.handlers[0]
        file_handler.close()
        detect_logger.removeHandler(file_handler)


def find_matching_device_class(address,
                               communication_type,
                               detect_logger,
                               create_switchboard_func,
                               device_classes):
    """Returns all classes where the device responses match the detect criteria.

    Args:
        address(str): communication_address.
        communication_type(str): category of communication.
        detect_logger(Logger): logs device interactions.
        create_switchboard_func (func): function to create a switchboard.
        device_classes(list): device_classes whose match criteria must be compared to.

    Returns:
        list: classes where the device responses match the detect criteria.
    """

    matching_classes = []
    responses = _get_detect_query_response(address,
                                           communication_type,
                                           detect_logger,
                                           create_switchboard_func)
    for device_class in device_classes:
        if _matches_criteria(responses, device_class.DETECT_MATCH_CRITERIA):
            matching_classes.append(device_class)
            detect_logger.info("{}: Match.".format(device_class.DEVICE_TYPE))
        else:
            detect_logger.info("{}: No Match.".format(device_class.DEVICE_TYPE))
    return matching_classes


def get_communication_type_classes(communication_type):
    """Returns classes with that communication type.

    Args:
        communication_type(str): category of communication.

    Returns:
        list: classes with that communication type.
    """
    all_classes = copy.copy(supported_classes.SUPPORTED_AUXILIARY_DEVICE_CLASSES)
    all_classes += copy.copy(supported_classes.SUPPORTED_PRIMARY_DEVICE_CLASSES)
    all_classes += copy.copy(supported_classes.SUPPORTED_VIRTUAL_DEVICE_CLASSES)
    matching_classes = []
    for device_class in all_classes:
        if device_class.COMMUNICATION_TYPE == communication_type:
            matching_classes.append(device_class)
    return matching_classes


def _get_detect_query_response(address,
                               communication_type,
                               detect_logger,
                               create_switchboard_func):  # pylint: disable=unused-argument
    """Gathers device responses for all queries of that communication type.

    Args:
        address (str): communication_address
        communication_type (str): category of communication.
        detect_logger (Logger): logs device interactions.
        create_switchboard_func (func): function to create switchboard with.

    Returns:
        dict: device responses keyed by query enum member.
    """
    query_dict = DETECT_DICTIONARY[communication_type]
    args = [address, detect_logger]

    query_responses = {}
    for query_name in query_dict:
        try:
            query_responses[query_name] = query_dict[query_name](*args)
        except Exception as err:
            detect_logger.debug(f"failed getting detect query response for {address}: {err!r}")
            query_responses[query_name] = repr(err)

    return query_responses


def _matches_criteria(responses, match_criteria):
    """Checks if response dict matches match criteria.

    Note:
        There are two categories of values in match_criteria: bool and regexp/str
        Bools must match exactly while regexp must find a match in the response value.

    Args:
        responses (dict): device responses keyed by query name.
        match_criteria (dict): match values keyed by query name

    Returns:
        bool: whether or not responses meets match criteria
    """
    for entry, value in match_criteria.items():
        if isinstance(value, bool):
            if responses[entry] != value:
                return False
        else:
            if not re.search(value, responses[entry]):
                return False
    return True


def _setup_logger(log_file_path):
    """Set up a logger to log device interactions to the detect file.

    Args:
        log_file_path (str): path to log to.

    Returns:
        logger: logger for logging to log_file_path.
    """
    detect_logger = logging.getLogger(log_file_path)
    detect_logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(log_file_path)
    formatter = logging.Formatter(FMT)
    handler.setFormatter(formatter)
    detect_logger.addHandler(handler)
    return detect_logger
