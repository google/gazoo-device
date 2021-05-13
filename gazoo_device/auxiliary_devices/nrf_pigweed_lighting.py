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

"""Device class for nRF Pigweed Lighting device."""
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device.base_classes import nrf_connect_sdk_device
from gazoo_device.capabilities import pwrpc_common_default
from gazoo_device.capabilities import pwrpc_light_default
from gazoo_device.utility import pwrpc_utils

# TODO(b/185956488): Remove conditional imports of Pigweed
try:
  # pylint: disable=g-import-not-at-top
  from button_service import button_service_pb2
  from device_service import device_service_pb2
  from lighting_service import lighting_service_pb2
except ImportError:
  button_service_pb2 = None
  device_service_pb2 = None
  lighting_service_pb2 = None


class NRFPigweedLighting(nrf_connect_sdk_device.NRFConnectSDKDevice):
  """Device class for NRFPigweedLighting devices.

  This device class is for the Pigweed lighting application running
  on the nRF connect platform:
  https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/nrfconnect
  """
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.product_name: "j-link",
      detect_criteria.PigweedQuery.manufacturer_name: "segger",
      detect_criteria.PigweedQuery.app_type:
          pwrpc_utils.PigweedAppType.LIGHTING.value,
  }
  DEVICE_TYPE = "nrfpigweedlighting"
  _OWNER_EMAIL = "gdm-authors@google.com"
  _COMMUNICATION_KWARGS = {"protobufs": (button_service_pb2,
                                         lighting_service_pb2,
                                         device_service_pb2),
                           "baudrate": nrf_connect_sdk_device.BAUDRATE}

  @decorators.DynamicProperty
  def firmware_version(self):
    """Firmware version of the device."""
    return self.pw_rpc_common.software_version

  @decorators.CapabilityDecorator(pwrpc_common_default.PwRPCCommonDefault)
  def pw_rpc_common(self):
    return self.lazy_init(pwrpc_common_default.PwRPCCommonDefault,
                          device_name=self.name,
                          switchboard_call=self.switchboard.call)

  @decorators.CapabilityDecorator(pwrpc_light_default.PwRPCLightDefault)
  def pw_rpc_light(self):
    """PwRPCLight instance to send RPC command."""
    return self.lazy_init(pwrpc_light_default.PwRPCLightDefault,
                          device_name=self.name,
                          switchboard_call=self.switchboard.call)
