# Copyright 2023 Google LLC
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
"""Communication type interface.

A communication type identifies all possible connections and maps them to
transports, buttons, data framers, and line identifiers.
"""
import abc
import os
from typing import Any
from gazoo_device import gdm_logger
from gazoo_device.switchboard import data_framer
from gazoo_device.switchboard import ftdi_buttons
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard.transports import transport_base
from gazoo_device.utility import usb_config
from gazoo_device.utility import usb_utils

JLINK_COMMS_PRODUCT_NAME = "J-Link"
NRF_DK_COMMS_ADDRESS_LINUX = "SEGGER_J-Link"
NRF_DK_EFR32_COMMS_ADDRESS_MAC = "tty.usbmodem"

logger = gdm_logger.get_logger()


def get_specific_serial_addresses(
    match_criteria: usb_utils.MatchCriteria) -> list[str]:
  """Returns addresses for connections that match criteria.

  Excludes Android devices.
  Connections first excluded and then included.
  If there is no include regex, all instances that don't match exclude_regex
  are included.

  Dictionary entry: {'<key>':
  {'include_regex': <regex>, 'exclude_regex': '<regex>'}}

  Args:
    match_criteria: Criteria for finding a match.

  Returns:
    Addresses from UsbInfo instances that match criteria.
  """
  instances = usb_utils.find_matching_connections(match_criteria)
  accessible_instances = [
      instance for instance in instances
      if os.access(instance.address, os.R_OK | os.W_OK)
  ]
  inaccessible_addresses = [
      instance.address
      for instance in instances
      if instance not in accessible_instances
  ]
  if inaccessible_addresses:
    logger.warning(
        "No read/write permission for these serial address(es): %s",
        inaccessible_addresses)
  return [
      instance.address
      for instance in accessible_instances
      if instance.product_name not in usb_config.ANDROID_NAMES
  ]


class CommunicationType(abc.ABC):
  """Default settings for a communication type.

  Child classes should at minimum overwrite get_transport_list and
  get_comms_addresses.
  Child classes will likely overwrite init with their required args.
  """

  def __init__(self, comms_address: str) -> None:
    """Initiates args."""
    self.comms_address = comms_address

  def get_button_list(self) -> list[ftdi_buttons.FtdiButtons]:
    """Set ups the list of FTDI button instances as needed.

    For non-ftdi devices it just returns an empty list.

    Returns:
      FTDI button instances.
    """
    return []

  @classmethod
  @abc.abstractmethod
  def get_comms_addresses(cls) -> list[str]:
    """Detects the comms addresses that match this communication type.

    List can overlap those from other communication types.

    Returns:
      Potential communication addresses.
    """

  def get_data_framers(self,
                       num_transports: int) -> list[data_framer.DataFramer]:
    """Set up framers used to atomicize the raw output of the device.

    Deals with interwoven lines as well as tokenized output. Default
    is to use new line character to separate the lines.

    Args:
      num_transports: Number of declared transports.

    Returns:
      Data framers mapped to each transport.
    """
    return [data_framer.NewlineFramer()] * num_transports

  def get_identifier(self) -> line_identifier.AllUnknownIdentifier:
    """Setup identifiers used to distinguish loglines from responses.

    Defaults to labelling all as unknown.

    Returns:
      LineIdentifier: type of line identifier.
    """
    return line_identifier.AllUnknownIdentifier()

  def get_partial_line_timeout_list(self, num_transports: int) -> list[float]:
    """Time to wait before returning partial lines for a device.

    Args:
      num_transports: Number of declared transports.

    Returns:
      Timeouts for each transport.
    """
    return [.1] * num_transports

  def get_switchboard_kwargs(self) -> dict[str, Any]:
    """Returns args needed to set up switchboard for this communication type.

    Returns:
      Dictionary of transport_list, identifier, framer_list, button_list.
    """
    transport_list = self.get_transport_list()
    num_transports = len(transport_list)
    return {
        "transport_list":
            transport_list,
        "identifier":
            self.get_identifier(),
        "framer_list":
            self.get_data_framers(num_transports),
        "button_list":
            self.get_button_list(),
        "partial_line_timeout_list":
            self.get_partial_line_timeout_list(num_transports),
    }

  @abc.abstractmethod
  def get_transport_list(self) -> list[transport_base.TransportBase]:
    """Setups up the transports which will communicate raw device io.

    Returns:
      list: Initiated transports.
    """
