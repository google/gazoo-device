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

"""Unit tests for gazoo_device_controllers.py.

Does a sanity check on the device controllers, capabilities, communication
types, and detect criteria exported by the gazoo_device_controllers module.
"""
from gazoo_device import data_types
from gazoo_device import gazoo_device_controllers
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.tests.unit_tests.utils import unit_test_case

# The lists below do not have to be exhaustive.
_EXPECTED_REAL_DEVICE_CLASS_NAMES = ()

_EXPECTED_VIRTUAL_DEVICE_CLASS_NAMES = ()

_EXPECTED_AUXILIARY_DEVICE_CLASS_NAMES = (
    "Cambrionix",
    "DliPowerSwitch",
    "RaspberryPi",
    "UnifiPoeSwitch",
    "Yepkit",
)

_EXPECTED_CAPABILITY_INTERFACE_CLASS_NAMES = (
    "CommPowerBase",
    "DevicePowerBase",
    "EventParserBase",
    "FastbootBase",
    "FileTransferBase",
    "FlashBuildBase",
    "PackageManagementBase",
    "ShellBase",
    "SwitchPowerBase",
    "SwitchboardBase",
    "UsbHubBase",
)

_EXPECTED_CAPABILITY_FLAVOR_CLASS_NAMES = (
    "CommPowerDefault",
    "DevicePowerDefault",
    "EventParserDefault",
    "FastbootDefault",
    "FileTransferAdb",
    "FileTransferDocker",
    "FileTransferEcho",
    "FileTransferScp",
    "PackageManagementAndroid",
    "ShellSSH",
    "SwitchPowerDliPowerswitch",
    "SwitchPowerEthernet",
    "SwitchPowerUnifiSwitch",
    "SwitchPowerUsbDefault",
    "SwitchPowerUsbWithCharge",
    "UsbHubDefault",
)

# Only *new* communication types that are exported by gazoo_device_controllers
_NEW_COMMUNICATION_TYPES = (
    "AdbComms",
    "DockerComms",
    "JlinkSerialComms",
    "PtyProcessComms",
    "SerialComms",
    "SshComms",
    "YepkitComms",
)
# Communication types for which detect criteria are exported
_COMM_TYPES_WITH_DETECT_CRITERIA = (
    "AdbComms",
    "DockerComms",
    "JlinkSerialComms",
    "PtyProcessComms",
    "SerialComms",
    "SshComms",
    "YepkitComms",
)
# Communication types for which no detect criteria are exported
_COMM_TYPES_WITHOUT_DETECT_CRITERIA = (
)

_EXTENSIONS = gazoo_device_controllers.export_extensions()


class GazooDeviceControllersTests(unit_test_case.UnitTestCase):
  """Unit tests for gazoo_device_controllers.py."""

  def test_supported_capability_flavors(self):
    """Test that capability flavors are exported by the package."""
    flavor_names = [
        flavor.__name__ for flavor in _EXTENSIONS["capability_flavors"]
    ]
    self._verify_expected_names_are_present(
        flavor_names, _EXPECTED_CAPABILITY_FLAVOR_CLASS_NAMES)
    self._verify_unexpected_names_are_not_present(
        flavor_names, _EXPECTED_CAPABILITY_INTERFACE_CLASS_NAMES)
    self.assertNotIn(capability_base.CapabilityBase.__name__, flavor_names)

  def test_supported_capability_interfaces(self):
    """Test that capability interfaces are exported by the package."""
    interface_names = [
        interface.__name__ for interface in _EXTENSIONS["capability_interfaces"]
    ]
    self._verify_expected_names_are_present(
        interface_names, _EXPECTED_CAPABILITY_INTERFACE_CLASS_NAMES)
    self._verify_unexpected_names_are_not_present(
        interface_names, _EXPECTED_CAPABILITY_FLAVOR_CLASS_NAMES)
    self.assertNotIn(capability_base.CapabilityBase.__name__, interface_names)

  def test_supported_device_classes(self):
    """Test that device classes are exported by the package."""
    real_device_class_names = [
        device_class.__name__ for device_class in _EXTENSIONS["primary_devices"]
    ]
    virtual_device_class_names = [
        device_class.__name__ for device_class in _EXTENSIONS["virtual_devices"]
    ]
    auxiliary_device_class_names = [
        device_class.__name__
        for device_class in _EXTENSIONS["auxiliary_devices"]
    ]
    self._verify_expected_names_are_present(real_device_class_names,
                                            _EXPECTED_REAL_DEVICE_CLASS_NAMES)
    self._verify_unexpected_names_are_not_present(
        real_device_class_names, _EXPECTED_VIRTUAL_DEVICE_CLASS_NAMES)
    self._verify_unexpected_names_are_not_present(
        real_device_class_names, _EXPECTED_AUXILIARY_DEVICE_CLASS_NAMES)
    self._verify_expected_names_are_present(
        virtual_device_class_names, _EXPECTED_VIRTUAL_DEVICE_CLASS_NAMES)
    self._verify_unexpected_names_are_not_present(
        virtual_device_class_names, _EXPECTED_REAL_DEVICE_CLASS_NAMES)
    self._verify_unexpected_names_are_not_present(
        virtual_device_class_names, _EXPECTED_AUXILIARY_DEVICE_CLASS_NAMES)
    self._verify_expected_names_are_present(
        auxiliary_device_class_names, _EXPECTED_AUXILIARY_DEVICE_CLASS_NAMES)
    self._verify_unexpected_names_are_not_present(
        auxiliary_device_class_names, _EXPECTED_REAL_DEVICE_CLASS_NAMES)
    self._verify_unexpected_names_are_not_present(
        auxiliary_device_class_names, _EXPECTED_VIRTUAL_DEVICE_CLASS_NAMES)

  def test_supported_communication_types(self):
    """Test that communication types are exported by the package."""
    comm_type_names = [
        comm_type.__name__ for comm_type in _EXTENSIONS["communication_types"]
    ]
    self._verify_expected_names_are_present(comm_type_names,
                                            _NEW_COMMUNICATION_TYPES)

  def test_detect_criteria(self):
    """Test that detect criteria are exported by the package."""
    all_comm_types = (
        _COMM_TYPES_WITH_DETECT_CRITERIA + _COMM_TYPES_WITHOUT_DETECT_CRITERIA)
    for comm_type in all_comm_types:
      with self.subTest(communication_type=comm_type):
        self.assertIn(comm_type, _EXTENSIONS["detect_criteria"])
        if comm_type in _COMM_TYPES_WITH_DETECT_CRITERIA:
          self.assertTrue(_EXTENSIONS["detect_criteria"][comm_type])
        else:
          self.assertFalse(_EXTENSIONS["detect_criteria"][comm_type])

  def test_download_key(self):
    """Tests the download_key function."""
    mock_key_info = data_types.KeyInfo(
        "my_ssh_key", data_types.KeyType.SSH, "gazoo_device_controllers")
    regex = r"GDM doesn't come with built-in SSH key.*my_ssh_key"
    with self.assertRaisesRegex(RuntimeError, regex):
      gazoo_device_controllers.download_key(
          mock_key_info, self.artifacts_directory)

  def _verify_expected_names_are_present(self, names, expected_names):
    for expected_name in expected_names:
      self.assertIn(expected_name, names)

  def _verify_unexpected_names_are_not_present(self, names, unexpected_names):
    for unexpected_name in unexpected_names:
      self.assertNotIn(unexpected_name, names)


if __name__ == "__main__":
  unit_test_case.main()
