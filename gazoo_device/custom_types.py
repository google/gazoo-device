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

"""Common types used for type annotations in gazoo_device and externally.

This module must not contain any imports from other gazoo_device modules to
avoid circular imports. For device types, see device_types.py.
"""
from typing import Literal, Union

MakeDeviceReadySettingStr = Literal["on", "off", "check_only", "flash_build"]
PropertyName = str
PropertyValue = Union[bool, float, int, str, None]
DeviceConfig = dict[PropertyName, PropertyValue]
DetectionInfo = tuple[DeviceConfig, DeviceConfig]
DeviceName = str
PersistentConfigsDict = dict[
    Literal["devices", "other_devices"],
    dict[DeviceName, DeviceConfig]]
OptionalConfigsDict = dict[
    Literal["device_options", "other_device_options"],
    dict[DeviceName, DeviceConfig]]
# Such entries are present in Manager._devices and Manager.other_devices.
ManagerDeviceConfigDict = dict[Literal["persistent", "options"],
                               DeviceConfig]
# Returned by <device_instance>.props.
DeviceClassConfigDict = dict[Literal["persistent_identifiers", "optional"],
                             DeviceConfig]
