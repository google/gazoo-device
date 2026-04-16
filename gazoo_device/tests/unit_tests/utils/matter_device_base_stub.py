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

"""Stub concrete subclass of abstract MatterDeviceBase for unit testing.

This module is a GDM extension package (as it defines export_extensions).
"""
from typing import Any

from gazoo_device import decorators
from gazoo_device.base_classes import matter_device_base
from gazoo_device.detect_criteria import pigweed_detect_criteria
import immutabledict

FAKE_OS = "fake-os"
FAKE_PLATFORM = "fake-platform"


class MatterDeviceBaseStub(matter_device_base.MatterDeviceBase):
  """Dummy implementation for instantiation of MatterDevice."""
  DEVICE_TYPE = "matterdevicestub"
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict({
      # Dummy detection query.
      pigweed_detect_criteria.PigweedQuery.IS_MATTER: True,
  })
  ENDPOINT_ID_TO_CLASS = {}

  @decorators.PersistentProperty
  def os(self) -> str:
    return FAKE_OS

  @decorators.PersistentProperty
  def platform(self) -> str:
    return FAKE_PLATFORM


def export_extensions() -> dict[str, Any]:
  """Exports device class and capabilities to act as a GDM extension package."""
  return {"primary_devices": [MatterDeviceBaseStub]}

__version__ = "0.0.1"
