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

"""Device class for Partner Example Matter Lighting device."""
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.base_classes import matter_device_base
from gazoo_device.capabilities import flash_build_jlink

logger = gdm_logger.get_logger()


# TODO(b/224858911) Update the module with generic device controllers
class PartnerExampleMatterLighting(matter_device_base.MatterDeviceBase):
  """Partner example primary Matter device controller for a lighting device.

  The example Matter device controller assumes the partner device uses the NRF
  vendor platform (Nordic NRF52840 DK). If your device uses EFR32
  (Silabs EFR32MG) or ESP32 (Espressif M5Stack) platforms, simply inherit
  the device class from efr32_matter_device.Efr32MatterDevice or
  esp32_matter_device.Esp32MatterDevice respectively.
  See
  https://github.com/google/gazoo-device/tree/master/gazoo_device/primary_devices/
  for more examples.
  """

  # TODO(user): You may need to change the value of
  # detect_criteria.PigweedQuery.PRODUCT_NAME and
  # detect_criteria.PigweedQuery.MANUFACTURER_NAME for your device.
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.PRODUCT_NAME:
          "partner-device-product-name",
      # Fill in your device's product name, see README.md for instructions.
      detect_criteria.PigweedQuery.MANUFACTURER_NAME:
          "partner-device-manufacturer-name",
      # Fill in your device's manufacturer name, see README.md for instructions.
      # Real detection queries look like this
      # (Take NRF Matter lighting sample app as an example):
      # detect_criteria.PigweedQuery.PRODUCT_NAME: "j-link",
      # detect_criteria.PigweedQuery.MANUFACTURER_NAME: "segger",
      detect_criteria.PigweedQuery.IS_MATTER: True,
  }
  ENDPOINT_ID_TO_CLASS = None
  DEVICE_TYPE = "examplematterlighting"
  _OWNER_EMAIL = "gdm-authors@google.com"

  @decorators.PersistentProperty
  def os(self) -> str:
    return "Partner Device OS"

  @decorators.PersistentProperty
  def platform(self) -> str:
    return "Partner Device platform"

  @decorators.CapabilityDecorator(flash_build_jlink.FlashBuildJLink)
  def flash_build(self) -> flash_build_jlink.FlashBuildJLink:
    """FlashBuildJLink capability to flash hex image."""
    return self.lazy_init(flash_build_jlink.FlashBuildJLink,
                          device_name=self.name,
                          serial_number=self.serial_number,
                          platform_name="Partner Device Platform")
