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

"""Unit tests for base class esp32MatterDevice."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device import errors
from gazoo_device.base_classes import esp32_matter_device
from gazoo_device.capabilities import device_power_default
from gazoo_device.capabilities import pwrpc_common_default
from gazoo_device.tests.unit_tests.capability_tests.mixins import pwrpc_common_test
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
import immutabledict

_FAKE_DEVICE_ID = "esp32matterdevicestub-detect"
_FAKE_DEVICE_ADDRESS = "fake-device-address"
_FAKE_VENDOR_ID = "fake-vendor-id"
_FAKE_PRODUCT_ID = "fake-product-id"
_ESP32_CONNECT_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "os": "FreeRTOS",
    "platform": "ESP32",
    "serial_number": "FT2BSR6O",
    "name": "esp32matterdevicestub_detect",
    "device_type": "esp32matterdevicestub",
    "vendor_id": _FAKE_VENDOR_ID,
    "product_id": _FAKE_PRODUCT_ID,
})


class Esp32MatterDeviceStub(esp32_matter_device.Esp32MatterDevice):
  """Dummy implementation for instantiation of Esp32MatterDevice."""
  DEVICE_TYPE = "esp32matterdevicestub"
  ENDPOINT_ID_TO_CLASS = {}


class Esp32MatterDeviceTest(fake_device_test_case.FakeDeviceTestCase,
                            pwrpc_common_test.PigweedRpcCommonTestMixin):
  """Unit tests for base class Esp32MatterDevice."""

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements(_FAKE_DEVICE_ID)
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_ADDRESS
    self.uut = Esp32MatterDeviceStub(self.mock_manager,
                                     self.device_config,
                                     log_directory=self.artifacts_directory)

  @mock.patch.object(esp32_matter_device.os.path, "exists", return_value=True)
  def test_is_connected_true(self, mock_exists):
    """Verifies is_connected returns true when console port exists."""
    self.assertTrue(
        esp32_matter_device.Esp32MatterDevice.is_connected(self.device_config))
    mock_exists.assert_called_once()

  @mock.patch.object(
      esp32_matter_device.Esp32MatterDevice, "pw_rpc_common")
  def test_get_detection_info_on_success(self, mock_rpc_common):
    """Verifies persistent properties are set correctly."""
    mock_rpc_common.vendor_id = _FAKE_VENDOR_ID
    mock_rpc_common.product_id = _FAKE_PRODUCT_ID
    self._test_get_detection_info(
        console_port_name=_FAKE_DEVICE_ADDRESS,
        device_class=Esp32MatterDeviceStub,
        persistent_properties=_ESP32_CONNECT_PERSISTENT_PROPERTIES)

  def test_flash_build_capability(self):
    """Verifies the initialization of flash_build capability."""
    self.assertIsNotNone(self.uut.flash_build)

  def test_matter_endpoints_capability(self):
    """Verifies the initialization of matter_endpoints capability."""
    self.assertIsNotNone(self.uut.matter_endpoints)

  def test_device_power_capability(self):
    """Verifies the initialization of device_power capability."""
    self.assertIsNotNone(self.uut.device_power)

  @mock.patch.object(
      device_power_default.DevicePowerDefault, "cycle", autospec=True)
  def test_device_reboot_hard(self, reboot_fn):
    """Test reboot hard reboot method."""
    self.uut.reboot(method="hard")
    reboot_fn.assert_called_once()

  @parameterized.parameters(dict(method="soft"), dict(method="pw_rpc"))
  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "reboot", autospec=True)
  def test_device_reboot(self, reboot_fn, method):
    """Test soft/pw_rpc reboot method."""
    self.uut.reboot(method)
    reboot_fn.assert_called_once()

  def test_device_reboot_raise_error(self):
    """Test reboot method with invalid method."""
    with self.assertRaisesRegex(
        errors.DeviceError,
        r"ValueError: Method invalid_reboot_method not recognized"):
      self.uut.reboot(method="invalid_reboot_method")


if __name__ == "__main__":
  fake_device_test_case.main()
