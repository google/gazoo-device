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

"""Device class for ESP32 M5Stack locking device."""
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.base_classes import esp32_matter_device
from gazoo_device.capabilities.matter_endpoints import door_lock  # pylint: disable=unused-import
from gazoo_device.protos import device_service_pb2
from gazoo_device.protos import locking_service_pb2
from gazoo_device.utility import pwrpc_utils
import immutabledict

logger = gdm_logger.get_logger()

# TODO(b/209366650) Use discovery cluster and remove the hard-coded IDs.
_ESP32_DOOR_LOCK_ENDPOINT_ID = 1


class Esp32MatterLocking(esp32_matter_device.Esp32MatterDevice):
  """Device class for Esp32MatterLocking devices.

  Matter locking application running on the Espressif ESP32 M5Stack platform:
  https://github.com/project-chip/connectedhomeip/tree/master/examples/lock-app/esp32
  """
  DETECT_MATCH_CRITERIA = {
      detect_criteria.PigweedQuery.product_name:
          "cp2104 usb to uart bridge controller",
      detect_criteria.PigweedQuery.manufacturer_name: r"silicon(_| )labs",
      detect_criteria.PigweedQuery.app_type:
          pwrpc_utils.PigweedAppType.LOCKING.value,
  }
  ENDPOINT_ID_TO_CLASS = immutabledict.immutabledict({
      _ESP32_DOOR_LOCK_ENDPOINT_ID: door_lock.DoorLockEndpoint,
  })
  DEVICE_TYPE = "esp32matterlocking"
  _OWNER_EMAIL = "gdm-authors@google.com"
  _COMMUNICATION_KWARGS = {"protobufs": (locking_service_pb2,
                                         device_service_pb2,),
                           "baudrate": esp32_matter_device.BAUDRATE}

  @decorators.CapabilityDecorator(door_lock.DoorLockEndpoint)
  def door_lock(self) -> door_lock.DoorLockEndpoint:
    """ZCL door lock endpoint instance."""
    return self.matter_endpoints.get(_ESP32_DOOR_LOCK_ENDPOINT_ID)
