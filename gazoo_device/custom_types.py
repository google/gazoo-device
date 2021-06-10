# Copyright 2021 Google LLC
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

"""Common types used across the gazoo_device module and externally."""
from typing import Dict, Union

from gazoo_device.base_classes import auxiliary_device
from gazoo_device.base_classes import gazoo_device_base
from typing_extensions import Literal  # Moved to typing in 3.8+

# A device object, as returned by Manager.create_device().
Device = Union[auxiliary_device.AuxiliaryDevice,
               gazoo_device_base.GazooDeviceBase]

PropertyName = str
PropertyValue = Union[bool, float, int, str, None]
DeviceConfig = Dict[PropertyName, PropertyValue]

DeviceName = str
PersistentConfigsDict = Dict[
    Literal["devices", "other_devices"],
    Dict[DeviceName, DeviceConfig]]
OptionalConfigsDict = Dict[
    Literal["device_options", "other_device_options"],
    Dict[DeviceName, DeviceConfig]]
# Such entries are present in Manager._devices and Manager.other_devices.
ManagerDeviceConfigDict = Dict[Literal["persistent", "options"],
                               DeviceConfig]
# Returned by <device_instance>.props.
DeviceClassConfigDict = Dict[Literal["persistent_identifiers", "optional"],
                             DeviceConfig]
