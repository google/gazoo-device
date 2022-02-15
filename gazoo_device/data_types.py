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

"""Simple data types without dependencies on other gazoo_device modules."""
import dataclasses
import enum

from typing_extensions import Literal

MAKE_DEVICE_READY_SETTING = Literal["on", "off", "check_only", "flash_build"]


@enum.unique
class KeyType(enum.Enum):
  SSH = "ssh"
  OTHER = "other"


@dataclasses.dataclass(frozen=True)
class KeyInfo:
  file_name: str  # Name of the key file.
  type: KeyType  # Key type, SSH or other (such as API).
  package: str  # Name of the package registering the key.
