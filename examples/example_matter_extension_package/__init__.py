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

"""A Matter example extension package for gazoo_device."""
from typing import Any, Dict, NoReturn

from gazoo_device import data_types
from gazoo_device import detect_criteria
from example_matter_extension_package import example_matter_device

__version__ = "0.0.1"
_PACKAGE_NAME = "example_matter_extension_package"


def download_key(key_info: data_types.KeyInfo, local_key_path: str) -> NoReturn:
  """Raises an error with instructions on how to generate or obtain a key.

  Args:
    key_info: Information about key to download.
    local_key_path: File to which the key should be stored.

  Raises:
    RuntimeError: No SSH keys are exported.
  """
  raise RuntimeError(f"No SSH keys are exported by {_PACKAGE_NAME}")


def export_extensions() -> Dict[str, Any]:
  """Exports the device controller defined by the extension package."""
  return {
      "primary_devices": [example_matter_device.PartnerExampleMatterLighting],
      "auxiliary_devices": [],
      "virtual_devices": [],
      "communication_types": [],
      "detect_criteria": {},
      "capability_interfaces": [],
      "capability_flavors": [],
  }
