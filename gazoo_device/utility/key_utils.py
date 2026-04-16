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

"""Utilities for downloading keys (SSH or API)."""
import os.path

from gazoo_device import data_types

_PUBLIC_KEY_SUFFIX = ".pub"


def download_key(key_info: data_types.KeyInfo, local_key_path: str) -> None:
  """Raises an error with instructions on how to generate or obtain a key.

  Args:
    key_info: Information about key to download.
    local_key_path: File to which the key should be stored.

  Raises:
    RuntimeError: Key has to be retrieved or generated manually.
  """
  base_error = f"GDM doesn't come with built-in SSH key {key_info}. "

  if local_key_path.endswith(_PUBLIC_KEY_SUFFIX):
    private_key_path = local_key_path[:-len(_PUBLIC_KEY_SUFFIX)]
  else:
    private_key_path = local_key_path
  how_to_fix = (
      "Run 'ssh-keygen' to generate your own key. "
      f"Select {private_key_path} as the file to which the key should be "
      "saved. Leave the passphrase empty.")
  raise RuntimeError(base_error + how_to_fix)
