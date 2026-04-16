"""Unit tests for capability_base.py."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.tests.unit_tests.utils import fake_capabilities
from gazoo_device.tests.unit_tests.utils import unit_test_case


class CapabilityBaseTests(unit_test_case.UnitTestCase):
  """Unit tests for capability_base.py."""

  def setUp(self):
    super().setUp()

    self.mock_device_name = "some_device"
    self.supported_capability_interfaces_mock = self.enter_context(
        mock.patch.dict(
            extensions.capability_interfaces,
            fake_capabilities.SUPPORTED_INTERFACES,
            clear=True))

  @parameterized.named_parameters(
      ("test_none", None, False),
      ("test_true", True, True),
      ("test_false", False, True))
  def test_health_checked_function(self, healthy_value, expected_value):
    """Tests health_checked logic."""
    self.uut = capability_base.CapabilityBase(self.mock_device_name)
    self.uut._healthy = healthy_value
    self.assertEqual(self.uut.health_checked, expected_value)

  def test_get_capability_interface_errors(self):
    """Test get_capability_interface raises an error when there's no supported interface."""
    classes = (fake_capabilities.UnsupportedCapabilityBase,
               fake_capabilities.NoInterfaceFlavor,
               fake_capabilities.UnsupportedFlavor)

    for a_class in classes:
      with self.assertRaisesRegex(
          TypeError, "does not inherit from a known capability interface"):
        a_class.get_capability_interface()

  def test_get_capability_interface_success(self):
    """Test various get_capability_interface successful usages."""
    test_cases = (
        (capability_base.CapabilityBase, capability_base.CapabilityBase),
        (fake_capabilities.ValidParentCapabilityBase,
         fake_capabilities.ValidParentCapabilityBase),
        (fake_capabilities.ValidChildCapabilityBase,
         fake_capabilities.ValidChildCapabilityBase),
        (fake_capabilities.ValidParentCapabilityFlavor,
         fake_capabilities.ValidParentCapabilityBase),
        (fake_capabilities.ValidChildCapabilityFlavor,
         fake_capabilities.ValidChildCapabilityBase),
        (fake_capabilities.NonConformingInterfaceNameFlavor,
         fake_capabilities.NonConformingCapabilityInterfaceNameWithOverride))

    for a_class, expected_result in test_cases:
      self.assertIs(a_class.get_capability_interface(), expected_result)

  def test_get_capability_name_errors(self):
    """Test error scenarios of get_capability_name method."""
    with self.assertRaises(TypeError):
      fake_capabilities.NoInterfaceFlavor.get_capability_name()
    with self.assertRaises(TypeError):
      fake_capabilities.UnsupportedFlavor.get_capability_name()
    with self.assertRaises(ValueError):
      capability_base.CapabilityBase.get_capability_name()
    with self.assertRaises(RuntimeError):
      cap_if = fake_capabilities.NonConformingCapabilityInterfaceNameNoOverride
      cap_if.get_capability_name()

  def test_get_capability_name_success(self):
    """Test various get_capability_name successful usages."""
    test_cases = (
        (fake_capabilities.ValidParentCapabilityBase,
         fake_capabilities.PARENT_CAPABILITY_NAME),
        (fake_capabilities.ValidChildCapabilityBase,
         fake_capabilities.CHILD_CAPABILITY_NAME),
        (fake_capabilities.NonConformingCapabilityInterfaceNameWithOverride,
         fake_capabilities.NONCONFORMING_CAPABILITY_NAME),
        (fake_capabilities.ValidParentCapabilityFlavor,
         fake_capabilities.PARENT_CAPABILITY_NAME),
        (fake_capabilities.ValidChildCapabilityFlavor,
         fake_capabilities.CHILD_CAPABILITY_NAME))

    for a_class, expected_name in test_cases:
      self.assertEqual(a_class.get_capability_name(), expected_name)

  def test_get_capability_name_caching(self):
    """Test that cache hits do not generate another get_capability_name() call."""
    expected_name = fake_capabilities.CHILD_CAPABILITY_NAME
    flavor = fake_capabilities.ValidChildCapabilityFlavor
    flavor.get_capability_name.cache_clear()
    self.assertEqual(flavor.get_capability_name(), expected_name)
    with mock.patch.object(
        capability_base,
        "get_default_capability_name") as mock_get_capability_name:
      self.assertEqual(flavor.get_capability_name(), expected_name)
      mock_get_capability_name.assert_not_called()

  def test_validate_required_keys_missing_all_keys(self):
    """Test validate_required_keys() method when dict is missing all of the required keys."""
    error_msg = (r"{} failed to create {!r} capability\. "
                 r"Dictionary {!r} is missing the following keys:".format(
                     self.mock_device_name,
                     fake_capabilities.PARENT_CAPABILITY_NAME,
                     fake_capabilities.DICT_VALIDATION_DICT_NAME))

    with self.assertRaisesRegex(errors.DeviceError, error_msg) as context:
      fake_capabilities.ValidDictValidationFlavor({}, self.mock_device_name)

    for expected_key_name in fake_capabilities.DICT_VALIDATION_KEYS:
      self.assertIn(expected_key_name, str(context.exception))

  def test_validate_required_keys_missing_some_keys(self):
    """Test validate_required_keys() method when dict is missing some of the required keys."""
    error_msg = (
        r"{} failed to create {!r} capability\. "
        r"Dictionary {!r} is missing the following keys: \['bar'\]".format(
            self.mock_device_name, fake_capabilities.PARENT_CAPABILITY_NAME,
            fake_capabilities.DICT_VALIDATION_DICT_NAME))

    with self.assertRaisesRegex(errors.DeviceError, error_msg):
      fake_capabilities.ValidDictValidationFlavor({"foo": 1},
                                                  self.mock_device_name)

  def test_validate_required_keys_success(self):
    """Test validate_required_keys() method when dict has all of the required keys."""
    fake_capabilities.ValidDictValidationFlavor({
        "foo": 1,
        "bar": "baz"
    }, self.mock_device_name)


if __name__ == "__main__":
  unit_test_case.main()
