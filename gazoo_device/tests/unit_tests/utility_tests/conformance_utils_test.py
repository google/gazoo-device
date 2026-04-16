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

"""Unit tests for conformance utilities."""
import abc
import logging
from typing import NoReturn
from unittest import mock

from absl.testing import parameterized
from gazoo_device import decorators
from gazoo_device import extensions
from gazoo_device import package_registrar
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.tests.unit_tests.utils import fake_capabilities
from gazoo_device.tests.unit_tests.utils import gazoo_device_base_stub
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import conformance_utils


# Inheritance hierarchy:
# RootCapabilityInterface1 -> DerivedCapabilityInterface1 -> SomeCapability1
#                                                         -> SomeCapability2
#                          -> DerivedCapabilityInterface2 -> SomeCapability3
#                          -> SomeCapability4
# RootCapabilityInterface2 -> DerivedCapabilityInterface3 -> SomeCapability5
#                          -> SomeCapability6


class RootCapabilityInterface1(capability_base.CapabilityBase):
  """Root capability interface 1."""


class RootCapabilityInterface2(capability_base.CapabilityBase):
  """Root capability interface 2."""


class DerivedCapabilityInterface1(RootCapabilityInterface1):
  """Derived capability interface 1."""


class DerivedCapabilityInterface2(RootCapabilityInterface1):
  """Derived capability interface 2."""


class DerivedCapabilityInterface3(RootCapabilityInterface2):
  """Derived capability interface 3."""


class SomeCapability1(DerivedCapabilityInterface1):
  """Capability 1."""


class SomeCapability2(DerivedCapabilityInterface1):
  """Capability 2."""


class SomeCapability3(DerivedCapabilityInterface2):
  """Capability 3."""


class SomeCapability4(RootCapabilityInterface1):
  """Capability 4."""


class SomeCapability5(DerivedCapabilityInterface3):
  """Capability 5."""


class SomeCapability6(RootCapabilityInterface2):
  """Capability 6."""


