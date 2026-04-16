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

"""Stub concrete subclass of abstract SshDevice for unit testing.

This module is a GDM extension package (as it defines export_extensions).
"""
from typing import Any

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.base_classes import ssh_device
from gazoo_device.detect_criteria import generic_detect_criteria
import immutabledict

_LOGGER = gdm_logger.get_logger()


class SshDeviceStub(ssh_device.SshDevice):
  """Add dummy implementations for abstract methods to allow instantiation of SshDevice."""
  DEVICE_TYPE = "sshdevicestub"
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict({
      # Dummy detection query.
      generic_detect_criteria.GenericQuery.ALWAYS_TRUE: True,
  })

  @decorators.LogDecorator(_LOGGER)
  def factory_reset(self) -> None:
    del self  # Unused.

  @decorators.DynamicProperty
  def firmware_version(self) -> str:
    del self  # Unused.
    return "1234"

  @decorators.PersistentProperty
  def platform(self) -> str:
    del self  # Unused.
    return "dummy"

  @decorators.PersistentProperty
  def model(self) -> str:
    del self  # Unused.
    return "dummy"

  @decorators.LogDecorator(_LOGGER)
  def reboot(self, no_wait: bool = False, method: str = "shell") -> None:
    del self, no_wait, method  # Unused.


def export_extensions() -> dict[str, Any]:
  """Exports device class and capabilities to act as a GDM extension package."""
  return {"primary_devices": [SshDeviceStub]}

__version__ = "0.0.1"
