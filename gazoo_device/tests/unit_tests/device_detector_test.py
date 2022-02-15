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

"""Unit tests for device detector."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device import detect_criteria
from gazoo_device import device_detector
from gazoo_device import extensions
from gazoo_device import manager
from gazoo_device.auxiliary_devices import cambrionix
from gazoo_device.auxiliary_devices import raspberry_pi
from gazoo_device.switchboard import communication_types
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import fake_devices
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import host_utils

_CAMBRIONIX_PORT = (
    "/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DJ00JMN0-if00-port0")


class _FakeManager:
  """Provides stubbed out manager."""

  def __init__(self):
    self._open_devices = {}

  def create_switchboard(self, *args, **kwargs):
    del args, kwargs  # Unused.
    return mock.MagicMock(spec=switchboard.SwitchboardDefault)


class TestDeviceDetector(unit_test_case.UnitTestCase):
  """Tests for device_detector.py."""

  def setUp(self):
    super().setUp()
    self.fake_manager = _FakeManager()
    aux_devices = manager.Manager.get_supported_auxiliary_device_classes()
    self.detector = device_detector.DeviceDetector(
        manager=self.fake_manager,
        log_directory=self.artifacts_directory,
        persistent_configs={
            "devices": {},
            "other_devices": {}
        },
        options_configs={
            "device_options": {},
            "other_device_options": {}
        },
        supported_auxiliary_device_classes=aux_devices)
    self.maxDiff = None  # pylint: disable=invalid-name
    self.mock_out_usb_utils_methods()
    extensions.primary_devices.append(fake_devices.FakeSSHDevice)
    extensions.primary_devices.append(fake_devices.FakePtyDevice)

  def tearDown(self):
    extensions.primary_devices.remove(fake_devices.FakePtyDevice)
    extensions.primary_devices.remove(fake_devices.FakeSSHDevice)
    super().tearDown()

  def test_001_get_known_connections(self):
    """Tests that _create_known_connections returns correct connections.

    FTDI ports should have -if00-port0 removed.
    """
    self.detector.persistent_configs = {
        "devices": {
            "sshdevice-1234": {
                "console_port_name": "12.34.56.10"
            },
            "sshdevice-5678": {
                "console_port_name": "12.34.56.20"
            },
        },
        "other_devices": {
            "cambrionix-5678": {
                "hub_port_name": _CAMBRIONIX_PORT
            },
            "yepkit-1234": {
                "hub_port_name": "12345678"
            }
        }
    }
    known_connections = self.detector._create_known_connections()
    self.assertCountEqual(
        known_connections,
        ["12.34.56.10", "12.34.56.20", "12345678", _CAMBRIONIX_PORT])

  def test_03_filter_out_known_connections(self):
    """Tests that _filter_out_known_connections filters out connections."""
    con_dict = {
        "SshComms": ["12.34.56.10", "12.34.56.20"],
        "AdbComms": ["12.34.56.20:5555"],
        "YepkitComms": [],
        "SerialComms": [_CAMBRIONIX_PORT],
    }
    known_con = [
        "12.34.56.10",
        _CAMBRIONIX_PORT
    ]

    expected_new_con = {
        "SshComms": ["12.34.56.20"],
        "AdbComms": ["12.34.56.20:5555"],
        "YepkitComms": [],
        "SerialComms": []
    }

    new_con_dict = self.detector._filter_out_known_connections(
        con_dict, known_con)
    self.assertEqual(expected_new_con, new_con_dict)

  @mock.patch.object(detect_criteria, "find_matching_device_class")
  @mock.patch.object(host_utils, "is_pingable", return_value=True)
  def test_04_identify_connection_device_class(self, mock_ping,
                                               mock_matching_class):
    """Tests _identify_connection_device_class."""
    address_to_class_list = {
        "12.34.56.10": [fake_devices.FakeSSHDevice],
        _CAMBRIONIX_PORT: [cambrionix.Cambrionix],
        "/dev/serial/by-id/usb-FTDI_Gobbly_59cead45-if02-port0": [],
        "12.34.56.10:5555": []
    }

    def mock_match(address, *args, **kwargs):
      del args, kwargs  # Unused.
      return address_to_class_list[address]

    mock_matching_class.side_effect = mock_match
    con_dict = {
        "SshComms": ["12.34.56.10"],
        "AdbComms": ["12.34.56.10:5555"],
        "YepkitComms": [],
        "SerialComms": [
            _CAMBRIONIX_PORT,
            "/dev/serial/by-id/usb-FTDI_Gobbly_59cead45-if02-port0",
        ]
    }

    expected_response = [
        (fake_devices.FakeSSHDevice, "12.34.56.10"),
        (cambrionix.Cambrionix, _CAMBRIONIX_PORT)
    ]

    unidentified_connections = [
        "/dev/serial/by-id/usb-FTDI_Gobbly_59cead45-if02-port0",
        "12.34.56.10:5555"
    ]

    potential_tuples, _, no_id_cons = (
        self.detector._identify_connection_device_class(con_dict))
    self.assertCountEqual(potential_tuples, expected_response)
    self.assertCountEqual(no_id_cons, unidentified_connections)

  @mock.patch.object(
      detect_criteria,
      "find_matching_device_class",
      return_value=[fake_devices.FakeSSHDevice, raspberry_pi.RaspberryPi])
  @mock.patch.object(host_utils, "is_pingable", return_value=True)
  def test_04_identify_connection_works_with_multiple_matches(
      self, mock_ping, mock_matching_class):
    """Tests _identify_connection_device_class() with multiple matches."""
    con_dict = {"SshComms": ["12.34.56.10"]}
    expected_response = [(fake_devices.FakeSSHDevice, "12.34.56.10")]

    potential_tuples, _, _ = self.detector._identify_connection_device_class(
        con_dict)
    self.assertEqual(potential_tuples, expected_response)

  @mock.patch.object(
      fake_devices.FakeSSHDevice,
      "get_detection_info",
      return_value=({
          "console_port_name": "12.34.56.123",
          "serial_number": "12345678",
          "name": "\tdetect_sshdevice",
          "device_type": "sshdevice",
      }, {}))
  @mock.patch.object(fake_devices.FakeSSHDevice, "make_device_ready")
  def test_10_get_info_success(self, mock_make_device, mock_get_info):
    """Tests _detect_get_info() success."""
    name, persistent_props, optional_props = self.detector._detect_get_info(
        fake_devices.FakeSSHDevice, "12.34.56.123")
    self.assertEqual(name, "sshdevice-5678")
    self.assertEqual(
        persistent_props, {
            "console_port_name": "12.34.56.123",
            "serial_number": "12345678",
            "device_type": "sshdevice",
            "name": "sshdevice-5678",
        })
    self.assertEqual(optional_props, {})

  def test_15_add_to_configs_success(self):
    """Tests _add_to_configs for a primary device."""
    self.detector._add_to_configs(fake_devices.FakeSSHDevice, "sshdevice-1234",
                                  {"console_port_name": "12.34.56.10"}, {})

    self.assertIn(
        "sshdevice-1234", self.detector.persistent_configs["devices"])
    self.assertIn(
        "sshdevice-1234", self.detector.options_configs["device_options"])

    self.assertEqual(
        {"console_port_name": "12.34.56.10"},
        self.detector.persistent_configs["devices"]["sshdevice-1234"])

    # Ensure universal options get placed in options
    self.assertEqual(
        {
            "alias": None,
            "usb_port": None,
            "usb_hub": None,
            "location": None,
            "power_switch": None,
            "power_port": None
        },
        self.detector.options_configs["device_options"]["sshdevice-1234"])

  def test_16_add_to_configs_other_success(self):
    """Tests _add_to_configs for an auxiliary device."""
    self.detector.persistent_configs = {
        "devices": {
            "sshdevice-6678": {
                "console_port_name": "12.34.56.10"
            },
        },
        "other_devices": {
            "cambrionix-5678": {
                "hub_port_name": _CAMBRIONIX_PORT
            },
            "yepkit-1234": {
                "hub_port_name": "12345678"
            }
        }
    }

    self.detector._add_to_configs(cambrionix.Cambrionix, "cambrionix-1234",
                                  {"hub_port_name": "56785678"},
                                  {"alias": None})

    self.assertIn("cambrionix-1234",
                  self.detector.persistent_configs["other_devices"])
    self.assertIn("cambrionix-1234",
                  self.detector.options_configs["other_device_options"])

    self.assertDictEqual(
        {"hub_port_name": "56785678"},
        self.detector.persistent_configs["other_devices"]["cambrionix-1234"])

    # Ensure universal options get placed in options
    self.assertDictEqual({
        "alias": None
    }, self.detector.options_configs["other_device_options"]["cambrionix-1234"])

  @parameterized.named_parameters(
      ("success_short_name_primary_device", "sshdevice", "56781234",
       fake_devices.FakeSSHDevice, "sshdevice-1234"),
      ("success_short_name_auxiliary_device", "cambrionix", "12345678",
       cambrionix.Cambrionix, "cambrionix-5678"),
      ("success_long_name_primary_device", "sshdevice", "12345678",
       fake_devices.FakeSSHDevice, "sshdevice-12345678"),
      ("failure_serial_number_too_short", "sshdevice", "123",
       fake_devices.FakeSSHDevice, None))
  def test_generate_name(
      self, device_type, serial_number, device_class, expected_name):
    """Tests _generate_name() for a successful scenario."""
    self.detector.persistent_configs = {
        "devices": {
            "sshdevice-5678": {
                "serial_number": "22345678"
            }
        },
        "other_devices": {
            "cambrionix-5678": {
                "serial_number": "12345678"
            }
        }
    }

    if expected_name is None:
      with self.assertRaisesRegex(RuntimeError, "too short"):
        self.detector._generate_name(device_type, serial_number, device_class)
    else:
      name = self.detector._generate_name(
          device_type, serial_number, device_class)
      self.assertEqual(name, expected_name)

  def test_25_print_summary(self):
    """Tests _print_summary."""
    new_names = ["sshdevice-1234", "cambrionix-1234"]
    errs = []
    no_id_conns = ["123.14.167.123", "adb_serial1"]
    self.detector._print_summary(new_names, errs, no_id_conns)

  @mock.patch.object(
      cambrionix.Cambrionix,
      "get_detection_info",
      side_effect=RuntimeError("Unable to communicate"))
  @mock.patch.object(cambrionix.Cambrionix, "make_device_ready")
  @mock.patch.object(
      fake_devices.FakeSSHDevice,
      "get_detection_info",
      return_value=({
          "serial_number": "12345678",
          "device_type": "sshdevice",
          "console_port_name": "12.34.56.78"
      }, {}))
  @mock.patch.object(fake_devices.FakeSSHDevice, "make_device_ready")
  def test_30_detect_new_devices(
      self, mock_sshdevice_make, mock_sshdevice_get_info,
      mock_cambrionix_make, mock_cambrionix_get_info):
    """Tests that detect_new_devices detects devices and handles errors."""
    connections = {
        "SshComms": ["12.34.56.78"],
        "SerialComms": [_CAMBRIONIX_PORT],
    }

    persistent_configs, option_configs = self.detector.detect_new_devices(
        connections)
    self.assertCountEqual(["sshdevice-5678"], persistent_configs["devices"])
    self.assertCountEqual(["sshdevice-5678"], option_configs["device_options"])
    # cambrionix-0123 should not be detected because it raises an error.
    self.assertFalse(persistent_configs["other_devices"])
    self.assertFalse(option_configs["other_device_options"])

  @mock.patch.object(
      cambrionix.Cambrionix,
      "get_detection_info",
      return_value=({
          "serial_number": "01230123",
          "device_type": "cambrionix",
          "console_port_name": _CAMBRIONIX_PORT,
      }, {}))
  @mock.patch.object(cambrionix.Cambrionix, "make_device_ready")
  @mock.patch.object(
      fake_devices.FakeSSHDevice,
      "get_detection_info",
      return_value=({
          "serial_number": "12345678",
          "device_type": "sshdevice",
          "console_port_name": "12.34.56.78"
      }, {}))
  @mock.patch.object(fake_devices.FakeSSHDevice, "make_device_ready")
  def test_31_detect_all_new_devices(
      self, mock_sshdevice_make, mock_sshdevice_get_info,
      mock_cambrionix_make, mock_cambrionix_get_info):
    """Tests that detect_all_new_devices detects devices and handles errors."""
    connections = {
        "SerialComms": [_CAMBRIONIX_PORT],
        "SshComms": []
    }

    with mock.patch.object(
        communication_types, "detect_connections", return_value=connections):
      persistent_configs, option_configs = self.detector.detect_all_new_devices(
          )

    self.assertCountEqual(
        ["cambrionix-0123"], persistent_configs["other_devices"])
    self.assertCountEqual(
        ["cambrionix-0123"], option_configs["other_device_options"])
    # sshdevice-5678 should not be detected as static IP has not been provided.
    self.assertFalse(persistent_configs["devices"])
    self.assertFalse(option_configs["device_options"])

  @mock.patch.object(
      cambrionix.Cambrionix,
      "get_detection_info",
      return_value=({
          "serial_number": "01230123",
          "device_type": "cambrionix",
          "console_port_name": _CAMBRIONIX_PORT,
      }, {}))
  @mock.patch.object(cambrionix.Cambrionix, "make_device_ready")
  @mock.patch.object(
      fake_devices.FakeSSHDevice,
      "get_detection_info",
      return_value=({
          "serial_number": "22345678",
          "device_type": "sshdevice",
          "console_port_name": "123.17.123.12"
      }, {}))
  @mock.patch.object(fake_devices.FakeSSHDevice, "make_device_ready")
  @mock.patch.object(detect_criteria, "find_matching_device_class")
  def test_32_detect_all_new_devices_with_static_ips(
      self, mock_matching_class, mock_sshdevice_make, mock_sshdevice_get_info,
      mock_cambrionix_make, mock_cambrionix_get_info):
    """Tests detect_all_new_devices with provided static_ips."""
    address_to_class_list = {
        _CAMBRIONIX_PORT: [cambrionix.Cambrionix],
        "/dev/serial/by-id/usb-FTDI_Gobbly_59cead44-if02-port0": [],
        "123.17.123.12": [fake_devices.FakeSSHDevice],
    }
    connections = {
        "SerialComms": [
            _CAMBRIONIX_PORT,
            "/dev/serial/by-id/usb-FTDI_Gobbly_59cead44-if02-port0",
        ],
        "SshComms": ["123.17.123.12"],
    }
    static_ips = ["123.17.123.12", "123.17.124.10"]

    def mock_match(address, *args, **kwargs):
      del args, kwargs  # Unused.
      return address_to_class_list[address]

    mock_matching_class.side_effect = mock_match

    with mock.patch.object(
        communication_types, "detect_connections", return_value=connections):
      persistent_configs, option_configs = self.detector.detect_all_new_devices(
          static_ips)
    self.assertCountEqual(["sshdevice-5678"], persistent_configs["devices"])
    self.assertCountEqual(["sshdevice-5678"], option_configs["device_options"])
    self.assertCountEqual(
        ["cambrionix-0123"], persistent_configs["other_devices"])
    self.assertCountEqual(
        ["cambrionix-0123"], option_configs["other_device_options"])

  @mock.patch.object(
      fake_devices.FakePtyDevice,
      "get_detection_info",
      return_value=({
          "console_port_name": "some_dir/some_binary --some_arg",
          "device_type": "ptydevice",
          "name": "ptydevice-5678",
          "serial_number": "12345678",
      }, {}))
  @mock.patch.object(
      device_detector.pty_process_utils,
      "get_launch_command",
      return_value="some_dir/some_binary --some_arg")
  @mock.patch.object(fake_devices.FakePtyDevice, "make_device_ready")
  def test_33_get_info_pty_process_comms(self,
                                         mock_make_device,
                                         mock_get_launch_command,
                                         mock_get_detection_info):
    """Tests that get_info succeeds with PtyProcessComms device type."""
    name, persistent_props, optional_props = self.detector._detect_get_info(
        fake_devices.FakePtyDevice, "some_dir/some_binary --some_arg")
    self.assertEqual(name, "ptydevice-5678")
    self.assertEqual(
        persistent_props, {
            "console_port_name": "some_dir/some_binary --some_arg",
            "serial_number": "12345678",
            "device_type": "ptydevice",
            "name": "ptydevice-5678",
        })
    self.assertEqual(optional_props, {})


if __name__ == "__main__":
  unit_test_case.main()
