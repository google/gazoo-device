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

"""Device controller for EFR32 Matter device.

This device controller populates the supported Matter endpoints on the EFR32
platform by using the descriptor RPC service.
"""
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.base_classes import matter_device_base
from gazoo_device.capabilities import flash_build_jlink

logger = gdm_logger.get_logger()
_EFR32_JLINK_NAME = "EFR32MG12PXXXF1024"


class Efr32Matter(matter_device_base.MatterDeviceBase):
  """EFR32 Matter device controller."""
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.IS_MATTER: True,
      detect_criteria.PigweedQuery.MANUFACTURER_NAME: r"silicon(_| )labs",
      detect_criteria.PigweedQuery.PRODUCT_NAME: "j-link",
  }
  # Button definition on EFR32 dev board:
  # https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/efr32#running-the-complete-example
  VALID_BUTTON_IDS = (0, 1)

  DEVICE_TYPE = "efr32matter"

  @decorators.PersistentProperty
  def os(self) -> str:
    """OS of EFR32 platform."""
    return "FreeRTOS"

  @decorators.PersistentProperty
  def platform(self) -> str:
    """EFR32 Silabs platform."""
    return "EFR32MG"

  @decorators.CapabilityDecorator(flash_build_jlink.FlashBuildJLink)
  def flash_build(self) -> flash_build_jlink.FlashBuildJLink:
    """FlashBuildJLink capability to flash hex image."""
    return self.lazy_init(flash_build_jlink.FlashBuildJLink,
                          device_name=self.name,
                          serial_number=self.serial_number,
                          platform_name=_EFR32_JLINK_NAME,
                          reset_endpoints_fn=self.matter_endpoints.reset,
                          switchboard=self.switchboard)
