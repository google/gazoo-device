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

"""Device class for NRF Matter Lighting device."""
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.base_classes import nrf_matter_device
from gazoo_device.capabilities import pwrpc_button_default
from gazoo_device.capabilities.matter_endpoints import color_temperature_light  # pylint: disable=unused-import
from gazoo_device.capabilities.matter_endpoints import on_off_light  # pylint: disable=unused-import
from gazoo_device.protos import button_service_pb2
from gazoo_device.protos import device_service_pb2
from gazoo_device.protos import lighting_service_pb2
from gazoo_device.utility import pwrpc_utils
import immutabledict

logger = gdm_logger.get_logger()

# Button action details can be referred to
# https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/nrfconnect#device-ui
_VALID_BUTTON_IDS = (0, 1, 2, 3)
_BUTTON_RPC_TIMEOUT = 5  # seconds
# TODO(b/209366650) Use discovery cluster and remove the hard-coded IDs.
_NRF_ON_OFF_LIGHT_ENDPOINT_ID = 1
_NRF_COLOR_TEMPERATURE_LIGHT_ENDPOINT_ID = 2


class NrfMatterLighting(nrf_matter_device.NrfMatterDevice):
  """Device class for NrfMatterLighting devices.

  Matter lighting sample application running on the nRF connect platform:
  https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/nrfconnect
  """
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.product_name: "j-link",
      detect_criteria.PigweedQuery.manufacturer_name: "segger",
      detect_criteria.PigweedQuery.app_type:
          pwrpc_utils.PigweedAppType.LIGHTING.value,
  }
  ENDPOINT_ID_TO_CLASS = immutabledict.immutabledict({
      _NRF_ON_OFF_LIGHT_ENDPOINT_ID: on_off_light.OnOffLightEndpoint,
      _NRF_COLOR_TEMPERATURE_LIGHT_ENDPOINT_ID:
          color_temperature_light.ColorTemperatureLightEndpoint,
  })
  DEVICE_TYPE = "nrfmatterlighting"
  _COMMUNICATION_KWARGS = {
      "protobufs": (button_service_pb2,
                    device_service_pb2,
                    lighting_service_pb2),
      "baudrate": nrf_matter_device.BAUDRATE,
  }
  _OWNER_EMAIL = "gdm-authors@google.com"

  @decorators.CapabilityDecorator(pwrpc_button_default.PwRPCButtonDefault)
  def pw_rpc_button(self):
    """PwRPCButtonDefault capability to send RPC command."""
    return self.lazy_init(
        pwrpc_button_default.PwRPCButtonDefault,
        device_name=self.name,
        valid_button_ids=_VALID_BUTTON_IDS,
        switchboard_call=self.switchboard.call,
        rpc_timeout_s=_BUTTON_RPC_TIMEOUT)

  @decorators.CapabilityDecorator(on_off_light.OnOffLightEndpoint)
  def on_off_light(self):
    """ZCL on_off light endpoint instance."""
    return self.matter_endpoints.get(_NRF_ON_OFF_LIGHT_ENDPOINT_ID)

  @decorators.CapabilityDecorator(
      color_temperature_light.ColorTemperatureLightEndpoint)
  def color_temperature_light(self):
    """ZCL color temperature light endpoint instance."""
    return self.matter_endpoints.get(_NRF_COLOR_TEMPERATURE_LIGHT_ENDPOINT_ID)
