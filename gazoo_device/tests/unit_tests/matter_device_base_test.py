# Copyright 2024 Google LLC
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

"""Unit tests for MatterDeviceBase."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device import console_config
from gazoo_device import errors
from gazoo_device import package_registrar
from gazoo_device.base_classes import matter_device_base
from gazoo_device.capabilities import device_power_default
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities import pwrpc_common_default
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import matter_device_base_stub
import immutabledict

_FAKE_DEVICE_ID = "matterdevicebasestub-1234"
_FAKE_DEVICE_ADDRESS = "fake-device-address"
_FAKE_QR_CODE = "fake-qr-code"
_FAKE_QR_CODE_URL = "fake-qr-code-url"
_FAKE_ENDPOINT_INST = "fake-endpoint-instance"
_FAKE_FIRMWARE_VERSION = "fake-firmware-version"
_FAKE_DEVICE_TYPE_ID = 0
_FAKE_ENDPOINT_NAME = "fake-endpoint-name"
_FAKE_COMMAND = "fake-command"
_FAKE_PAIRING_CODE = 0
_FAKE_PAIRING_DISCRIMINATOR = 0
_CONNECT_PERSISTENT_PROPERTIES = immutabledict.immutabledict({
    "os": matter_device_base_stub.FAKE_OS,
    "platform": matter_device_base_stub.FAKE_PLATFORM,
    "serial_number": "FT2BSR6O",
    "name": "matterdevicebasestub_detect",
    "device_type": "matterdevicestub",
})


class MatterDeviceTest(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for MatterDevice base class."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    package_registrar.register(matter_device_base_stub)

  def setUp(self):
    super().setUp()
    self.setup_fake_device_requirements(_FAKE_DEVICE_ID)
    self.device_config["persistent"]["console_port_name"] = _FAKE_DEVICE_ADDRESS
    self.uut = matter_device_base_stub.MatterDeviceBaseStub(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory)

  def test_health_check(self):
    """Verifies health_check is not empty."""
    self.assertTrue(bool(self.uut.health_checks))

  @mock.patch.object(matter_device_base.MatterDeviceBase, "device_power")
  def test_check_power_on(self, mock_device_power):
    """Veirifes check_power_on on success."""
    self.uut.check_power_on()
    mock_device_power.on.assert_called_once()

  @mock.patch.object(matter_device_base.MatterDeviceBase, "matter_endpoints")
  def test_check_rpc_working_on_success(self, mock_matter_endpoints):
    """Verifies check_rpc_working on success."""
    self.uut.check_rpc_working()
    mock_matter_endpoints.reset.assert_called_once()
    mock_matter_endpoints.list.assert_called_once()

  @mock.patch.object(matter_device_base.MatterDeviceBase, "matter_endpoints")
  @mock.patch.object(matter_device_base.MatterDeviceBase, "device_power")
  def test_check_rpc_working_on_failure_power_cycling(
      self, mock_device_power, mock_endpoints):
    """Verifies check_rpc_working on failure with power cycling."""
    mock_endpoints.list.side_effect = errors.DeviceError("error")
    mock_device_power.healthy = True
    self.uut.check_rpc_working()
    mock_device_power.cycle.assert_called_once()

  @mock.patch.object(matter_device_base.MatterDeviceBase, "matter_endpoints")
  @mock.patch.object(matter_device_base.MatterDeviceBase, "device_power")
  def test_check_rpc_working_on_failure_power_cycling_fails(
      self, mock_device_power, mock_endpoints):
    """Verifies check_rpc_working with power cycling failure."""
    mock_endpoints.list.side_effect = errors.DeviceError("error")
    mock_device_power.healthy = False
    self.uut.check_rpc_working()
    mock_device_power.cycle.assert_not_called()

  def test_device_usb_hub_name_property(self):
    """Verifies device_usb_hub_name property getter."""
    self.uut.props["persistent_identifiers"]["device_usb_hub_name"] = "usb-hub"
    self.assertEqual(self.uut.device_usb_hub_name, "usb-hub")

  def test_device_usb_port_property(self):
    """Verifies device_usb_port property getter."""
    self.uut.props["persistent_identifiers"]["device_usb_port"] = "1"
    self.assertEqual(self.uut.device_usb_port, "1")

  def test_comm_power_hub_name_property(self):
    """Verifies comm_power_hub_name property getter."""
    self.uut.props["optional"]["comm_power_hub_name"] = "fake-comm-power-hub"
    self.assertEqual(self.uut.comm_power_hub_name, "fake-comm-power-hub")

  def test_comm_power_port_property(self):
    """Verifies comm_power_port property getter."""
    self.uut.props["optional"]["comm_power_port"] = "4"
    self.assertEqual(self.uut.comm_power_port, "4")

  def test_device_power_persistent_hub_name_selection(self):
    """Verifies device_power uses persistent hub if optional hub is not set."""
    persistent_ids = self.uut.props["persistent_identifiers"]
    persistent_ids["device_usb_hub_name"] = "persistent-hub"
    persistent_ids["device_usb_port"] = 1
    self.uut.props["optional"]["comm_power_hub_name"] = None
    self.uut.props["optional"]["comm_power_port"] = None

    with mock.patch.object(
        self.uut, "lazy_init", autospec=True
    ) as mock_lazy_init:
      _ = self.uut.device_power
      mock_lazy_init.assert_called_with(
          device_power_default.DevicePowerDefault,
          device_name=self.uut.name,
          get_manager=self.uut.get_manager,
          default_hub_type="cambrionix",
          props=self.uut.props,
          usb_ports_discovered=True,
          get_switchboard_if_initialized=(
              self.uut._get_switchboard_if_initialized),
          wait_until_connected_fn=self.uut.wait_until_connected,
          wait_for_bootup_complete_fn=self.uut.wait_for_bootup_complete,
          usb_hub_name_prop="device_usb_hub_name",
          usb_port_prop="device_usb_port")

  def test_device_power_optional_hub_name_selection(self):
    """Verifies device_power uses optional hub name if set."""
    self.uut.props["optional"]["comm_power_hub_name"] = "optional-hub"
    self.uut.props["optional"]["comm_power_port"] = 2

    with mock.patch.object(
        self.uut, "lazy_init", autospec=True
    ) as mock_lazy_init:
      _ = self.uut.device_power
      mock_lazy_init.assert_called_with(
          device_power_default.DevicePowerDefault,
          device_name=self.uut.name,
          get_manager=self.uut.get_manager,
          default_hub_type="cambrionix",
          props=self.uut.props,
          usb_ports_discovered=True,
          get_switchboard_if_initialized=(
              self.uut._get_switchboard_if_initialized),
          wait_until_connected_fn=self.uut.wait_until_connected,
          wait_for_bootup_complete_fn=self.uut.wait_for_bootup_complete,
          usb_hub_name_prop="comm_power_hub_name",
          usb_port_prop="comm_power_port")

  @mock.patch.object(console_config, "get_log_only_configuration")
  def test_get_console_configuration_on_success(self, mock_console_config):
    """Verifies get_console_configuration on success."""
    config = self.uut.get_console_configuration()
    self.assertIsNotNone(config)
    mock_console_config.assert_called_once()

  @mock.patch.object(matter_device_base.os.path, "exists", return_value=True)
  def test_is_connected_true(self, mock_exists):
    """Verifies is_connected returns true when console port exists."""
    self.assertTrue(
        matter_device_base.MatterDeviceBase.is_connected(self.device_config))
    mock_exists.assert_called_once()

  @mock.patch.object(
      matter_device_base.MatterDeviceBase, "matter_endpoints")
  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "get_endpoint_instance_by_class",
      return_value=_FAKE_ENDPOINT_INST)
  def test_get_detection_info_on_success(
      self,
      mock_get_endpoint_instance_by_class,
      mock_matter_endpoints):
    """Verifies persistent properties are set correctly."""
    self._test_get_detection_info(
        console_port_name=_FAKE_DEVICE_ADDRESS,
        device_class=matter_device_base_stub.MatterDeviceBaseStub,
        persistent_properties=_CONNECT_PERSISTENT_PROPERTIES)

  def test_matter_endpoints_capability(self):
    """Verifies the initialization of matter_endpoints capability."""
    self.assertIsNotNone(self.uut.matter_endpoints)

  def test_device_power_capability(self):
    """Verifies the initialization of device_power capability."""
    self.assertIsNotNone(self.uut.device_power)

  @mock.patch.object(
      device_power_default.DevicePowerDefault, "cycle", autospec=True)
  def test_device_reboot_hard(self, reboot_fn):
    """Verifies the hard reboot on success."""
    self.uut.reboot(method="hard")
    reboot_fn.assert_called_once()

  @parameterized.parameters(dict(method="soft"), dict(method="pw_rpc"))
  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "reboot", autospec=True)
  def test_device_reboot(self, reboot_fn, method):
    """Verifies the soft reboot on success."""
    self.uut.reboot(method)
    reboot_fn.assert_called_once()

  def test_device_reboot_raise_error(self):
    """Verifies reboot method with invalid method."""
    with self.assertRaisesRegex(
        errors.DeviceError,
        r"ValueError: Method invalid_reboot_method not recognized"):
      self.uut.reboot(method="invalid_reboot_method")

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "software_version",
      new_callable=mock.PropertyMock,
      return_value=_FAKE_FIRMWARE_VERSION)
  def test_get_firmware_version_on_success(self, unused_mock_sw_version):
    """Verifies get firmware_version on success."""
    self.assertEqual(self.uut.firmware_version, _FAKE_FIRMWARE_VERSION)

  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "get_endpoint_class_and_device_type_id",
      return_value=(
          mock.Mock(DEVICE_TYPE_NAME=_FAKE_ENDPOINT_NAME),
          _FAKE_DEVICE_TYPE_ID,
      ),
      autospec=True,
  )
  def test_get_firmware_type_on_success(
      self, unused_mock_get_endpoint_class_and_device_type_id
  ):
    self.assertEqual(self.uut.firmware_type, _FAKE_ENDPOINT_NAME)

  @mock.patch.object(pwrpc_common_default.PwRPCCommonDefault, "reboot")
  def test_reboot_on_success(self, mock_reboot):
    """Verifies reboot on success."""
    self.uut.reboot()
    mock_reboot.assert_called_once()

  @mock.patch.object(pwrpc_common_default.PwRPCCommonDefault, "factory_reset")
  def test_factory_reset_on_success(self, mock_factory_reset):
    """Verifies factory reset on success."""
    self.uut.factory_reset()
    mock_factory_reset.assert_called_once()

  def test_common_rpc_capability_initialization_success(self):
    """Verifies the initialization of pw_rpc_common capability."""
    self.assertIsNotNone(self.uut.pw_rpc_common)

  def test_shell_not_implemented(self):
    """Verifies the shell method not implemented."""
    error_regex = "shell not implemented."
    with self.assertRaisesRegex(errors.DeviceError, error_regex):
      self.uut.shell(command=_FAKE_COMMAND)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault, "wait_for_bootup_complete")
  def test_wait_for_bootup_complete_on_success(
      self, mock_wait_for_bootup_complete):
    """Verifies the wait_for_bootup_complete on success."""
    self.uut.wait_for_bootup_complete()
    mock_wait_for_bootup_complete.assert_called_once()

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "pairing_info",
      new_callable=mock.PropertyMock)
  def test_get_pairing_code_on_success(self, mock_pairing_info):
    """Verifies get pairing_code on success."""
    fake_pairing_code = mock.Mock(code=_FAKE_PAIRING_CODE)
    mock_pairing_info.return_value = fake_pairing_code
    self.assertEqual(self.uut.pairing_code, _FAKE_PAIRING_CODE)

  @mock.patch.object(
      pwrpc_common_default.PwRPCCommonDefault,
      "pairing_info",
      new_callable=mock.PropertyMock)
  def test_get_pairing_discriminator_on_success(self, mock_pairing_info):
    """Verifies get pairing_discriminator on success."""
    fake_discriminator = mock.Mock(discriminator=_FAKE_PAIRING_DISCRIMINATOR)
    mock_pairing_info.return_value = fake_discriminator
    self.assertEqual(
        self.uut.pairing_discriminator, _FAKE_PAIRING_DISCRIMINATOR)

  @mock.patch.object(matter_device_base.MatterDeviceBase, "pw_rpc_common")
  def test_pairing_state(self, fake_pw_rpc_common):
    """Verifies pairing_state on success."""
    fake_pw_rpc_common.pairing_state = True
    self.assertTrue(self.uut.pairing_state)

  @mock.patch.object(matter_device_base.MatterDeviceBase, "pw_rpc_common")
  def test_qr_code(self, fake_pw_rpc_common):
    """Verifies get qr_code on success."""
    fake_pw_rpc_common.qr_code = _FAKE_QR_CODE
    self.assertEqual(_FAKE_QR_CODE, self.uut.qr_code)

  @mock.patch.object(matter_device_base.MatterDeviceBase, "pw_rpc_common")
  def test_qr_code_url(self, fake_pw_rpc_common):
    """Verifies get qr_code_url on success."""
    fake_pw_rpc_common.qr_code_url = _FAKE_QR_CODE_URL
    self.assertEqual(_FAKE_QR_CODE_URL, self.uut.qr_code_url)

  def test_pw_rpc_button_capability(self):
    """Verifies the initialization of pw_rpc_button capability."""
    self.assertIsNotNone(self.uut.pw_rpc_button)

  def test_pw_rpc_event_subscription_capability(self):
    """Verifies the initialization of pw_rpc_event_subscription capability."""
    self.assertIsNotNone(self.uut.pw_rpc_event_subscription)


if __name__ == "__main__":
  fake_device_test_case.main()
