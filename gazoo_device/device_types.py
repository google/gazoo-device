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

"""Common device types used for type annotations in gazoo_device and externally.

Abstract and base classes are used instead of concrete classes to avoid:
* circular imports;
* dependencies on all device classes in GDM (to modularize packaging).
"""
from typing import Union

from gazoo_device.base_classes import auxiliary_device
from gazoo_device.base_classes import auxiliary_power_hub_device
from gazoo_device.base_classes import gazoo_device_base

# Using these abstract classes can result in not-instantiable pytype errors.
# There's no way to express that we expect a class to be a subclass of an
# abstract class. TypeVar() with a bound doesn't work for this, as it refers to
# binding to a specific subclass rather than any subclass. The only options are
# to either silence not-instantiable pytype errors, or disable pytype altogether
# by annotating these as Any.
PrimaryDevice = gazoo_device_base.GazooDeviceBase
AuxiliaryDevice = auxiliary_device.AuxiliaryDevice
Device = Union[PrimaryDevice, AuxiliaryDevice]
AuxiliaryPowerHubDevice = auxiliary_power_hub_device.AuxiliaryPowerHubDevice
