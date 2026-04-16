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

"""Simple data classes without dependencies on other gazoo_device modules."""
import dataclasses
import enum


@enum.unique
class KeyType(enum.Enum):
  SSH = "ssh"
  OTHER = "other"


@dataclasses.dataclass(frozen=True)
class KeyInfo:
  file_name: str  # Name of the key file.
  type: KeyType  # Key type, SSH or other (such as API).
  # Name of the key package. Defines the name of the sub-folder to which the key
  # is downloaded. Typically matches the name of the extension package. The
  # relative key path (<package>/<file_name>) must be unique.
  package: str