class ConformanceUtilsTests(unit_test_case.UnitTestCase):
  """Unit tests for conformance utilities."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    package_registrar.register(gazoo_device_base_stub)

  def setUp(self):
    super().setUp()
    self.enter_context(
        mock.patch.dict(
            extensions.capability_interfaces,
            fake_capabilities.SUPPORTED_INTERFACES))
    self.enter_context(
        mock.patch.dict(
            extensions.capability_flavors,
            fake_capabilities.SUPPORTED_FLAVORS))

  def test_capability_decorators_errors(self):
    """Tests multiple CapabilityDecorator scenarios which should raise."""
    test_cases = [
        (fake_capabilities.DeviceWithInvalidCapability1,
         "foo",
         r"TypeError.*not a subclass of CapabilityBase"),
        (fake_capabilities.DeviceWithInvalidCapability2,
         "foo",
         r"TypeError.*not a subclass of CapabilityBase"),
        (fake_capabilities.DeviceWithInvalidCapability3,
         "foo",
         r"TypeError.*is not a class object"),
        (fake_capabilities.DeviceWithUnsupportedCapability,
         "foo",
         r"ValueError.*Capability class .* is not supported"),
        (fake_capabilities.DeviceCapabilityInterfaceInsteadOfFlavor,
         "some_valid_capability",
         r"ValueError.*Capability class .* is not supported"),
        (fake_capabilities.DeviceInvalidCapabilityName,
         "unexpected_capability_name",
         r"RuntimeError.*under invalid name"),
        (fake_capabilities.DeviceDifferentCapabilityInterfaces,
         "some_valid_capability",
         r"ValueError.*do not inherit from a common interface class"),
    ]

    for device_class, capability_name, error_regex in test_cases:
      with self.subTest(device_class=device_class):
        invalid_definitions = (
            conformance_utils.get_invalid_capability_definitions(device_class))
        self.assertTrue(invalid_definitions)
        self.assertEqual(invalid_definitions[0][0], capability_name)
        self.assertRegex(invalid_definitions[0][1], error_regex)

  def test_capability_decorators_success(self):
    """Tests multiple CapabilityDecorator scenarios which should succeed."""
    test_cases = [
        fake_capabilities.DeviceNoCapabilities,
        fake_capabilities.DeviceOneFlavorCapability,
        fake_capabilities.DeviceOneFlavorCapabilityList,
        fake_capabilities.DeviceNonConformingNameFlavor,
        fake_capabilities.DeviceMultipleFlavorsCapabilityList,
        fake_capabilities.DeviceMultipleFlavorsCapabilityTuple,
        fake_capabilities.DeviceMultipleCapabilities,
        fake_capabilities.DeviceMultipleCapabilitiesMultipleFlavors,
    ]

    for device_class in test_cases:
      with self.subTest(device_class=device_class):
        self.assertFalse(
            conformance_utils.get_invalid_capability_definitions(device_class))

  def test_log_decorator_compliance_with_decorator(self):
    """Tests LogDecorator compliance on a class with decorated methods."""

    class FakeDevice(gazoo_device_base.GazooDeviceBase):

      @decorators.LogDecorator(logging.getLogger(self._testMethodName))
      def some_method_with_docstring(self):
        """Some decorated method."""

    self.assertFalse(
        conformance_utils.get_log_decorator_violators(FakeDevice, False))

  def test_log_decorator_compliance_without_decorator(self):
    """Tests LogDecorator compliance on a class with methods NOT decorated."""

    class FakeDevice(gazoo_device_base.GazooDeviceBase):

      def some_method_with_docstring(self):
        """Some docstring."""

    self.assertIn(
        FakeDevice.some_method_with_docstring.__name__,
        conformance_utils.get_log_decorator_violators(FakeDevice, False))

  def test_log_decorator_compliance_not_nest_device_class(self):
    """Tests LogDecorator compliance on a class which isn't supported."""

    class FakeDevice:

      def some_method_with_docstring(self):
        """Some undecorated method."""

    regex = (r"instances of .*AuxiliaryDevice.*, .*GazooDeviceBase.*, "
             r".*CapabilityBase.*")
    with self.assertRaisesRegex(TypeError, regex):
      conformance_utils.get_log_decorator_violators(FakeDevice, True)

  def test_log_decorator_compliance_check_inherited_methods(self):
    """Tests LogDecorator compliance with undecorated inherited methods.

    Inherited methods are checked for compliance (check_inherited=True).
    """

    class FakeDeviceParent(gazoo_device_base.GazooDeviceBase):

      def some_undecorated_method(self):
        """Some undecorated method."""

    class FakeDeviceChild(FakeDeviceParent):
      pass

    self.assertIn(
        FakeDeviceParent.some_undecorated_method.__name__,
        conformance_utils.get_log_decorator_violators(FakeDeviceChild, True))

  def test_log_decorator_compliance_ignore_inherited_methods(self):
    """Tests LogDecorator compliance with undecorated inherited methods.

    Inherited methods are NOT checked for compliance (check_inherited=False).
    """

    class FakeDeviceParent(gazoo_device_base.GazooDeviceBase):

      def some_undecorated_method(self):
        """Some undecorated method."""

    class FakeDeviceChild(FakeDeviceParent):
      pass

    self.assertFalse(
        conformance_utils.get_log_decorator_violators(FakeDeviceChild, False))

  def test_log_decorator_compliance_has_returns_section(self):
    """Tests LogDecorator compliance for method with a 'Returns:' section."""

    class FakeDevice(gazoo_device_base.GazooDeviceBase):

      def some_method_with_docstring_with_returns_section(self):
        """Foo.

        Returns:
          int: bar.
        """
        del self  # Unused: it's a dummy instance method
        return 1

    self.assertFalse(
        conformance_utils.get_log_decorator_violators(FakeDevice, False))

  def test_log_decorator_compliance_on_class_methods(self):
    """Tests LogDecorator compliance with undecorated class methods."""

    class FakeDevice(gazoo_device_base.GazooDeviceBase):

      @classmethod
      def some_undecorated_class_method(cls):
        """Some undecorated class method."""

    self.assertFalse(
        conformance_utils.get_log_decorator_violators(FakeDevice, False))

  def test_log_decorator_compliance_on_static_methods(self):
    """Tests LogDecorator compliance with undecorated static methods."""

    class FakeDevice(gazoo_device_base.GazooDeviceBase):

      @staticmethod
      def some_undecorated_static_method():
        """Some undecorated static method."""

    self.assertFalse(
        conformance_utils.get_log_decorator_violators(FakeDevice, False))

  def test_log_decorator_compliance_on_abstract_methods(self):
    """Tests LogDecorator compliance with undecorated abstract methods."""

    class FakeDevice(gazoo_device_base.GazooDeviceBase):

      @abc.abstractmethod
      def some_undecorated_abstract_method(self):
        """Some undecorated abstract method."""

    self.assertFalse(
        conformance_utils.get_log_decorator_violators(FakeDevice, False))

  def test_log_decorator_compliance_single_line_docstring_with_return(self):
    """Tests LogDecorator compliance with one-line docstring with a return."""

    class FakeDevice(gazoo_device_base.GazooDeviceBase):

      def some_method_with_one_line_docstring_and_return(self):
        """Returns the number of Foos in the Bar."""
        del self  # Unused: it's a dummy instance method
        return 1

    self.assertFalse(
        conformance_utils.get_log_decorator_violators(FakeDevice, False))

  def test_log_decorator_compliance_with_type_annotation(self):
    """Tests LogDecorator compliance on a method with type annotation."""

    class FakeDevice1(gazoo_device_base.GazooDeviceBase):
      """All required methods have been decorated with LogDecorator."""

      def some_method_returns_str(self) -> str:
        """Some method with a type annotation."""
        del self  # Unused: it's a dummy instance method
        return "foo"

      @decorators.LogDecorator(logging.getLogger(self._testMethodName))
      def some_method_returns_none(self) -> None:
        """Some method with a type annotation."""

      @decorators.LogDecorator(logging.getLogger(self._testMethodName))
      def some_method_never_returns(self) -> NoReturn:
        """Some method with a type annotation.

        Raises:
          RuntimeError: always raised to never return.
        """
        raise RuntimeError("Always raises")

    class FakeDevice2(gazoo_device_base.GazooDeviceBase):
      """Required methods have not been decorated with LogDecorator."""

      def some_method_returns_none(self) -> None:
        """Some method with a type annotation."""

      def some_method_never_returns(self) -> NoReturn:
        """Some method with a type annotation.

        Raises:
          RuntimeError: always raised to never return.
        """
        del self  # Unused: it's a dummy instance method
        raise RuntimeError("Always raises")

    self.assertFalse(
        conformance_utils.get_log_decorator_violators(FakeDevice1, False))

    self.assertCountEqual(
        conformance_utils.get_log_decorator_violators(FakeDevice2, False),
        ["some_method_returns_none", "some_method_never_returns"])

  @parameterized.named_parameters(
      ("derived_interfaces_share_root_interface",
       [DerivedCapabilityInterface1, DerivedCapabilityInterface2],
       RootCapabilityInterface1),
      ("root_and_derived_interfaces_share_root_interface",
       [RootCapabilityInterface1, DerivedCapabilityInterface1],
       RootCapabilityInterface1),
      ("derived_capabilities_share_root_interface",
       {SomeCapability1, SomeCapability4},
       RootCapabilityInterface1),
      ("derived_capabilities_share_derived_interface",
       {SomeCapability1, SomeCapability2},
       DerivedCapabilityInterface1),
      ("other_derived_capabilities_share_other_root_interface",
       (SomeCapability5, SomeCapability6),
       RootCapabilityInterface2),
      ("other_root_interface_and_derived_capability_share_root_interface",
       (RootCapabilityInterface2, SomeCapability5),
       RootCapabilityInterface2),
  )
  def test_get_shared_capability_interface_success(
      self, capability_flavors_or_interfaces, expected_shared_interface):
    """Tests get_shared_capability_interface when there's a shared interface."""
    self.assertEqual(
        conformance_utils.get_shared_capability_interface(
            capability_flavors_or_interfaces),
        expected_shared_interface)

  @parameterized.named_parameters(
      ("root_interfaces", [RootCapabilityInterface1, RootCapabilityInterface2]),
      ("root_and_derived_interfaces",
       {RootCapabilityInterface1, DerivedCapabilityInterface3}),
      ("derived_interfaces",
       {DerivedCapabilityInterface1, DerivedCapabilityInterface3}),
      ("derived_capabilities", (SomeCapability1, SomeCapability6)),
      ("root_interface_and_derived_capability",
       (RootCapabilityInterface2, SomeCapability1)),
  )
  def test_get_shared_capability_interface_error_no_shared_interface(
      self, capability_flavors_or_interfaces):
    """Tests get_shared_capability_interface when there's no shared interface."""
    with self.assertRaisesRegex(
        ValueError, "do not inherit from a common interface class"):
      conformance_utils.get_shared_capability_interface(
          capability_flavors_or_interfaces)


if __name__ == "__main__":
  unit_test_case.main()
