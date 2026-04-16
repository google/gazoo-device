# Copyright 2023 Google LLC
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

"""Stub concrete subclass of abstract GazooDeviceBase for unit testing.

This module is a GDM extension package (as it defines export_extensions).
"""
from typing import Any, NoReturn

from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.detect_criteria import generic_detect_criteria
from gazoo_device.switchboard.communication_types import ssh_comms
from gazoo_device.tests.unit_tests.utils import fake_devices
import immutabledict


class GazooDeviceBaseStub(fake_devices.FakeGazooDeviceBase):
  """Stub GazooDeviceBase implementation with additional attributes for testing."""
  COMMUNICATION_TYPE = ssh_comms.SshComms
  _COMMUNICATION_KWARGS = immutabledict.immutabledict()
  DEVICE_TYPE = "devicestub"
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict({
      # Dummy detection query.
      generic_detect_criteria.GenericQuery.ALWAYS_TRUE: True,
  })
  logger = gdm_logger.get_logger()  # Mocked by device_base_class_test.py.

  @decorators.DynamicProperty
  def firmware_type(self) -> str:
    return "some_type"

  @decorators.DynamicProperty
  def bad_property(self) -> NoReturn:
    raise errors.DeviceError("x")

  @decorators.health_check
  def check_1(self) -> NoReturn:
    """Fake health check 1.

    Raises:
      CheckDeviceReadyError: for testing.
    """
    raise errors.CheckDeviceReadyError(self.name, "health check failed")

  @decorators.health_check
  def check_2(self) -> NoReturn:
    """Fake health check 2.

    Raises:
      CheckDeviceReadyError: for testing.
    """
    raise errors.CheckDeviceReadyError(self.name, "health check failed")

  @decorators.health_check
  def check_3(self) -> NoReturn:
    """Fake health check 3.

    Raises:
      DeviceError: for testing.
    """
    raise errors.DeviceError("health check failed")


def export_extensions() -> dict[str, Any]:
  """Exports device class and capabilities to act as a GDM extension package."""
  return {"primary_devices": [GazooDeviceBaseStub]}

__version__ = "0.0.1"
