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
auxiliary_devices = []  # List of device classes
# "capabilities" are derived from "capability_interfaces"
capabilities = {}  # Capability name -> capability interface name
capability_interfaces = {}  # Capability interface name -> interface class
capability_flavors = {}  # Capability flavor name -> capability flavor class
communication_types = {}  # Communication type name -> communication type class
# "detect_criteria" is a mapping of
# Communication type name -> {Query Key: Query function}
detect_criteria = {}
primary_devices = []  # List of device classes
virtual_devices = []  # List of device classes
# "package_info" is a mapping of Package name -> immutabledict({
#   "version": package version (str),
#   "key_download_function": package key download function,
#   "import_path": package import path (str)})
package_info = {}
keys = []  # List of data_types.KeyInfo instances
manager_cli_mixins = []  # List of class objects inheriting from FireManager


def get_registered_package_info() -> str:
  """Returns names and versions of all registered extension packages."""
  extension_versions = []
  for package_name, package_data in package_info.items():
    extension_versions.append(f"{package_name} {package_data['version']}")
  return ", ".join(extension_versions)
