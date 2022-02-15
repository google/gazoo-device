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

"""An example extension package for gazoo_device."""
from typing import Any, Dict

from gazoo_device import data_types
from gazoo_device import detect_criteria
from example_extension_package import example_linux_device

__version__ = "0.0.1"
_PACKAGE_NAME = "example_extension_package"


def download_key(key_info: data_types.KeyInfo, local_key_path: str) -> None:
  """Raises an error with instructions on how to generate or obtain a key.

  Args:
    key_info: Information about key to download.
    local_key_path: File to which the key should be stored.

  Raises:
    RuntimeError: Key has to be retrieved or generated manually.
  """
  raise RuntimeError(
      "The example device controller doesn't come with a key. "
      "Run 'ssh-keygen' to generate your own key. "
      f"Select {local_key_path} as the file to which the key should be "
      "saved. Leave the passphrase empty. Then transfer the new key to the "
      "device to ensure GDM can access it without a password: "
      f"'ssh-copy-id -i {local_key_path} <user>@<device_ip>'")


def export_extensions() -> Dict[str, Any]:
  """Exports the device controller defined by the extension package."""
  return {
      "primary_devices": [example_linux_device.ExampleLinuxDevice],
      "auxiliary_devices": [],
      "virtual_devices": [],
      "communication_types": [],
      "detect_criteria": {
          "SshComms": detect_criteria.GENERIC_QUERY_DICT,
      },
      "capability_interfaces": [],
      "capability_flavors": [],
      # TODO(user): Uncomment the key below if your device needs a password to
      # connect via SSH and you want to use a controller-specific key. To set a
      # key up, run "gdm download-keys" after registering this device
      # controller and follow the instructions.
      "keys": [
          # example_linux_device.SSH_KEY_INFO,
      ],
  }
