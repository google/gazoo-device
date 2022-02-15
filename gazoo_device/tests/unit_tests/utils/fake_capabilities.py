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

"""Fake capability definitions and fake device classes with fake capabilities for unit testing."""
from gazoo_device import decorators
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.tests.unit_tests.utils import fake_devices
from gazoo_device.utility import common_utils

VALID_CAPABILITY_NAME = "some_valid_capability"
OTHER_VALID_CAPABILITY_NAME = "some_other_valid_capability"
NONCONFORMING_CAPABILITY_NAME = "non_conforming_capability"
PARENT_CAPABILITY_NAME = "valid_parent_capability"
CHILD_CAPABILITY_NAME = "valid_child_capability"


def get_interface_name(interface):
  return common_utils.generate_name(interface)


def get_flavor_name(flavor):
  return common_utils.generate_name(flavor)


# Valid capability interface definitions
class ValidCapabilityBase(capability_base.CapabilityBase):

  @classmethod
  def get_capability_name(cls):
    return VALID_CAPABILITY_NAME


class ValidOtherCapabilityBase(capability_base.CapabilityBase):

  @classmethod
  def get_capability_name(cls):
    return OTHER_VALID_CAPABILITY_NAME


class ValidParentCapabilityBase(capability_base.CapabilityBase):
  pass


class ValidChildCapabilityBase(ValidParentCapabilityBase):
  pass


class NonConformingCapabilityInterfaceNameWithOverride(
    capability_base.CapabilityBase):

  @classmethod
  def get_capability_name(cls):
    return NONCONFORMING_CAPABILITY_NAME


# Invalid capability interface definitions
class InvalidCapabilityBase:
  """Doesn't inherit from CapabilityBase."""
  pass


class UnsupportedCapabilityBase(capability_base.CapabilityBase):
  pass


class NonConformingCapabilityInterfaceNameNoOverride(
    capability_base.CapabilityBase):
  pass


_SUPPORTED_INTERFACES = [
    ValidCapabilityBase, ValidOtherCapabilityBase, ValidParentCapabilityBase,
    ValidChildCapabilityBase, NonConformingCapabilityInterfaceNameWithOverride,
    NonConformingCapabilityInterfaceNameNoOverride
]

SUPPORTED_INTERFACES = {
    get_interface_name(interface): interface
    for interface in _SUPPORTED_INTERFACES
}

# Note: NonConformingCapabilityInterfaceNameNoOverride is intentionally
# excluded. Generating a name for it should raise an error.
CAPABILITIES = {
    VALID_CAPABILITY_NAME:
        get_interface_name(ValidCapabilityBase),
    OTHER_VALID_CAPABILITY_NAME:
        get_interface_name(ValidOtherCapabilityBase),
    NONCONFORMING_CAPABILITY_NAME:
        get_interface_name(NonConformingCapabilityInterfaceNameWithOverride),
    PARENT_CAPABILITY_NAME:
        get_interface_name(ValidParentCapabilityBase),
    CHILD_CAPABILITY_NAME:
        get_interface_name(ValidChildCapabilityBase)
}


# Valid capability flavor definitions
class ValidCapabilityFlavor(ValidCapabilityBase):
  pass


class ValidCapabilityFlavor1(ValidCapabilityBase):
  pass


class ValidOtherCapabilityFlavor(ValidOtherCapabilityBase):
  pass


class ValidParentCapabilityFlavor(ValidParentCapabilityBase):
  pass


class ValidChildCapabilityFlavor(ValidChildCapabilityBase):
  pass


class NonConformingInterfaceNameFlavor(
    NonConformingCapabilityInterfaceNameWithOverride):
  pass


DICT_VALIDATION_KEYS = ["foo", "bar"]
DICT_VALIDATION_DICT_NAME = "some_dict"


class ValidDictValidationFlavor(ValidParentCapabilityBase):

  def __init__(self, some_dict, device_name):
    super(ValidDictValidationFlavor, self).__init__(device_name=device_name)

    self.validate_required_keys(DICT_VALIDATION_KEYS, some_dict,
                                DICT_VALIDATION_DICT_NAME)


_SUPPORTED_FLAVORS = [
    ValidCapabilityFlavor, ValidCapabilityFlavor1, ValidDictValidationFlavor,
    ValidOtherCapabilityFlavor, ValidParentCapabilityFlavor,
    ValidChildCapabilityFlavor, NonConformingInterfaceNameFlavor
]

