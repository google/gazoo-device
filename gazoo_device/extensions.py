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

"""Global variables containing all extensions known to GDM.

Extension modules are registered by package_registrar.py at runtime.
Extension modules consist of:
- primary, auxiliary, and virtual device classes (controllers);
- capability interfaces and capability flavors (implementations);
- communication types;
- detection criteria for each communication type;
- metadata (extension package name and version);
- keys (such as SSH keys).

These values are intended for internal GDM usage only.
"""
from typing import Any, Callable, Literal, Union

from gazoo_device import data_types
import immutabledict

# We can't import some classes in this module due to import cycles.
_AuxiliaryDevice = Any  # device_types.AuxiliaryDevice
_CapabilityBase = Any  # capability_base.CapabilityBase
_CommunicationType = Any  # communication_types.CommunicationType
_DetectQueryMapping = Any  # detect_criteria.DetectQueryMapping
_FireManager = Any  # fire_manager.FireManager
_PrimaryDevice = Any  # device_types.PrimaryDevice

_CapabilityFlavorName = str
_CapabilityFlavorClass = type[_CapabilityBase]
_CapabilityInterfaceName = str
_CapabilityInterfaceClass = type[_CapabilityBase]
_CapabilityName = str
_CommunicationTypeName = str
_CommunicationTypeClass = type[_CommunicationType]
_FireManagerSubclass = type[_FireManager]
_PackageImportPath = str
_PackageName = str
_PackageVersion = str
_KeyLocalPath = str
_KeyDownloadFunction = Callable[[data_types.KeyInfo, _KeyLocalPath], None]

auxiliary_devices: list[type[_AuxiliaryDevice]] = []
# "capabilities" are derived from "capability_interfaces".
# Several capability interfaces can share the same name if they're derived from
# a common parent interface.
capabilities: dict[_CapabilityName, set[_CapabilityInterfaceName]] = {}
capability_interfaces: dict[
    _CapabilityInterfaceName, _CapabilityInterfaceClass
] = {}
capability_flavors: dict[_CapabilityFlavorName, _CapabilityFlavorClass] = {}
communication_types: dict[_CommunicationTypeName, _CommunicationTypeClass] = {}
detect_criteria: dict[_CommunicationTypeName, _DetectQueryMapping] = {}
primary_devices: list[type[_PrimaryDevice]] = []
virtual_devices: list[type[_PrimaryDevice]] = []
# "package_info" is a mapping of Package name -> immutabledict.immutabledict({
#     "version": package version (str),
#     "import_path": package import path (str),
# })
package_info: dict[
    _PackageName,
    immutabledict.immutabledict[
        Literal["version", "import_path"],
        Union[_PackageVersion, _PackageImportPath]
    ]
] = {}
key_to_download_function: dict[data_types.KeyInfo, _KeyDownloadFunction] = {}
manager_cli_mixins: list[_FireManagerSubclass] = []


def get_registered_package_info() -> str:
  """Returns names and versions of all registered extension packages."""
  extension_versions = []
  for package_name, package_data in package_info.items():
    extension_versions.append(f"{package_name} {package_data['version']}")
  return ", ".join(extension_versions)
