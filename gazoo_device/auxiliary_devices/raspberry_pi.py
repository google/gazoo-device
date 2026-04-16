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

"""Raspberry Pi device class."""
from typing import Any

from gazoo_device import gdm_logger
from gazoo_device import mobly_controller
from gazoo_device import version
from gazoo_device.base_classes import raspbian_device
from gazoo_device.detect_criteria import ssh_detect_criteria
from gazoo_device.keys import raspberry_pi_key
from gazoo_device.utility import key_utils
import immutabledict

logger = gdm_logger.get_logger()


class RaspberryPi(raspbian_device.RaspbianDevice):
  """Base Class for RaspberryPi Devices.

  Supports the following functionality:
      --logging
      --shell
      --reboot
  """
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict({
      ssh_detect_criteria.SshQuery.IS_RASPBIAN_RPI: True,
      ssh_detect_criteria.SshQuery.IS_CHIP_TOOL_PRESENT: False,
      ssh_detect_criteria.SshQuery.IS_MATTER_LINUX_APP_RUNNING: False,
  })
  DEVICE_TYPE = "raspberrypi"


_DeviceClass = RaspberryPi
_COMMUNICATION_TYPE = _DeviceClass.COMMUNICATION_TYPE.__name__
# For Mobly controller integration.
MOBLY_CONTROLLER_CONFIG_NAME = (
    mobly_controller.get_mobly_controller_config_name(_DeviceClass.DEVICE_TYPE))
create = mobly_controller.create
destroy = mobly_controller.destroy
get_info = mobly_controller.get_info
get_manager = mobly_controller.get_manager


def export_extensions() -> dict[str, Any]:
  """Exports device class and capabilities to act as a GDM extension package."""
  return {
      "auxiliary_devices": [_DeviceClass],
      "detect_criteria": immutabledict.immutabledict({
          _COMMUNICATION_TYPE: ssh_detect_criteria.SSH_QUERY_DICT,
      }),
      "keys": [
          raspberry_pi_key.SSH_KEY_PRIVATE,
          raspberry_pi_key.SSH_KEY_PUBLIC,
      ],
  }

__version__ = version.VERSION
download_key = key_utils.download_key
