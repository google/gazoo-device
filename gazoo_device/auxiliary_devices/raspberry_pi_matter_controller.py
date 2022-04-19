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

from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.auxiliary_devices import raspberry_pi
from gazoo_device.capabilities import matter_controller_chip_tool

logger = gdm_logger.get_logger()


class RaspberryPiMatterController(raspberry_pi.RaspberryPi):
  """Base Class for RaspberryPiMatterController Devices."""
  DETECT_MATCH_CRITERIA = {
      detect_criteria.SshQuery.IS_RPI: True,
      detect_criteria.SshQuery.IS_CHIP_TOOL_PRESENT: True,
  }
  DEVICE_TYPE = "rpi_matter_controller"
  _OWNER_EMAIL = "gdm-authors@google.com"

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
        send_file_to_device=self.file_transfer.send_file_to_device)
