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

"""Raspberry Pi Matter Controller device class."""
from typing import Any, Optional

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device import mobly_controller
from gazoo_device import version
from gazoo_device.auxiliary_devices import raspberry_pi
from gazoo_device.base_classes import matter_endpoints_mixin
from gazoo_device.capabilities import matter_controller_chip_tool
from gazoo_device.capabilities import matter_endpoints_accessor_chip_tool
from gazoo_device.detect_criteria import ssh_detect_criteria
from gazoo_device.keys import raspberry_pi_key
from gazoo_device.utility import key_utils
import immutabledict

logger = gdm_logger.get_logger()

_LOGGING_CMD = ("tail", "-F", matter_controller_chip_tool.LOGGING_FILE_PATH)


class RaspberryPiMatterController(
    raspberry_pi.RaspberryPi,
    matter_endpoints_mixin.MatterEndpointAliasesMixin):
  """Base Class for RaspberryPiMatterController Devices."""
  _COMMUNICATION_KWARGS = immutabledict.immutabledict({
      "log_cmd": _LOGGING_CMD,
      "key_info": raspberry_pi_key.SSH_KEY_PRIVATE,
      "username": "ubuntu"
  })
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict({
      ssh_detect_criteria.SshQuery.IS_UBUNTU_RPI: True,
      ssh_detect_criteria.SshQuery.IS_CHIP_TOOL_PRESENT: True,
  })
  DEVICE_TYPE = "rpi_matter_controller"

  _RESPONSE_REGEX = immutabledict.immutabledict({
      # Example matched pattern:
      # <2024-03-13 00:15:12.753091> GDM-0: [DMG] 3 (unsigned), 4 (unsigned), 6 (unsigned), 8 (unsigned), 29 (unsigned)  # pylint:disable=line-too-long
      "DESCRIPTOR_ATTRIBUTE_RESPONSE": r".DMG.\s*(\d+ \(unsigned\)(?:\s*,\s+\d+ \(unsigned\))*)",
      "DEVICE_TYPE_LIST_RESPONSE": r".TOO.\s+(?:Device)?Type: (\d+)",
  })

  @decorators.LogDecorator(logger)
  def factory_reset(self) -> None:
    """Factory resets the device."""
    self.matter_controller.factory_reset()

  @decorators.CapabilityDecorator(
      matter_controller_chip_tool.MatterControllerChipTool)
  def matter_controller(
      self) -> matter_controller_chip_tool.MatterControllerChipTool:
    """Matter controller capability to send chip-tool commands to the device."""
    return self.lazy_init(
        matter_controller_chip_tool.MatterControllerChipTool,
        device_name=self.name,
        regex_shell_fn=self.shell_with_regex,
        shell_fn=self.shell,
        send_file_to_device=self.file_transfer.send_file_to_device,
        get_property_fn=self.get_property,
        set_property_fn=self.set_property)

  @decorators.OptionalProperty
  def matter_node_id(self) -> Optional[int]:
    """Matter Node ID assigned to the currently commissioned end device."""
    return self.props["optional"].get("matter_node_id")

  @decorators.CapabilityDecorator(
      matter_endpoints_accessor_chip_tool.MatterEndpointsAccessorChipTool)
  def matter_endpoints(
      self
  ) -> matter_endpoints_accessor_chip_tool.MatterEndpointsAccessorChipTool:
    """Matter capability to access commissioned device's endpoint instances."""
    if self.matter_node_id is None:
      raise errors.DeviceError(
          "matter_endpoints requires a commissioned end device.")

    return self.lazy_init(
        matter_endpoints_accessor_chip_tool.MatterEndpointsAccessorChipTool,
        device_name=self.name,
        node_id_getter=lambda: self.matter_node_id,
        shell_fn=self.shell,
        shell_with_regex=self.shell_with_regex,
        matter_controller=self.matter_controller,
        device_type=self.DEVICE_TYPE,
        response_regex=self._RESPONSE_REGEX,
    )


_DeviceClass = RaspberryPiMatterController
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
