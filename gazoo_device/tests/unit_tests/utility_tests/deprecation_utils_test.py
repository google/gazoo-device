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

"""Verifies the functionality of the deprecation_utils."""

from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import deprecation_utils


class _Nested:
  """_Nested object stub."""

  @property
  def prop(self):
    return "nested prop"

  def method(self):
    return "nested method"


class _Cap:
  """_Cap stub."""

  def __init__(self, nested_object):
    self._prop = "cap prop"
    self._method = "cap method"
    self._nested_object = nested_object

  @property
  def prop(self):
    return self._prop

  @property
  def nested_object(self):
    return self._nested_object

  def method(self):
    return self._method


class _ExampleDevice:
  """Example test device."""

  DEPRECATED_LIST = [("old_method", "cap.method", True),
                     ("old_property", "cap.prop", False)]

  def __init__(self):
    self._device_property = "device_property"
    self._device_method = "device_method"

  @property
  def device_property(self):
    return self._device_property

  @property
  def cap(self):
    if not (hasattr(self, "_cap") and self._cap):
      self._cap = _Cap(_Nested())
    return self._cap

  def device_method(self):
    return self._device_method


# This must be called on a class, not an instance of a class.
deprecation_utils.add_deprecated_attributes(_ExampleDevice,
                                            _ExampleDevice.DEPRECATED_LIST)


class DeprecationUtilsTests(unit_test_case.UnitTestCase):
  """Tests deprecation utilities."""

  def test_deprecated_method_calls_capability(self):
    """Verify that attributes return the same value through the deprecated method."""
    self.uut = _ExampleDevice()
    self.assertEqual(self.uut.old_method(), self.uut.cap.method())
    self.assertEqual(self.uut.old_property, self.uut.cap.prop)

  def test_deprecated_class_property_works(self):
    """Verify that a renamed property returns the same value."""

    class TestDevice(_ExampleDevice):
      pass

    deprecation_utils.add_deprecated_attribute(TestDevice,
                                               "test_device_property",
                                               "device_property", False)
    self.uut = TestDevice()
    self.assertEqual(self.uut.test_device_property, self.uut.device_property)

  def test_deprecated_class_method_works(self):
    """Verify that a renamed method returns the same value."""

    class TestDevice(_ExampleDevice):
      pass

    deprecation_utils.add_deprecated_attribute(TestDevice,
                                               "test_device_method",
                                               "device_method", False)
    self.uut = TestDevice()
    self.assertEqual(self.uut.test_device_method(), self.uut.device_method())

  def test_nested_properties(self):
    """Verify that nested properties can be added and resolve correctly."""

    class TestDevice(_ExampleDevice):
      pass

    deprecation_utils.add_deprecated_attribute(TestDevice,
                                               "old_replaced_by_nested",
                                               "cap.nested_object.prop", False)
    self.uut = TestDevice()
    self.assertEqual(self.uut.old_replaced_by_nested,
                     self.uut.cap.nested_object.prop)

  def test_verify_attributes_are_not_static(self):
    """Verify that attributes return the correct value after a change."""
    self.uut = _ExampleDevice()
    self.assertEqual(self.uut.old_method(), self.uut.cap.method())
    self.assertEqual(self.uut.old_property, self.uut.cap.prop)
    self.uut.cap._method = "modified method"
    self.uut.cap._prop = "modified prop"
    self.assertEqual(self.uut.old_method(), self.uut.cap.method())
    self.assertEqual(self.uut.old_property, self.uut.cap.prop)


if __name__ == "__main__":
  unit_test_case.main()
