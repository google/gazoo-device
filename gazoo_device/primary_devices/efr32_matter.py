# Copyright 2024 Google LLC
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
from typing import Any

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device import mobly_controller
from gazoo_device import version
from gazoo_device.base_classes import matter_device_base
from gazoo_device.capabilities import flash_build_commander
from gazoo_device.capabilities.interfaces import matter_controller_base
from gazoo_device.capabilities.matter_clusters.interfaces import measurement_base
from gazoo_device.detect_criteria import pigweed_detect_criteria
import immutabledict

logger = gdm_logger.get_logger()
_EFR32_JLINK_NAME = "EFR32MG12PXXXF1024"


class Efr32Matter(matter_device_base.MatterDeviceBase):
  """EFR32 Matter device controller."""
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict({
      pigweed_detect_criteria.PigweedQuery.IS_MATTER: True,
      pigweed_detect_criteria.PigweedQuery.MANUFACTURER_NAME:
          r"silicon(_| )labs",
      pigweed_detect_criteria.PigweedQuery.PRODUCT_NAME: "j-link",
  })
  # Button definition on EFR32 dev board:
  # https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/efr32#running-the-complete-example
  VALID_BUTTON_IDS = (0, 1)

  DEVICE_TYPE = "efr32matter"

  MATTER_COMMISSION_METHOD = matter_controller_base.CommissionMethod.BLE_THREAD

  @decorators.PersistentProperty
  def os(self) -> str:
    """OS of EFR32 platform."""
    return "FreeRTOS"

  @decorators.PersistentProperty
  def platform(self) -> str:
    """EFR32 Silabs platform."""
    return "EFR32MG"

  @decorators.CapabilityDecorator(flash_build_commander.FlashBuildCommander)
  def flash_build(self) -> flash_build_commander.FlashBuildCommander:
    """FlashBuildCommander capability to flash s37 image."""
    return self.lazy_init(
        flash_build_commander.FlashBuildCommander,
        device_name=self.name,
        serial_number=self.serial_number,
        reset_endpoints_fn=self.matter_endpoints.reset,
        switchboard=self.switchboard,
        wait_for_bootup_complete_fn=self.wait_for_bootup_complete)


_DeviceClass = Efr32Matter
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
      "primary_devices": [_DeviceClass],
      "detect_criteria": immutabledict.immutabledict({
          _COMMUNICATION_TYPE: pigweed_detect_criteria.PIGWEED_QUERY_DICT,
      }),
      "capability_interfaces": [
          # Overrides for the implicit export logic.
          # MeasurementClusterBase is an interface. It is not abstract and
          # defines public attributes, so the implicit export logic considers
          # it a flavor by default.
          # This is to resolve b/322915885.
          measurement_base.MeasurementClusterBase,
      ],
  }

__version__ = version.VERSION
