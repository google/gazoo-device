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

"""SNMP queries sent to devices during detection to determine their device type."""
import logging
import re
import subprocess
from typing import Callable
from gazoo_device import errors
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.detect_criteria import base_detect_criteria
import immutabledict

# https://oidref.com/1.3.6.1.2.1.1.1
_GET_SYSTEM_DESCRIPTION_SNMP_COMMAND = (
    "snmpget -v 2c -c private {ip_address}:161 1.3.6.1.2.1.1.1.0")

# https://oidref.com/1.3.6.1.2.1.1.5
_GET_SYSTEM_NAME_SNMP_COMMAND = (
    "snmpget -v 2c -c private {ip_address}:161 1.3.6.1.2.1.1.5.0")

_DLINK_MODEL_RESPONSE_REG_EX = (
    r"((?:WS6-)?DGS-[0-9]+-[0-9]+)")

_SNMP_TIMEOUT_S = 5


class SnmpQuery(base_detect_criteria.QueryEnum):
  """Query names for detection of SnmpComms Devices."""
  IS_DLINK = "is_dlink_power_switch"


def get_dlink_model_name(ip_address: str) -> str:
  """Returns the model name of the Dlink switch at the ip_address.

  Expected response for supported dlink switch model should look like:

    "DGS-1100-<total-number-of-ports>" or
    "WS6-DGS-1210-<total-number-of-ports>"

  Depending on the dlink switch, this model identifier can be held in either
  the system name or system description OID, so both are checked here.

  Args:
    ip_address: The IP address to query for dlink model name.

  Raises:
    errors.DeviceError: When the dlink model is not contained in either the
    system name or system description OIDs.

  Returns:
    str: The model of the dlink switch.
  """
  system_description_cmd = _GET_SYSTEM_DESCRIPTION_SNMP_COMMAND.format(
      ip_address=ip_address)
  system_description_response = subprocess.check_output(
      system_description_cmd.split(), text=True, timeout=_SNMP_TIMEOUT_S)
  match_model = re.search(
      _DLINK_MODEL_RESPONSE_REG_EX, system_description_response)
  if match_model:
    return match_model.group(1)

  system_name_cmd = _GET_SYSTEM_NAME_SNMP_COMMAND.format(ip_address=ip_address)
  system_name_response = subprocess.check_output(
      system_name_cmd.split(), text=True, timeout=_SNMP_TIMEOUT_S)
  match_model = re.search(_DLINK_MODEL_RESPONSE_REG_EX, system_name_response)
  if match_model:
    return match_model.group(1)

  raise errors.DeviceError(
      f"Failed to retrieve model name from dlink_switch {ip_address}.\n"
      f"Sent commands {[system_description_cmd, system_name_cmd]} and"
      f"got responses {[system_description_response, system_name_response]}")


def _is_dlink_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> bool:
  """Determines if address belongs to dlink switch."""
  del create_switchboard_func  # Unused by _is_dlink_query
  try:
    model = get_dlink_model_name(ip_address=address)
    detect_logger.info("Got response to sysDescr SNMP query: %s\n"
                       "_is_dlink_query response: True", model)
  except (subprocess.CalledProcessError, errors.DeviceError) as err:
    detect_logger.info("_is_dlink_query failure: %r", err, exc_info=True)
    return False
  return True

SNMP_QUERY_DICT: immutabledict.immutabledict[
    SnmpQuery, base_detect_criteria.DetectQueryCallable] = (
        immutabledict.immutabledict({
            SnmpQuery.IS_DLINK: _is_dlink_query,
        })
    )