SUPPORTED_FLAVORS = {
    get_flavor_name(flavor): flavor for flavor in _SUPPORTED_FLAVORS
}


# Invalid capability flavor definitions
class NoInterfaceFlavor(capability_base.CapabilityBase):
  pass


class UnsupportedFlavor(UnsupportedCapabilityBase):
  pass


# Device classes with invalid capability definitions
class DeviceWithInvalidCapability1(fake_devices.FakeGazooDeviceBase):
  """Capability doesn't inherit from CapabilityBase."""

  @decorators.CapabilityDecorator(InvalidCapabilityBase)
  def foo(self):
    return 1


class DeviceWithInvalidCapability2(fake_devices.FakeGazooDeviceBase):
  """Invalid capability class."""

  @decorators.CapabilityDecorator(str)
  def foo(self):
    return 1


class DeviceWithInvalidCapability3(fake_devices.FakeGazooDeviceBase):
  """Capability is a class instance (not a class object)."""

  @decorators.CapabilityDecorator("some_string")
  def foo(self):
    return 1


class DeviceWithUnsupportedCapability(fake_devices.FakeGazooDeviceBase):

  @decorators.CapabilityDecorator(UnsupportedFlavor)
  def foo(self):
    return 1


class DeviceInvalidCapabilityName(fake_devices.FakeGazooDeviceBase):

  @decorators.CapabilityDecorator(ValidCapabilityFlavor)
  def unexpected_capability_name(self):
    return 1


class DeviceDifferentCapabilityInterfaces(fake_devices.FakeGazooDeviceBase):

  @decorators.CapabilityDecorator(
      [ValidCapabilityFlavor, ValidOtherCapabilityFlavor])
  def some_valid_capability(self):
    return 1


class DeviceCapabilityInterfaceInsteadOfFlavor(
    fake_devices.FakeGazooDeviceBase):

  @decorators.CapabilityDecorator(ValidCapabilityBase)
  def some_valid_capability(self):
    return 1


# Device classes with valid capability definitions
class DeviceNoCapabilities(fake_devices.FakeGazooDeviceBase):
  pass


class DeviceOneFlavorCapability(fake_devices.FakeGazooDeviceBase):

  @decorators.CapabilityDecorator(ValidCapabilityFlavor)
  def some_valid_capability(self):
    return 1


class DeviceOneFlavorCapabilityList(fake_devices.FakeGazooDeviceBase):

  @decorators.CapabilityDecorator([ValidCapabilityFlavor])
  def some_valid_capability(self):
    return 1


class DeviceParentFlavorCapability(fake_devices.FakeGazooDeviceBase):

  @decorators.CapabilityDecorator([ValidParentCapabilityFlavor])
  def valid_parent_capability(self):
    return 1


class DeviceChildFlavorCapability(fake_devices.FakeGazooDeviceBase):

  @decorators.CapabilityDecorator([ValidChildCapabilityFlavor])
  def valid_child_capability(self):
    return 1


class DeviceNonConformingNameFlavor(fake_devices.FakeGazooDeviceBase):

  @decorators.CapabilityDecorator(NonConformingInterfaceNameFlavor)
  def non_conforming_capability(self):
    return 1


class DeviceMultipleFlavorsCapabilityList(fake_devices.FakeGazooDeviceBase):

  @decorators.CapabilityDecorator(
      [ValidCapabilityFlavor, ValidCapabilityFlavor1])
  def some_valid_capability(self):
    return 1


class DeviceMultipleFlavorsCapabilityTuple(fake_devices.FakeGazooDeviceBase):

  @decorators.CapabilityDecorator(
      (ValidCapabilityFlavor, ValidCapabilityFlavor1))
  def some_valid_capability(self):
    return 1


class DeviceMultipleCapabilities(fake_devices.FakeGazooDeviceBase):

  @decorators.CapabilityDecorator(ValidCapabilityFlavor)
  def some_valid_capability(self):
    return 1

  @decorators.CapabilityDecorator(ValidOtherCapabilityFlavor)
  def some_other_valid_capability(self):
    return 1


class DeviceMultipleCapabilitiesMultipleFlavors(
    fake_devices.FakeGazooDeviceBase):
  """Mock device with multiple capabilities and multiple flavors of them."""

  @decorators.CapabilityDecorator(
      (ValidCapabilityFlavor, ValidCapabilityFlavor1))
  def some_valid_capability(self):
    return 1

  @decorators.CapabilityDecorator(ValidOtherCapabilityFlavor)
  def some_other_valid_capability(self):
    return 1
