# Copyright 2021 Google LLC
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
from gazoo_device.base_classes import nrf_matter_device
from gazoo_device.capabilities import pwrpc_light_default
from gazoo_device.protos import device_service_pb2
from gazoo_device.protos import lighting_service_pb2
from gazoo_device.utility import pwrpc_utils

logger = gdm_logger.get_logger()


class PartnerExampleMatterLighting(nrf_matter_device.NrfMatterDevice):
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

  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.product_name:
          "partner-device-product-name",
      # Fill in your device's product name, see README.md for instructions.
      detect_criteria.PigweedQuery.manufacturer_name:
          "partner-device-manufacturer-name",
      # Fill in your device's manufacturer name, see README.md for instructions.
      # Real detection queries look like this
      # (Take NRF Matter lighting sample app as an example):
      # detect_criteria.PigweedQuery.product_name: "j-link",
      # detect_criteria.PigweedQuery.manufacturer_name: "segger",
      detect_criteria.PigweedQuery.app_type:
          pwrpc_utils.PigweedAppType.LIGHTING.value,
  }
  DEVICE_TYPE = "examplematterlighting"
  _COMMUNICATION_KWARGS = {
      "protobufs": (device_service_pb2,
                    lighting_service_pb2),
      "baudrate": nrf_matter_device.BAUDRATE,
  }
  _OWNER_EMAIL = "gdm-authors@google.com"

  @decorators.CapabilityDecorator(pwrpc_light_default.PwRPCLightDefault)
  def pw_rpc_light(self):
    """PwRPCLight capability to send RPC command."""
    return self.lazy_init(
        pwrpc_light_default.PwRPCLightDefault,
        device_name=self.name,
        switchboard_call=self.switchboard.call)
