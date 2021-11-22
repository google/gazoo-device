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

"""Device class for EFR32 Matter Lighting device."""
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.base_classes import efr32_matter_device
from gazoo_device.capabilities import pwrpc_button_default
from gazoo_device.capabilities import pwrpc_light_default
from gazoo_device.protos import button_service_pb2
from gazoo_device.protos import device_service_pb2
from gazoo_device.protos import lighting_service_pb2
from gazoo_device.utility import pwrpc_utils

logger = gdm_logger.get_logger()

# Button action details can be referred to
# https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/efr32#running-the-complete-example
_VALID_BUTTON_IDS = (0, 1)
_BUTTON_RPC_TIMEOUT = 5  # seconds
_LIGHTING_RPC_TIMEOUT = 5  # seconds


class Efr32MatterLighting(efr32_matter_device.Efr32MatterDevice):
  """Device class for Efr32MatterLighting devices.

  Matter lighting sample application running on the Silabs EFR32 platform:
  https://github.com/project-chip/connectedhomeip/blob/master/examples/lighting-app/efr32/README.md
  """
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.product_name: "j-link",
      detect_criteria.PigweedQuery.manufacturer_name: r"silicon(_| )labs",
      detect_criteria.PigweedQuery.app_type:
          pwrpc_utils.PigweedAppType.LIGHTING.value,
  }
  DEVICE_TYPE = "efr32matterlighting"
  _OWNER_EMAIL = "gdm-authors@google.com"
  _COMMUNICATION_KWARGS = {"protobufs": (button_service_pb2,
                                         lighting_service_pb2,
                                         device_service_pb2),
                           "baudrate": efr32_matter_device.BAUDRATE}

  @decorators.CapabilityDecorator(pwrpc_button_default.PwRPCButtonDefault)
  def pw_rpc_button(self):
    """PwRPCButtonDefault capability to send RPC command."""
    return self.lazy_init(
        pwrpc_button_default.PwRPCButtonDefault,
        device_name=self.name,
        valid_button_ids=_VALID_BUTTON_IDS,
        switchboard_call=self.switchboard.call,
        rpc_timeout_s=_BUTTON_RPC_TIMEOUT)

  @decorators.CapabilityDecorator(pwrpc_light_default.PwRPCLightDefault)
  def pw_rpc_light(self):
    """PwRPCLight capability to send RPC commands."""
    return self.lazy_init(
        pwrpc_light_default.PwRPCLightDefault,
        device_name=self.name,
        switchboard_call=self.switchboard.call,
        rpc_timeout_s=_LIGHTING_RPC_TIMEOUT)
