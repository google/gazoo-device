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

"""Device controller for NRF Matter device.

This device controller populates the supported Matter endpoints on the NRF
platform by using the descriptor RPC service.
"""
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.base_classes import matter_device_base
from gazoo_device.capabilities import flash_build_jlink

logger = gdm_logger.get_logger()
_NRF_JLINK_NAME = "NRF52840_XXAA"


class NrfMatter(matter_device_base.MatterDeviceBase):
  """NRF Matter device controller."""
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.IS_MATTER: True,
      detect_criteria.PigweedQuery.MANUFACTURER_NAME: "segger",
      detect_criteria.PigweedQuery.PRODUCT_NAME: "j-link",
  }
  # Button definition on Nordic dev board:
  # https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/nrfconnect#device-ui
  VALID_BUTTON_IDS = (0, 1, 2, 3)

  DEVICE_TYPE = "nrfmatter"

  @decorators.PersistentProperty
  def os(self) -> str:
    """OS of NRF platform."""
    return "Zephyr RTOS"

  @decorators.PersistentProperty
  def platform(self) -> str:
    """NRF platform."""
    return "nRF Connect"

  @decorators.CapabilityDecorator(flash_build_jlink.FlashBuildJLink)
  def flash_build(self) -> flash_build_jlink.FlashBuildJLink:
    """FlashBuildJLink capability to flash hex image."""
    return self.lazy_init(flash_build_jlink.FlashBuildJLink,
                          device_name=self.name,
                          serial_number=self.serial_number,
                          platform_name=_NRF_JLINK_NAME,
                          reset_endpoints_fn=self.matter_endpoints.reset,
                          switchboard=self.switchboard)
