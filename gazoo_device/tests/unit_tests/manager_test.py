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
"""This test script verifies GDM is working with Manager."""
import atexit
import builtins
import collections
import copy
import datetime
import gc
import json
import logging
import os
import shutil
import signal
from unittest import mock

from absl.testing import parameterized
from gazoo_device import config as config_gdm
from gazoo_device import data_types
from gazoo_device import decorators
from gazoo_device import device_detector
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import gdm_logger
from gazoo_device import log_parser
from gazoo_device import manager
from gazoo_device.auxiliary_devices import cambrionix
from gazoo_device.capabilities import switch_power_usb_with_charge
from gazoo_device.switchboard import communication_types
from gazoo_device.switchboard import log_process
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import fake_devices
from gazoo_device.tests.unit_tests.utils import fake_transport
from gazoo_device.tests.unit_tests.utils import gc_test_utils
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import host_utils
from gazoo_device.utility import multiprocessing_utils
from gazoo_device.utility import usb_config

logger = gdm_logger.get_logger()
ANOTHER_MESSAGE_LINE = "{} [APPL] This is another message\n"
MAX_LOG_LINES = 10
NO_MATCH_LINE = "{} [BOOT] Non-matching line\n"
STATE_LINE = "{} [APPL] Some other message with group data {}\n"
_TEST_FILTER_FILE = "optional_description.json"
UNIQUE_MESSAGE_LINE = "{} [APPL] Some unique message\n"

FAKE_DEVICES = {
    "devices": {
        "sshdevice-0000": {
            "serial_number": "00000000",
            "name": "sshdevice-0000",
            "device_type": "sshdevice",
            "model": "linux",
            "console_port_name": "123.123.78.9"
        },
        "sshdevice-0001": {
            "serial_number": "00000001",
            "name": "sshdevice-0001",
            "device_type": "sshdevice",
            "model": "linux",
            "console_port_name": "123.123.78.0"
        },
    },
    "other_devices": {
        "cambrionix-1234": {
            "serial_number": "1234",
            "name": "cambrionix-1234",
            "device_type": "cambrionix",
            "model": "PP15S",
            "console_port_name":
                ("/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DJ00JMN0-if00"
                 "-port0"),
        }
    }
}

FAKE_DEVICE_OPTIONS = {
    "device_options": {
        "sshdevice-0000": {
            "alias": "linux",
        },
        "sshdevice-0001": {
            "alias": "linux2",
        },
    },
    "other_device_options": {
        "cambrionix-1234": {
            "alias": ""
        }
    }
}
DEFAULT_FILES = {
    "gdm_log_file_name": config_gdm.DEFAULT_LOG_FILE,
    "device_options_file_name": config_gdm.DEFAULT_OPTIONS_FILE,
    "device_file_name": config_gdm.DEFAULT_DEVICE_FILE,
    "testbeds_file_name": config_gdm.DEFAULT_TESTBEDS_FILE,
    "gdm_config_file_name": config_gdm.DEFAULT_GDM_CONFIG_FILE
}
USB_INFO_DICT = {
    "/dev/tty.usbserial-DJ00JMN0":
        usb_config.UsbInfo(
            vendor_id="0403",
            ftdi_interface=0,
            product_name="FT230X Basic UART",
            manufacturer="FTDI",
            disk="/dev/ttyUSB3",
            product_id="6015",
            serial_number="DJ00JMN0",
            address="/dev/tty.usbserial-DJ00JMN0"),
    "/dev/tty.usbserial-12345670":
        usb_config.UsbInfo(
            ftdi_interface=0,
            product_id="2460",
            serial_number="1234567",
            address="/dev/tty.usbserial-12345670"),
    "/dev/tty.usbserial-12345673":
        usb_config.UsbInfo(
            ftdi_interface=3,
            serial_number="1234567",
            address="/dev/tty.usbserial-12345673"),
    "360av3":
        usb_config.UsbInfo(
            serial_number="12345", address="360av3", product_name="Android")
}


def load_config(file_name, key=None):
  """Loads a json config from a file into a dict and returns the dict.

  Args:
      file_name: The json file path.
      key: The key is a string, and it indicate which dict entry caller is
        interested in.

  Returns:
      The return value depends on key value. If the key value is None,
      the whole dict will return to caller. If there's a key specified,
      returns just the entry from that key.
  Raises:
      ValueError: if file not found.
  """
  if not os.path.exists(file_name):
    raise ValueError(
        "Config file {} is not found. \n Current directory: {}".format(
            file_name, os.getcwd()))
  with open(file_name, "r") as open_file:
    try:
      conf = json.load(open_file)
    except Exception as err:
      raise RuntimeError("Unable to parse {} as a json file. Error: {}".format(
          file_name, str(repr(err))))
  if key is None:
    return conf
  if key not in conf:
    raise ValueError("{} is not an entry in {}".format(key, file_name))
  else:
    return conf[key]


def remove_file(filename):
  if filename is not None and os.path.isfile(filename):
    os.remove(filename)


def _create_dict(a_dict, file_path):
  with open(file_path, "w+") as open_file:
    json.dump(a_dict, open_file)


class DynamicWithSetter():
  """Mock device class with setter."""

  @decorators.DynamicProperty
  def dynamic_property(self):
    pass

  @dynamic_property.setter
  def dynamic_property(self, value):
    pass

  def get_capability_name(self):
    return "DynamicWithSetter"


class DynamicWithOutSetter():
  """Mock device class without setter."""

  @decorators.DynamicProperty
  def dynamic_property(self):
    pass

  def get_capability_name(self):
    return "DynamicWithOutSetter"


class MockOutDevices:
  """Mocks out Devices used in testing."""

  def __init__(self):
    self.patchs = []
    self.patchs.append(
        mock.patch.object(
            fake_devices.FakeSSHDevice, "is_connected", return_value=True))
    self.patchs.append(
        mock.patch.object(
            cambrionix.Cambrionix, "is_connected", return_value=True))
    self.patchs.append(
        mock.patch.object(cambrionix.Cambrionix, "make_device_ready"))
    self.patchs.append(
        mock.patch.object(fake_devices.FakeSSHDevice, "make_device_ready"))
    self.patchs.append(
        mock.patch.object(fake_devices.FakeSSHDevice, "check_device_ready"))
    self.patchs.append(
        mock.patch.object(cambrionix.Cambrionix, "check_device_ready"))
    self.patchs.append(mock.patch.object(cambrionix.Cambrionix, "_command"))
    self.patchs.append(
        mock.patch.object(
            cambrionix.Cambrionix, "_get_system_hardware",
            return_value="PP15S"))

  def __enter__(self):
    for patcher in self.patchs:
      patcher.start()
    return self

  def __exit__(self, a_type, value, trace):
    for patcher in self.patchs:
      patcher.stop()


def populate_config_files(artifacts_directory):
  """Create fake gdm config files."""
  config_folder = os.path.join(artifacts_directory, "fake_configs")
  if os.path.exists(config_folder):
    shutil.rmtree(config_folder)
  os.mkdir(config_folder)
  fake_gdm_config = {
      "device_file_name": os.path.join(config_folder, "c.json"),
      "device_options_file_name": os.path.join(config_folder, "d.json"),
      "testbeds_file_name": os.path.join(config_folder, "e.json"),
      "log_directory": artifacts_directory
  }
  files = {
      "gdm_log_file_name":
          os.path.join(config_folder, "gdm.txt"),
      "device_options_file_name":
          os.path.join(config_folder, "device_options.json"),
      "device_file_name":
          os.path.join(config_folder, "devices.json"),
      "testbeds_file_name":
          os.path.join(config_folder, "testbeds.json"),
      "gdm_config_file_name":
          os.path.join(config_folder, "gdm.json"),
  }
  file_paths = list(files.values()) + list(fake_gdm_config.values())
  for file_path in file_paths:
    if file_path == artifacts_directory:
      continue
    with open(file_path, "w+") as open_file:
      open_file.write("")
  _create_dict(FAKE_DEVICES, files["device_file_name"])
  _create_dict(FAKE_DEVICE_OPTIONS, files["device_options_file_name"])
  _create_dict(fake_gdm_config, files["gdm_config_file_name"])
  _create_dict({"testbeds": {}}, files["testbeds_file_name"])
  _create_dict({}, fake_gdm_config["device_file_name"])
  _create_dict({}, fake_gdm_config["device_options_file_name"])
  _create_dict({"testbeds": {}}, fake_gdm_config["testbeds_file_name"])
  return fake_gdm_config, files


class ManagerTestsSetup(unit_test_case.UnitTestCase):
  """Common setup and helper methods for Manager & FireManager unit tests."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    extensions.primary_devices.append(fake_devices.FakeSSHDevice)

  @classmethod
  def tearDownClass(cls):
    extensions.primary_devices.remove(fake_devices.FakeSSHDevice)
    super().tearDownClass()

  def setUp(self):
    super().setUp()
    # Create fresh config files for each test.
    self.fake_gdm_config, self.files = populate_config_files(
        self.artifacts_directory)

    self.device_log_file = os.path.join(self.artifacts_directory,
                                        self._testMethodName + "-device.txt")
    self.event_file_name = log_process.get_event_filename(self.device_log_file)
    self.first_name = list(FAKE_DEVICES["devices"].keys())[0]
    self.second_name = list(FAKE_DEVICES["devices"].keys())[1]
    self.auxiliary_name = list(FAKE_DEVICES["other_devices"].keys())[0]
    self.uut = None

  def tearDown(self):
    if getattr(self, "uut"):
      self.uut.close()
    super().tearDown()

  def _create_log_file(self, event_count):
    """Creates a temporary log file for testing Parser event history commands.

    The temporary event history log file will contain event_count total events
    for each of the following raw log lines:
        * ANOTHER_MESSAGE_LINE
        * NO_MATCH_LINE
        * STATE_LINE
        * UNIQUE_MESSAGE_LINE
    Args:
        event_count (int): number of event relevant log line blocks to add to
          file.
    """
    with open(self.device_log_file, "w+") as log_file:
      for i in range(event_count):
        now = datetime.datetime.now()
        time_info = now.strftime("<%Y-%m-%d %H:%M:%S.%f>")
        log_file.write(ANOTHER_MESSAGE_LINE.format(time_info))
        log_file.write(NO_MATCH_LINE.format(time_info))
        log_file.write(STATE_LINE.format(time_info, i))
        log_file.write(UNIQUE_MESSAGE_LINE.format(time_info))


class ManagerTests(ManagerTestsSetup, gc_test_utils.GCTestUtilsMixin):
  """Unit tests for the manager.py module."""

  def test_manager_construct_destruct(self):
    """Test Manager constructing and destructing raises no errors."""
    uut = manager.Manager()
    del uut

  def test_manager_debug_level_INFO_sets_log_handler_level(self):
    self.uut = self._create_manager_object(debug_level=logging.INFO)
    self.assertEqual(self.uut.gdm_log_handler.level, logging.INFO)

  def test_manager_debug_level_DEVELOPER_sets_log_handler_level(self):
    self.uut = self._create_manager_object(debug_level="developer")
    self.assertEqual(self.uut.gdm_log_handler.level, logging.DEBUG)

  def test_manager_debug_level_DEBUG_sets_log_handler_level(self):
    self.uut = self._create_manager_object(debug_level=logging.DEBUG)
    self.assertEqual(self.uut.gdm_log_handler.level, logging.DEBUG)

  def test_manager_default_config_files_exist(self):
    """Verifying the default files passed to the manager exist on the host."""
    self.uut = self._create_manager_object()
    self.assertTrue(
        os.path.exists(config_gdm.DEFAULT_LOG_DIRECTORY),
        "DEFAULT_LOG_DIRECTORY {} does not exist".format(
            config_gdm.DEFAULT_LOG_DIRECTORY))
    self.assertTrue(
        os.path.exists(config_gdm.DEFAULT_GDM_CONFIG_FILE),
        "DEFAULT_GDM_CONFIG_FILE {} does not exist".format(
            config_gdm.DEFAULT_GDM_CONFIG_FILE))
    self.assertTrue(
        os.path.exists(config_gdm.DEFAULT_DEVICE_FILE),
        "DEFAULT_DEVICE_FILE {} does not exist".format(
            config_gdm.DEFAULT_DEVICE_FILE))
    self.assertTrue(
        os.path.exists(config_gdm.DEFAULT_OPTIONS_FILE),
        "DEFAULT_OPTIONS_FILE {} does not exist".format(
            config_gdm.DEFAULT_OPTIONS_FILE))
    self.assertTrue(
        os.path.exists(config_gdm.DEFAULT_TESTBEDS_FILE),
        "DEFAULT_TESTBEDS_FILE {} does not exist".format(
            config_gdm.DEFAULT_TESTBEDS_FILE))

  def test_manager_loads_default_config_files(self):
    """Verifying the manager correctly sets all the attributes passed in."""
    self.uut = manager.Manager(gdm_log_file="{}/{}_gdm.txt".format(
        self.artifacts_directory, self._testMethodName + "-2"))
    for key, value in DEFAULT_FILES.items():
      if key == "gdm_log_file_name":
        continue
      self.assertEqual(
          getattr(self.uut, key), value,
          ("Manager should have loaded {} ({}) from defaults but it didnt, "
           "Instead key is {}").format(key, value, getattr(self.uut, key)))

  def test_manager_constructor_accepts_custom_config_file(self):
    """Verifying manager overrides the defaults with gdm_config."""
    self.uut = manager.Manager(
        gdm_log_file="{}/{}_gdm.txt".format(self.artifacts_directory,
                                            self._testMethodName + "-2"),
        gdm_config_file_name=self.files["gdm_config_file_name"])
    for key, value in self.fake_gdm_config.items():
      self.assertEqual(
          str(getattr(self.uut, key)), str(value),
          ("Manager should have loaded {} from gdm_config_file. "
           "instead of {}, its {}").format(key, value, getattr(self.uut, key)))

  def test_manager_constructor_accepts_custom_arguments(self):
    """Verifying arguments override both gdm config and defaults."""
    self.uut = self._create_manager_object()
    for key, value in self.files.items():
      if key in ["device_log_file", "gdm_log_file_name", "testbeds_file_name"]:
        continue
      err_msg = ("Manager should have loaded {} from arguments. Instead of {}, "
                 "its {}").format(key, value, getattr(self.uut, key))
      self.assertEqual(str(getattr(self.uut, key)), str(value), err_msg)

  def test_manager_rejects_bad_log_directory_parameter(self):
    """Verifying error user provides a log_directory that doesn't exist."""
    fake_d = "/tmp/t/r/s"
    if os.path.exists(fake_d):
      self.fail("Cannot run test as bad directory {} exists".format(fake_d))
    with self.assertRaises(errors.DeviceError):
      manager.Manager(
          gdm_log_file="{}/{}_gdm.txt".format(self.artifacts_directory,
                                              self._testMethodName + "-2"),
          log_directory=fake_d)

  def test_manager_close_called_twice(self):
    """Test calling Manager.close() more than once closes devices correctly."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.uut.create_device("sshdevice-0000")
      self.assertTrue(self.uut.get_open_device_names())
      self.uut.close()
      self.assertFalse(self.uut.get_open_device_names())
      with mock.patch.object(fake_devices.FakeSSHDevice, "close",
                             autospec=True) as mock_close:
        self.uut.close()
        mock_close.assert_not_called()

  def test_manager_get_device_prop_bad_types_raises_error(self):
    """Testing a bad property types and characters that GDM forbids."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.logger.info("Testing a string with a space")
      with self.assertRaises(errors.DeviceError):
        self.uut.get_device_prop(self.first_name, "serial number")
      self.logger.info("Testing non-ascii characters")
      with self.assertRaisesRegex(errors.DeviceError,
                                  "contains illegal non-ascii characters"):
        self.uut.get_device_prop(self.first_name, "mango_emoji_🥭")
      self.logger.info("Testing integer on set-prop")
      with self.assertRaises(errors.DeviceError):
        self.uut.set_prop(self.first_name, 1, None)
      self.logger.info("Testing empty string on set-prop")
      with self.assertRaises(errors.DeviceError):
        self.uut.set_prop(self.first_name, "alias", "")
      self.logger.info("Testing a list on set-prop")
      with self.assertRaises(errors.DeviceError):
        self.uut.set_prop(self.first_name, "alias", ["alphabet"])
      self.logger.info("Testing a string with a tab")
      with self.assertRaises(errors.DeviceError):
        self.uut.set_prop(self.first_name, "alias", "BullsEye\t")
      self.logger.info("Testing a string with a return")
      with self.assertRaises(errors.DeviceError):
        self.uut.set_prop(self.first_name, "alias", "BullsEye\n")

  def test_manager_get_device_prop_bad_device_name_raises_error(self):
    """Testing giving the manager a bad device name will raise an error."""
    name_s = "sdkjfhskdjhf"
    self.uut = self._create_manager_object()
    with self.assertRaises(errors.DeviceError):
      self.uut.get_device_prop(name_s)

  def test_manager_get_device_prop_bad_prop_name_raises_error_(self):
    """Testing gdm raises error in get_device_prop."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      with self.assertRaises(AttributeError):
        self.uut.get_device_prop(self.first_name, "lskdfhsldkfjlskdjf")

  def test_manager_get_device_prop_method_raises_error(self):
    """Test get-prop reboot."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      with self.assertRaises(errors.DeviceError):
        self.uut.get_device_prop(self.first_name, "reboot")

  def test_manager_get_device_prop_dynamic_of_disconnected_raises_error(
      self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      with mock.patch.object(
          fake_devices.FakeSSHDevice,
          "make_device_ready",
          side_effect=errors.DeviceError("x")):
        with self.assertRaises(errors.DeviceError):
          self.logger.info(
              self.uut.get_device_prop(self.first_name, "firmware_version"))

  def test_manager_get_device_prop_manager_successful(self):
    """Testing gdm returns all types of properties."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.uut.get_device_prop("manager", "device_options_file_name")
      self.uut.get_device_prop("manager")

  def test_manager_get_device_prop_first_name(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.uut.get_device_prop(self.first_name, "alias")

  def test_manager_get_device_prop_persistent_successful(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.uut.get_device_prop(self.first_name, "serial_number")

  def test_manager_get_device_prop_dynamic_first_name(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      connected = self.uut.get_device_prop(self.first_name, "connected")
      self.assertTrue(
          connected,
          "Device is not reporting as connected in setup for dynamic property")
      self.uut.get_device_prop(self.first_name, "firmware_version")

  def test_manager_get_device_prop_with_non_name_identifier_successful(
      self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      old_alias = self.uut.get_device_prop(self.first_name, "alias")
      self.uut.set_prop(self.first_name, "alias", "test040")
      try:
        name_returned = self.uut.get_device_prop("test040", "name")
        self.assertEqual(name_returned, self.first_name)
      finally:
        self.uut.set_prop(self.first_name, "alias", old_alias)

  def test_manager_get_device_prop_none_successful(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.uut.get_device_prop("sshdevice-0001")

  def test_get_device_prop_with_all_aliases(self):
    """Verifies get-prop with different identifiers."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      for prop in ["serial_number", "alias", "communication_address"]:
        identifier = self.uut.get_device_prop(self.first_name, prop)
        self.uut.get_device_prop(identifier.upper(), "firmware_version")

  def test_manager_get_device_prop_auxiliary_name(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.uut.get_device_prop(self.auxiliary_name, "alias")

  def test_manager_get_device_prop_persistent_auxiliary_successful(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.uut.get_device_prop(self.auxiliary_name, "serial_number")

  def test_manager_get_device_prop_dynamic_auxiliary_name(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      connected = self.uut.get_device_prop(self.auxiliary_name, "connected")
      self.assertTrue(
          connected,
          "Device is not reporting as connected in setup for dynamic property")
      self.uut.get_device_prop(self.first_name, "firmware_version")

  def test_manager_set_prop_dynamic_raises_error(self):
    """Testing if set_prop doesn't overwrite dynamic prop."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      with self.assertRaisesRegex(errors.DeviceError, "dynamic"):
        self.uut.set_prop(self.first_name, "firmware_version",
                          "FAKE_FIRMWARE_VERSION")

  def test_manager_set_prop_persistent_raises_error(self):
    """Testing if set_prop doesn't overwrite dynamic prop."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      with self.assertRaisesRegex(errors.DeviceError, "persistent"):
        self.uut.set_prop(self.first_name, "serial_number",
                          "FAKE_SERIAL_NUMBER")

  def test_manager_set_prop_persistent_auxiliary_raises_error(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      with self.assertRaisesRegex(errors.DeviceError, "persistent"):
        self.uut.set_prop(self.auxiliary_name, "serial_number", "1234")

  def test_manager_set_prop_dynamic_auxiliary_raises_error(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      with self.assertRaisesRegex(errors.DeviceError, "dynamic"):
        self.uut.set_prop(self.auxiliary_name, "firmware_version", "1234")

  def test_manager_get_device_prop_custom_successful(self):
    """Testing if custom property can be retrieved."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.uut.set_prop(self.first_name, "gobbly", "gook")
      value = self.uut.get_device_prop(self.first_name, "gobbly")
      self.assertEqual(
          "gook", value,
          "Value 'gobbly' not set to gook for {}".format(self.first_name))
      device = self.uut.create_device(self.first_name)
      self.assertEqual(
          device.props["optional"]["gobbly"], value,
          "Optional property 'gobbly' not set to gook for {}".format(
              self.first_name))

  def test_manager_get_device_prop_custom_auxiliary_successful(self):
    """Testing if custom property can be retrieved."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.uut.set_prop(self.auxiliary_name, "gobbly", "gook")
      value = self.uut.get_device_prop(self.auxiliary_name, "gobbly")
      self.assertEqual(
          "gook", value,
          "Value 'gobbly' not set to gook for {}".format(self.first_name))
      device = self.uut.create_device(self.auxiliary_name)
      self.assertEqual(
          device.props["optional"]["gobbly"], value,
          "Optional property 'gobbly' not set to gook for {}".format(
              self.first_name))

  def test_manager_set_prop_string_successful(self):
    """Testing if set_prop works on strings."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      o_alias = self.uut.get_device_prop(self.first_name, "alias")
      n_alias = "StringName"
      try:
        self.uut.set_prop(self.first_name, "alias", n_alias)
        self.uut.reload_configuration()  # ensure it saved to file
        cur_alias = self.uut.get_device_prop(self.first_name, "alias")
        self.assertEqual(
            cur_alias, n_alias,
            "Did not successfully set alias in the device options file")
      finally:
        self.uut.set_prop(self.first_name, "alias", o_alias)

  def test_manager_set_prop_None_successful(self):
    """Testing if set_prop works on none."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      o_alias = self.uut.get_device_prop(self.first_name, "alias")
      n_alias = None
      try:
        self.uut.set_prop(self.first_name, "alias", n_alias)
        self.uut.reload_configuration()  # ensure it saved to file
        cur_alias = self.uut.get_device_prop(self.first_name, "alias")
        self.assertIsNone(
            cur_alias,
            "Did not successfully set alias in the device options file")
      finally:
        self.uut.set_prop(self.first_name, "alias", o_alias)

  def test_manager_set_prop_unicode_successful(self):
    """Testing if set_prop works with unicode."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      o_alias = self.uut.get_device_prop(self.first_name, "alias")
      try:
        self.uut.set_prop(self.first_name, "alias", u"UnicodeName")
        new_alias = self.uut.get_device_prop(self.first_name, "alias")
        self.assertIsInstance(
            new_alias, str,
            "Manager did not convert set unicode property into a string")
      finally:
        self.uut.set_prop(self.first_name, "alias", o_alias)

  def test_manager_set_prop_manager_successful(self):
    """Modify manager config and ensure its written to file."""
    manager_test_path = "/fake/manager/path/and/config.json"
    self.uut = self._create_manager_object()
    original_config = load_config(self.uut.gdm_config_file_name)
    # test manager path
    try:
      for config_name in original_config.keys():
        self.uut.set_prop("manager", config_name, manager_test_path)
      modified_config = load_config(self.uut.gdm_config_file_name)
      for key in original_config.keys():
        self.assertEqual(
            modified_config[key], manager_test_path,
            "{} is not equal to {}".format(modified_config[key],
                                           manager_test_path))
    finally:
      _create_dict(original_config, self.uut.gdm_config_file_name)

  def test_manager_set_prop_custom_successful(self):
    """Testing if set_prop works for new property."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.uut.set_prop(self.first_name, "gobbly", "gook")

  def test_set_and_get_from_open_device(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      device = self.uut.create_device(self.first_name)
      self.assertTrue(
          self.uut.get_device_prop(self.first_name, "serial_number"))
      # Device is not closed by action
      self.assertIn(device.name, self.uut.get_open_device_names())
      self.assertIsNone(self.uut.set_prop(self.first_name, "alias", "phony"))
      self.assertIn(device.name, self.uut.get_open_device_names())
      device.close()

  def test_manager_set_prop_dynamic_base_class_no_setter(self):
    """Test manager setting a dynamic property fails if there is no setter."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      # Test with on a dynamic property without setter
      with mock.patch.object(
          fake_devices.FakeSSHDevice,
          "file_transfer",
          DynamicWithOutSetter(),
          spec_set=True):
        device = self.uut.create_device("sshdevice-0000")
        with mock.patch.object(
            device,
            "get_dynamic_property_names",
            return_value=["file_transfer.dynamic_property"]):
          with self.assertRaises(errors.DeviceError):
            self.uut.set_prop("sshdevice-0000",
                              "file_transfer.dynamic_property", 22)

  def test_manager_set_prop_dynamic_base_class(self):
    """Test manager setting a dynamic property works if there is a setter."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      # Test with on a dynamic property with a setter
      with mock.patch.object(
          fake_devices.FakeSSHDevice,
          "file_transfer",
          DynamicWithSetter(),
          spec_set=True):
        device = self.uut.create_device("sshdevice-0000")
        with mock.patch.object(
            device,
            "get_dynamic_property_names",
            return_value=["file_transfer.dynamic_property"]):
          self.uut.set_prop("sshdevice-0000", "file_transfer.dynamic_property",
                            22)

  def test_manager_set_prop_dynamic_auxiliary_class_no_setter(self):
    """Test manager setting a dynamic property fails if there is no setter."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      # Test with on a dynamic property without setter
      with mock.patch.object(
          cambrionix.Cambrionix,
          "switch_power",
          DynamicWithOutSetter(),
          spec_set=True):
        z = self.uut.create_device("cambrionix-1234")
        with mock.patch.object(
            z,
            "get_dynamic_property_names",
            return_value=["switch_power.dynamic_property"]):
          with self.assertRaises(errors.DeviceError):
            self.uut.set_prop("cambrionix-1234",
                              "switch_power.dynamic_property", 22)

  def test_manager_set_prop_dynamic_auxiliary_class(self):
    """Test manager setting a dynamic property works if there is a setter."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      # Test with on a dynamic property with a setter
      with mock.patch.object(
          cambrionix.Cambrionix,
          "switch_power",
          DynamicWithSetter(),
          spec_set=True):
        dut = self.uut.create_device("cambrionix-1234")
        with mock.patch.object(
            dut,
            "get_dynamic_property_names",
            return_value=["switch_power.dynamic_property"]):
          self.uut.set_prop("cambrionix-1234", "switch_power.dynamic_property",
                            22)

  def test_manager_remove_prop_persistent_raises_error(self):
    """Testing remove_prop does not remove persistent properties."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      with self.assertRaises(errors.DeviceError):
        self.uut.remove_prop(self.first_name, "serial_number")

  def test_manager_remove_prop_manager_raises_error(self):
    """Testing remove_prop does not remove manager properties."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      with self.assertRaises(errors.DeviceError):
        self.uut.remove_prop("manager", "gdm_config_file_name")

  def test_manager_remove_prop_dynamic_raises_error(self):
    """Testing remove_prop does not remove dynamic properties."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      with self.assertRaises(errors.DeviceError):
        self.uut.remove_prop(self.first_name, "firmware_version")

  def test_manager_remove_prop_custom_successful(self):
    """Testing if remove_prop works for new property."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.uut.set_prop(self.first_name, "gobbly", "gook")
      self.uut.remove_prop(self.first_name, "gobbly")

  def test_manager_create_device_nonexisting_raises_error_and_suggestion(
      self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      with self.assertRaisesRegex(
          errors.DeviceError, "Close matches: sshdevice-0001, sshdevice-0000"):
        self.uut.create_device("sshdevice-0023")

  def test_manager_create_device_bad_type_raises_error(self):
    self.uut = self._create_manager_object()
    with self.assertRaises(errors.DeviceError):
      self.uut.create_device("gobbly-004")

  def test_manager_create_device_default_check_log_files(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      device = self.uut.create_device(self.first_name)
      with open(device.log_file_name, "w+") as open_file:
        open_file.write("")  # mock device does not write logs
      with open(device.event_file_name, "w+") as open_file:
        open_file.write("")  # mock device does not write events
      self.assertIsNotNone(device, "Was unable to create_device")
      self.assertTrue(
          os.path.exists(device.log_file_name),
          "Log File for device {} does not exist".format(device.name))
      self.assertTrue(
          os.path.exists(device.event_file_name),
          "Event Log File for device {} does not exist".format(device.name))
      manager_log_directory = os.path.realpath(self.uut.log_directory)
      device_event_directory = os.path.dirname(
          os.path.realpath(device.event_file_name))
      device_log_directory = os.path.dirname(
          os.path.realpath(device.log_file_name))
      # Verify event and log files are named correctly and in correct location
      self.assertEqual(
          manager_log_directory, device_event_directory,
          "Device did not put its event logs in the correct directory. "
          "Device d: {} and Manager d: {}".format(device_event_directory,
                                                  manager_log_directory))
      self.assertEqual(
          manager_log_directory, device_log_directory,
          "Device did not put its logs in the correct directory. "
          "Device d: {} and Manager d: {}".format(device_log_directory,
                                                  manager_log_directory))
      self.assertIsNone(device.log_file_symlink,
                        "Expected log file symlink to be None")
      self.assertIsNone(device.event_file_symlink,
                        "Expected event file symlink to be None")

  def test_manager_create_device_default_check_log_event_symlinks(self):
    """Verify stale log or event symlinks are properly removed."""
    self.uut = self._create_manager_object()
    name = self.first_name
    with MockOutDevices():
      log_symlink_name = os.path.join(config_gdm.DEFAULT_LOG_DIRECTORY,
                                      name + "-latest.txt")
      event_symlink_name = os.path.join(config_gdm.DEFAULT_LOG_DIRECTORY,
                                        name + "-latest-events.txt")
      bogus_log_name = os.path.join(config_gdm.DEFAULT_LOG_DIRECTORY,
                                    name + "bogus.txt")
      bogus_event_name = log_process.get_event_filename(bogus_log_name)
      temp_log_symlink_name = log_symlink_name + ".tmp"
      temp_event_symlink_name = event_symlink_name + ".tmp"
      if not os.path.lexists(temp_log_symlink_name):
        os.symlink(bogus_log_name, temp_log_symlink_name)
      if not os.path.lexists(temp_event_symlink_name):
        os.symlink(bogus_event_name, temp_event_symlink_name)
      device = self.uut.create_device(
          name, log_directory=config_gdm.DEFAULT_LOG_DIRECTORY)
      self.assertIsNotNone(device, "Was unable to create_device")
      self.assertTrue(
          os.path.lexists(log_symlink_name),
          "Expecting log symlink at {}".format(log_symlink_name))
      self.assertFalse(
          os.path.lexists(temp_log_symlink_name),
          "Expecting missing temporary log symlink {}".format(
              temp_log_symlink_name))
      self.assertTrue(
          os.path.lexists(event_symlink_name),
          "Expecting event symlink at {}".format(event_symlink_name))
      self.assertFalse(
          os.path.lexists(temp_event_symlink_name),
          "Expecting missing temporary event symlink {}".format(
              temp_event_symlink_name))

  def test_manager_create_device_closed_success(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      device1 = self.uut.create_device(self.first_name)
      device2 = self.uut.create_device(self.second_name)
      open_devices = self.uut.get_open_device_names()
      self.assertIn(self.first_name, open_devices)
      self.assertIn(self.second_name, open_devices)
      device1.close()
      device2.close()
      open_devices = self.uut.get_open_device_names()
      self.assertNotIn(self.first_name, open_devices)
      self.assertNotIn(self.second_name, open_devices)
      self.uut.create_device(self.first_name)
      self.uut.create_device(self.second_name)

  def test_create_device_open_error(self):
    """Ensure attempting to open already open device raises error."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.uut.create_device(self.first_name)
      self.uut.create_device(self.second_name)

      with self.assertRaisesRegex(errors.DeviceError, "open"):
        self.uut.create_device(self.first_name)

      with self.assertRaisesRegex(errors.DeviceError, "open"):
        self.uut.create_device(self.second_name)

  def test_create_device_open_success(self):
    """Tests create_device(raise_if_already_open=False) for an open device."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      device1 = self.uut.create_device(self.first_name)
      device2 = self.uut.create_device(self.second_name)
      self.assertIs(
          self.uut.create_device(self.first_name, raise_if_already_open=False),
          device1)
      self.assertIs(
          self.uut.create_device(self.second_name, raise_if_already_open=False),
          device2)

  def test_manager_create_device_with_non_default_log_directory(self):
    """Test verify that symlink is skipped for non default directory."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      name = self.first_name
      device = self.uut.create_device(
          name, log_directory=self.artifacts_directory)
      with open(device.log_file_name, "w+") as open_file:
        open_file.write("")  # mock device never writes a log line
      with open(device.event_file_name, "w+") as open_file:
        open_file.write("")  # mock device never writes a log line
      self.assertIsNotNone(device, "Was unable to create_device")
      self.assertTrue(
          os.path.exists(device.log_file_name),
          "Log file {} for {} never created".format(device.log_file_name, name))
      log_symlink_name = os.path.join(self.artifacts_directory,
                                      name + "-latest.txt")
      event_symlink_name = log_symlink_name + "-events.txt"
      self.assertFalse(
          os.path.lexists(log_symlink_name),
          "{} symlink file should be skipped for non default directory".format(
              log_symlink_name))
      self.assertFalse(
          os.path.lexists(event_symlink_name),
          "{} symlink file should be skipped for non default directory".format(
              event_symlink_name))

  def test_manager_create_device_with_upper_case_name_successful(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      name = self.first_name.upper()
      device = self.uut.create_device(name, log_file_name=self.device_log_file)
      self.assertTrue(device.make_device_ready.called)
      self.assertIsNotNone(device, "Was unable to create_device")

  def test_manager_create_device_error_in_make_device_ready(self):
    """Ensures create switchboard and make_device_ready errors get handled."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      with mock.patch.object(fake_devices.FakeSSHDevice, "close",
                             autospec=True):
        with mock.patch.object(
            fake_devices.FakeSSHDevice,
            "make_device_ready",
            side_effect=errors.DeviceError("x")):
          with self.assertRaisesRegex(errors.DeviceError, "x"):
            self.uut.create_device("sshdevice-0000")
          # console port should be closed when error in make_device_ready
          fake_devices.FakeSSHDevice.close.assert_called()

  def test_create_device_returns_same_auxiliary_device_instance(self):
    """Test that multiple create_device calls return same auxiliary device."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      device_1 = self.uut.create_device("cambrionix-1234")
      device_2 = self.uut.create_device("cambrionix-1234")
      self.assertIs(device_2, device_1)
      self.assertCountEqual(self.uut.get_open_devices(), [device_1])

  def test_get_open_devices_for_auxiliary_devices(self):
    """Tests get_open_devices() behavior with multiple auxiliary devices."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      device_1 = self.uut.create_device("cambrionix-1234")
      device_2 = self.uut.create_device("cambrionix-1234")
      # Closing one of two references shouldn't actually close the device.
      device_1.close()
      self.assertCountEqual(self.uut.get_open_devices(), [device_1])
      # Closing the second reference should release resources.
      device_2.close()
      self.assertFalse(self.uut.get_open_devices())

  def test_close_open_devices_nonzero_auxiliary_device_user_count(self):
    """Tests that close_open_devices closes all auxiliary devices.

    The devices should still be closed despite nonzero instance user counts.
    """
    self.uut = self._create_manager_object()
    with MockOutDevices():
      # Create 2 devices and don't close them directly.
      device = self.uut.create_device("cambrionix-1234")
      self.uut.create_device("cambrionix-1234")
      with mock.patch.object(
          device, "_close", wraps=device._close) as close_wrapper:
        self.uut.close_open_devices()
        self.assertFalse(self.uut.get_open_devices())
        close_wrapper.assert_called_once()

  def test_create_and_close_device_closed_primary_device(self):
    """Tests create_and_close_device() for a closed primary device."""
    self.uut = self._create_manager_object()
    device_name = "sshdevice-0000"
    with MockOutDevices():
      with self.uut.create_and_close_device(device_name) as device:
        self.assertIsInstance(device, fake_devices.FakeSSHDevice)
        self.assertIn(device_name, self.uut.get_open_device_names())
      self.assertNotIn(device_name, self.uut.get_open_device_names())

  def test_create_and_close_device_open_primary_device(self):
    """Tests create_and_close_device() for an open primary device."""
    self.uut = self._create_manager_object()
    device_name = "sshdevice-0000"
    with MockOutDevices():
      device1 = self.uut.create_device(device_name)
      with self.uut.create_and_close_device(
          device_name, raise_if_already_open=False) as device2:
        self.assertIs(device2, device1)
        self.assertIn(device_name, self.uut.get_open_device_names())
      # .close() should not be called since we reused the already open instance.
      self.assertIn(device_name, self.uut.get_open_device_names())

  def test_create_and_close_device_open_auxiliary_device(self):
    """Tests create_and_close_device() for an open auxiliary device."""
    self.uut = self._create_manager_object()
    device_name = "cambrionix-1234"
    with MockOutDevices():
      device1 = self.uut.create_device(device_name)
      with self.uut.create_and_close_device(
          device_name, raise_if_already_open=False) as device2:
        self.assertIs(device2, device1)
        self.assertIn(device_name, self.uut.get_open_device_names())
        open_count_before = device2._user_count
      self.assertEqual(
          device1._user_count,
          open_count_before - 1,
          "user count did not decrease: close() was not called")
      self.assertIn(device_name, self.uut.get_open_device_names())

  def test_manager_create_devices_with_list_of_strings_successful(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      device_name_list = self.uut.get_connected_devices()[:2]
      self.devices = self.uut.create_devices(device_name_list)
      for i in range(2):
        device_name = device_name_list[i]
        self.assertEqual(
            device_name, self.devices[i].name,
            "First device does not match the first device on config")

  def test_manager_create_devices_of_a_single_type_successful(self):
    """Mobly can potentially pass an id and a label in via a dictionary."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      # based on FAKE_DEVICES_CONFIG
      device_type = "sshdevice"
      device_name_list = list(FAKE_DEVICES["devices"].keys())
      total_of_type = 2
      self.devices = self.uut.create_devices(
          device_name_list, device_type=device_type)
      self.assertEqual(
          len(self.devices), total_of_type,
          ("create_devices should have created {} {} devices but instead "
           "created {}").format(total_of_type, device_type, len(self.devices)))

  def test_manager_create_devices_with_device_type_only(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      device_type = "sshdevice"
      total_of_type = 2
      self.devices = self.uut.create_devices(device_type=device_type)
    self.assertEqual(
        len(self.devices), total_of_type,
        ("create_devices should have created {} {} devices but instead "
         "created {}").format(total_of_type, device_type, len(self.devices)))

  def test_manager_create_devices_with_dictionaries(self):
    """Mobly can potentially pass an id and a label in via a dictionary."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      device_dict_list = [{
          "id": self.first_name,
          "label": "FirstDevice",
      }, {
          "name": FAKE_DEVICES["devices"][self.second_name]["serial_number"],
          "alias": "gobbly"
      }]
      self.devices = self.uut.create_devices(device_dict_list)
    self.assertEqual(device_dict_list[0]["id"], self.devices[0].name)
    self.assertEqual(device_dict_list[0]["label"], self.devices[0].alias)
    self.assertEqual(device_dict_list[1]["name"], self.devices[1].serial_number)
    self.assertEqual(device_dict_list[1]["alias"], self.devices[1].alias)

  def test_manager_create_devices_with_custom_filters(self):
    """Verify custom Parser filters are loaded for each device created."""
    filter_file = os.path.join(self.TEST_FILTER_DIR, _TEST_FILTER_FILE)
    self.uut = self._create_manager_object()
    with MockOutDevices():
      for name in self.uut.get_connected_devices():
        device = self.uut.create_device(
            name, log_directory=self.artifacts_directory, filters=[filter_file])
        self.assertIsNotNone(device, "Was unable to create_device")
        self.assertIn(
            "optional_description.my_message",
            device.event_parser.get_event_labels(),
            "Expecting 'optional_description.my_message' event label")

  def test_close_does_not_affect_other_instances(self):
    """Test that closing one Manager instance doesn't affect others."""
    uut1 = self._create_manager_object()
    uut2 = self._create_manager_object()
    with MockOutDevices():
      try:
        uut1.create_device(self.first_name)
        uut2.create_device(self.second_name)
        self.assertIn(self.first_name, uut1.get_open_device_names())
        self.assertNotIn(self.second_name, uut1.get_open_device_names())
        self.assertNotIn(self.first_name, uut2.get_open_device_names())
        self.assertIn(self.second_name, uut2.get_open_device_names())
        uut1.close()
        self.assertNotIn(self.first_name, uut1.get_open_device_names())
        self.assertIn(self.second_name, uut2.get_open_device_names())
      finally:
        uut1.close()
        uut2.close()

  @mock.patch.object(switch_power_usb_with_charge.SwitchPowerUsbWithCharge,
                     "set_mode")
  @mock.patch.object(
      switch_power_usb_with_charge.SwitchPowerUsbWithCharge,
      "get_mode",
      return_value="off")
  def test_create_device_with_usb_hub(self, mock_get_mode, mock_set_mode):
    self.uut = self._create_manager_object()
    self.uut.options_dict["sshdevice-0000"]["usb_hub"] = "cambrionix-1234"
    self.uut.options_dict["sshdevice-0000"]["usb_port"] = "1"
    try:
      with MockOutDevices():
        device = self.uut.create_device(
            "sshdevice-0000", log_directory=self.artifacts_directory)

        device.close()
        self.assertEqual(device.usb_hub.name, "cambrionix-1234")
        self.assertEqual(device.usb_hub.device_port, "1")
    finally:
      self.uut.options_dict["sshdevice-0000"]["usb_hub"] = None
      self.uut.options_dict["sshdevice-0000"]["usb_port"] = None

  def test_manager_create_log_parser_valid_parameters(self):
    """Uses valid parameter values and verifies LogParser object is returned."""
    filter_file = os.path.join(self.TEST_FILTER_DIR, _TEST_FILTER_FILE)
    self.uut = self._create_manager_object()
    self._create_log_file(MAX_LOG_LINES)
    log_parser_inst = self.uut.create_log_parser(
        self.device_log_file, filter_list=[filter_file])
    self.assertIsInstance(log_parser_inst, log_parser.LogParser,
                          "Unable to create LogParser object.")

  def test_event_related_methods_raise_error_for_bogus_event_label(self):
    """Verify Parser rejects bogus event labels for get_last_event * methods."""
    self.uut = self._create_manager_object()
    with MockOutDevices():
      device = self.uut.create_device(
          self.first_name, log_directory=self.artifacts_directory)
      self.assertIsNotNone(device, "Was unable to create_device")
      with self.assertRaises(errors.DeviceError) as cm:
        device.event_parser.get_last_event(["bogus_event_label"])
      self.assertIn(
          "label bogus_event_label not available.", repr(cm.exception),
          "Rejection of invalid event label did not occur {!r}".format(
              cm.exception))
      with self.assertRaises(errors.DeviceError) as cm:
        device.event_parser.get_event_history(["bogus_event_label"])
      self.assertIn(
          "label bogus_event_label not available.", repr(cm.exception),
          "Rejection of invalid event label did not occur {!r}".format(
              cm.exception))
      with self.assertRaises(errors.DeviceError) as cm:
        device.event_parser.get_event_history_count("bogus_event_label")
      self.assertIn(
          "label bogus_event_label not available.", repr(cm.exception),
          "Rejection of invalid event label did not occur {!r}".format(
              cm.exception))

  def test_manager_get_all_supported_device_types(self):
    self.uut = self._create_manager_object()
    all_types = self.uut.get_supported_device_types()
    primary_types = self.uut.get_supported_primary_device_types()
    other_types = self.uut.get_supported_auxiliary_device_types()
    virtual_types = self.uut.get_supported_virtual_device_types()
    self.assertIsInstance(all_types, list)
    self.assertIsInstance(primary_types, list)
    self.assertIsInstance(other_types, list)
    self.assertIn("cambrionix", all_types)
    self.assertIn("cambrionix", other_types)
    self.assertNotIn("cambrionix", primary_types)
    self.assertIn("sshdevice", all_types)
    self.assertNotIn("sshdevice", other_types)
    self.assertIn("sshdevice", primary_types)
    self.assertCountEqual(
        other_types + primary_types + virtual_types, all_types,
        "Not all device types are in list. Expecting {}. Found {}".format(
            all_types, primary_types + other_types + virtual_types))

  def test_manager_overwrite_configs(self):
    self.uut = self._create_manager_object()
    manager.config.BACKUP_PARENT_DIRECTORY = os.path.join(
        self.artifacts_directory, "fake_backup")
    os.makedirs(manager.config.BACKUP_PARENT_DIRECTORY)
    old_info = [
        self.uut.device_file_name, self.uut.device_options_file_name,
        self.uut.testbeds_file_name, self.uut.gdm_config_file_name
    ]
    self.uut.overwrite_configs()
    self.assertTrue(hasattr(self.uut, "backup_directory"))
    self.assertIn(manager.config.BACKUP_PARENT_DIRECTORY,
                  self.uut.backup_directory)
    self.assertEqual(
        len(list(self.uut._devices.keys())), 0,
        "Manager did not reload with blank configs.")
    try:
      for file_name in old_info:
        config = self.uut._load_config(file_name, None)
        if file_name == self.uut.gdm_config_file_name:
          keys = list(config.keys())
        else:
          init_key = list(config.keys())[0]  # the others have two levels
          keys = config[init_key]
        self.assertEqual(
            len(keys), 0,
            "After overwrite, config {} not empty".format(file_name))
      for old_file_name in old_info:
        new_name = os.path.join(self.uut.backup_directory,
                                os.path.basename(old_file_name))
        self.assertTrue(
            os.path.exists(new_name),
            "File {} was not correctly moved to directory {}. Files: {}".format(
                old_file_name, self.uut.backup_directory,
                os.listdir(self.uut.backup_directory)))
    finally:
      _create_dict(FAKE_DEVICES, self.files["device_file_name"])
      _create_dict(FAKE_DEVICE_OPTIONS, self.files["device_options_file_name"])
      shutil.rmtree(self.uut.backup_directory)

  def test_manager_close_open_devices(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      self.uut.create_device(self.first_name)
      self.uut.create_device(self.second_name)
      open_devices = self.uut.get_open_device_names()
      self.assertIn(
          self.first_name, open_devices,
          "{} not in managers list of open devices ({})".format(
              self.first_name, open_devices))
      self.assertIn(
          self.second_name, open_devices,
          "{} not in manager's open device list ({})".format(
              self.second_name, open_devices))
      self.uut.close()
      open_devices = self.uut.get_open_device_names()
      self.assertFalse(
          open_devices,
          "Should be no open devices after manager closed ({})".format(
              open_devices))

  def test_manager_close_device_success(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      device1 = self.uut.create_device(self.first_name)
      open_devices = self.uut.get_open_device_names()
      self.assertIn(
          self.first_name, open_devices,
          "{} not in managers list of open devices ({})".format(
              self.first_name, open_devices))
      self.uut.close_device(device1.serial_number)
      open_devices = self.uut.get_open_device_names()
      self.assertNotIn(
          self.first_name, open_devices,
          "{} should not be in manager's open device list ({})".format(
              self.first_name, open_devices))

  def test_manager_get_open_device_error(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      with self.assertRaises(errors.DeviceError) as cm:
        self.uut.get_open_device(self.first_name)
      self.assertIn("open", str(cm.exception))

  def test_manager_get_open_device_success(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      device1 = self.uut.create_device(self.first_name)
      device2 = self.uut.get_open_device(self.first_name)
      self.assertEqual(
          device1, device2,
          "Manager should have the same instance of device as the one created")

  def test_manager_get_open_devices_success(self):
    self.uut = self._create_manager_object()
    with MockOutDevices():
      device1 = self.uut.create_device(self.first_name)
      device2 = self.uut.create_device(self.second_name)
      devices = self.uut.get_open_devices()
      self.assertIn(
          device1, devices,
          "{} not in managers list of open devices ({})".format(
              self.first_name, devices))
      self.assertIn(
          device2, devices,
          "{} not in managers list of open devices ({})".format(
              self.first_name, devices))
      device1.close()
      device2.close()
      devices = self.uut.get_open_devices()
      self.assertFalse(
          devices,
          "No devices should be in manager's list of open devices ({})".format(
              devices))

  def test_backup_configs_directory_doesnt_exist(self):
    """Test backup_configs() fails if config backup directory doesn't exist."""
    self.uut = self._create_manager_object()
    with mock.patch.object(os.path, "exists", return_value=False):
      with self.assertRaisesRegex(errors.DeviceError, "does not exist"):
        self.uut.backup_configs()

  def test_detect(self):
    self.uut = self._create_manager_object()
    self.uut.devices = mock.MagicMock()
    persistent_configs = {
        "devices": self.uut.persistent_dict.copy(),
        "other_devices": self.uut.other_persistent_dict.copy()
    }
    options_configs = {
        "device_options": self.uut.options_dict.copy(),
        "other_device_options": self.uut.other_options_dict.copy()
    }
    persistent_configs["devices"]["sshdevice-5678"] = {
        "serial_number": "12345678",
        "device_type": "ssh",
        "model": "Linux",
        "console_port_name": "123.123.123"
    }
    options_configs["device_options"]["sshdevice-5678"] = {"alias": "blah"}
    with mock.patch.object(
        device_detector.DeviceDetector,
        "detect_all_new_devices",
        return_value=(persistent_configs, options_configs)):
      self.uut.detect()
    # Ensure new devices identifiers have been updated in manager instance
    self.assertEqual(self.uut._get_device_name("12345678"), "sshdevice-5678")
    self.assertEqual(self.uut._get_device_name("blah"), "sshdevice-5678")
    with mock.patch.object(
        device_detector.DeviceDetector,
        "detect_all_new_devices",
        return_value=(persistent_configs, options_configs)) as mock_detect:
      # Ensure static ip strings are correctly parsed into lists
      self.uut.detect(static_ips="123.123.78.90")
      mock_detect.assert_called_with(static_ips=[u"123.123.78.90"],
                                     comm_types=None,
                                     addresses=None)
      self.uut.detect(static_ips="123.123.78.90,123.123.78.1,99.9.9.0")
      mock_detect.assert_called_with(
          static_ips=[u"123.123.78.90", "123.123.78.1", "99.9.9.0"],
          comm_types=None,
          addresses=None)
      self.uut.detect(static_ips="123.123.78.90,,,,,123.123.78.1,,")
      mock_detect.assert_called_with(
          static_ips=[u"123.123.78.90", "123.123.78.1"],
          comm_types=None,
          addresses=None)

  def test_detect_force_overwrite(self):
    """Test detect() with force_overwrite=True."""
    self.uut = self._create_manager_object()
    self.uut.devices = mock.MagicMock()
    persistent_configs = {
        "devices": self.uut.persistent_dict.copy(),
        "other_devices": self.uut.other_persistent_dict.copy()
    }
    options_configs = {
        "device_options": self.uut.options_dict.copy(),
        "other_device_options": self.uut.other_options_dict.copy()
    }
    persistent_configs["devices"]["sshdevice-5678"] = {
        "serial_number": "12345678",
        "device_type": "sshdevice",
        "model": "Linux",
        "console_port_name": "123.123.78.1"
    }
    options_configs["device_options"]["sshdevice-5678"] = {"alias": "blah"}
    with mock.patch.object(
        device_detector.DeviceDetector,
        "detect_all_new_devices",
        return_value=(persistent_configs, options_configs)) as mock_detect:
      with mock.patch.object(self.uut, "overwrite_configs") as mock_overwrite:
        self.uut.detect(static_ips=["123.123.78.1"], force_overwrite=True)
      mock_overwrite.assert_called_once()
    mock_detect.assert_called_once_with(
        static_ips=["123.123.78.1", "123.123.78.9", "123.123.78.0"],
        comm_types=None,
        addresses=None)
    # Check that all devices are known to Manager
    device_names = (
        list(FAKE_DEVICES["devices"].keys()) +
        list(FAKE_DEVICES["other_devices"].keys()) + ["sshdevice-5678"])
    for device_name in device_names:
      self.uut._get_device_name(device_name, raise_error=True)

  @parameterized.named_parameters(
      ("comm_types", None, ["SshComms"], None),
      ("addresses", None, None, ["12.34.56.78"]),
      ("comm_types_and_addresses", None, ["SshComms"], ["12.34.56.78"]),
      ("comm_types_and_addresses_with_static_ips",
       ["12.34.56.78"], ["SshComms"], ["12.34.56.78"]),
  )
  @mock.patch.object(
      device_detector.DeviceDetector, "detect_new_devices", autospec=True,
      return_value=({}, {}))
  @mock.patch.object(communication_types, "detect_connections", autospec=True)
  def test_detect_argument_propagation(
      self, static_ips, comm_types, addresses,
      mock_detect_connections, mock_detect_new_devices):
    """Tests that detect() propagates arguments appropriately."""
    expected_static_ips = static_ips if static_ips is not None else []
    self.uut = self._create_manager_object()
    self.uut.detect(
        static_ips=static_ips,
        communication_types=comm_types,
        addresses=addresses)
    mock_detect_connections.assert_called_once_with(
        static_ips=expected_static_ips,
        comm_types=comm_types,
        addresses=addresses)
    mock_detect_new_devices.assert_called_once_with(
        mock.ANY, mock_detect_connections.return_value)

  def test_delete(self):
    self.uut = self._create_manager_object()
    persistent_configs = {
        "devices": self.uut.persistent_dict.copy(),
        "other_devices": self.uut.other_persistent_dict.copy()
    }
    options_configs = {
        "device_options": self.uut.options_dict.copy(),
        "other_device_options": self.uut.other_options_dict.copy()
    }
    persistent_configs["devices"]["sshdevice-5678"] = {
        "serial_number": "12345678",
        "device_type": "sshdevice",
        "model": "EVT",
        "console_port_name": "123.123.123"
    }
    options_configs["device_options"]["sshdevice-5678"] = {"alias": "blah"}
    with MockOutDevices():
      with mock.patch.object(
          device_detector.DeviceDetector,
          "detect_all_new_devices",
          return_value=(persistent_configs, options_configs)):
        self.uut.detect()
    # Ensure new devices identifiers have been updated in manager instance
    self.assertEqual(self.uut._get_device_name("12345678"), "sshdevice-5678")
    self.assertEqual(self.uut._get_device_name("blah"), "sshdevice-5678")
    self.uut.delete("sshdevice-5678")
    # verfiy that the device has been removed.
    with self.assertRaises(errors.DeviceError):
      self.uut._get_device_name("12345678", raise_error=True)

  def test_redetect(self):
    self.uut = self._create_manager_object()
    self.uut.devices = mock.MagicMock()
    persistent_configs = {
        "devices": self.uut.persistent_dict.copy(),
        "other_devices": self.uut.other_persistent_dict.copy()
    }
    options_configs = {
        "device_options": self.uut.options_dict.copy(),
        "other_device_options": self.uut.other_options_dict.copy()
    }
    persistent_configs["other_devices"]["cambrionix-4321"] = {
        "console_port_name": "fake_hub_name",
        "ftdi_serial_number": "FT2BSR6O",
        "total_ports": 15,
        "device_type": "cambrionix",
        "serial_number": "987654321",
        "model": "PP15S"
    }
    options_configs["other_device_options"]["cambrionix-4321"] = {
        "alias": "blah-cam"
    }
    with mock.patch.object(
        device_detector.DeviceDetector,
        "detect_all_new_devices",
        return_value=(persistent_configs, options_configs)):
      self.uut.detect()
      # Ensure new devices identifiers have been updated in manager instance
      self.assertEqual(
          self.uut._get_device_name("987654321"), "cambrionix-4321")
      self.assertEqual(self.uut._get_device_name("blah-cam"), "cambrionix-4321")
      # Re-detect the device
      # Assert settable properties were preserved
      with mock.patch.object(self.uut,
                             "_save_config_to_file") as mock_save_config:
        self.uut.redetect("cambrionix-4321")
        mock_save_config.assert_called_with(options_configs,
                                            self.uut.device_options_file_name)
    # Ensure new devices identifiers have been updated in manager instance
    self.assertEqual(self.uut._get_device_name("987654321"), "cambrionix-4321")
    self.assertEqual(self.uut._get_device_name("blah-cam"), "cambrionix-4321")

  def test_redetect_static_ip_device(self):
    self.uut = self._create_manager_object()
    persistent_configs = {
        "devices": self.uut.persistent_dict.copy(),
        "other_devices": self.uut.other_persistent_dict.copy()
    }
    options_configs = {
        "device_options": self.uut.options_dict.copy(),
        "other_device_options": self.uut.other_options_dict.copy()
    }
    with MockOutDevices():
      with mock.patch.object(
          device_detector.DeviceDetector,
          "detect_all_new_devices",
          return_value=(persistent_configs, options_configs)) as mock_detect:
        self.uut.redetect("sshdevice-0000")
        mock_detect.assert_called_with(static_ips=[u"123.123.78.9"],
                                       comm_types=None,
                                       addresses=None)

  @mock.patch.object(switch_power_usb_with_charge.SwitchPowerUsbWithCharge,
                     "set_mode")
  @mock.patch.object(
      switch_power_usb_with_charge.SwitchPowerUsbWithCharge,
      "get_mode",
      return_value="off")
  def test_redetect_device_with_usb_power_off(self, get_mode_mock,
                                              set_mode_mock):
    self.uut = self._create_manager_object()
    persistent_configs = {
        "devices": copy.deepcopy(self.uut.persistent_dict),
        "other_devices": self.uut.other_persistent_dict.copy()
    }
    options_configs = {
        "device_options": self.uut.options_dict.copy(),
        "other_device_options": self.uut.other_options_dict.copy()
    }
    # Change the current config to have hub_name and port set (so that the power
    # mode is changed as part of redetect.) Use the persistent_configs and
    # options_configs as what detection returns since other tests will fail if
    # the usb hub properties are set.
    current_persistent = {
        "devices": self.uut.persistent_dict.copy(),
        "other_devices": self.uut.other_persistent_dict.copy()
    }
    current_persistent["devices"]["sshdevice-0000"][
        "device_usb_hub_name"] = "cambrionix-1234"
    current_persistent["devices"]["sshdevice-0000"]["device_usb_port"] = "11"
    with MockOutDevices():
      with mock.patch.object(
          device_detector.DeviceDetector,
          "detect_all_new_devices",
          return_value=(persistent_configs, options_configs)):
        self.uut.redetect("sshdevice-0000")
        self.assertIn("sshdevice-0000", self.uut.persistent_dict)

  def test_redetect_device_not_redetected(self):
    """Test that redetect() raises an error if the device was not redetected."""
    self.uut = self._create_manager_object()
    persistent_configs = {
        "devices": copy.deepcopy(self.uut.persistent_dict),
        "other_devices": copy.deepcopy(self.uut.other_persistent_dict)
    }
    options_configs = {
        "device_options": copy.deepcopy(self.uut.options_dict),
        "other_device_options": copy.deepcopy(self.uut.other_options_dict)
    }
    err_msg = "Device sshdevice-0000 was not successfully redetected"
    # Change name from "sshdevice-0000" to "sshdevice-9999"
    persistent_configs["devices"]["sshdevice-9999"] = persistent_configs[
        "devices"].pop("sshdevice-0000")
    options_configs["device_options"]["sshdevice-9999"] = options_configs[
        "device_options"].pop("sshdevice-0000")
    with MockOutDevices():
      with mock.patch.object(
          device_detector.DeviceDetector,
          "detect_all_new_devices",
          return_value=(persistent_configs, options_configs)):
        with self.assertRaisesRegex(errors.DeviceError, err_msg):
          self.uut.redetect("sshdevice-0000")
    # Device should still be known to Manager after failed redetection
    self.uut._get_device_name("sshdevice-0000", raise_error=True)
    # Remove the device
    del persistent_configs["devices"]["sshdevice-9999"]
    del options_configs["device_options"]["sshdevice-9999"]
    with MockOutDevices():
      with mock.patch.object(
          device_detector.DeviceDetector,
          "detect_all_new_devices",
          return_value=(persistent_configs, options_configs)):
        with self.assertRaisesRegex(errors.DeviceError, err_msg):
          self.uut.redetect("sshdevice-0000")
    # Device should still be known to Manager after failed redetection
    self.uut._get_device_name("sshdevice-0000", raise_error=True)

  def test_devices(self):
    """Test that Manager.devices() prints a list of all known devices."""
    with MockOutDevices():
      self.uut = self._create_manager_object()
      self.uut.devices()

  def test_is_device_connected_error(self):
    """Test is_device_connected() returns False when is_connected() raises."""
    self.uut = self._create_manager_object()
    with mock.patch.object(
        fake_devices.FakeSSHDevice,
        "is_connected",
        side_effect=errors.DeviceError("Some error")):
      self.assertFalse(self.uut.is_device_connected("sshdevice-0000"))

  def test_get_device_name_not_string(self):
    """Test that get_device_name() raises when identifier is not a string."""
    self.uut = self._create_manager_object()
    with self.assertRaisesRegex(errors.DeviceError,
                                "Device identifier '1234' should be a string."):
      self.uut._get_device_name(1234)

  def test_load_config_raises_if_file_not_found(self):
    """Test that _load_config() raises if config file doesn't exist."""
    self.uut = self._create_manager_object()
    err_regex = ("Device load configuration failed. File devices.json is not "
                 "found")
    with mock.patch.object(os.path, "exists", return_value=False):
      with self.assertRaisesRegex(errors.DeviceError, err_regex):
        self.uut._load_config("devices.json")

  def test_load_config_raises_if_file_not_json(self):
    """Test that _load_config() raises if it fails to read the JSON."""
    self.uut = self._create_manager_object()
    json_err = json.decoder.JSONDecodeError("Extra data", "line 1 column 3", 2)
    err_regex = "Unable to parse GDM config file as a json file"
    with mock.patch.object(os.path, "exists", return_value=True):
      with mock.patch.object(builtins, "open"):
        with mock.patch.object(json, "load", side_effect=json_err):
          with self.assertRaisesRegex(errors.DeviceError, err_regex):
            self.uut._load_config("devices.json")

  def test_add_correct_value_to_config_value_is_none(self):
    """Test that add_correct_value_to_config() raises if value is None."""
    self.uut = self._create_manager_object()
    with self.assertRaisesRegex(errors.DeviceError,
                                "Final value for some_key should not be None"):
      self.uut._add_correct_value_to_config("some_key", None, None)

  def test_add_correct_path_to_config_path_is_none(self):
    """Test that add_correct_value_to_config() raises if path is None."""
    self.uut = self._create_manager_object()
    with self.assertRaisesRegex(errors.DeviceError,
                                "Final value for some_path should not be None"):
      self.uut._add_correct_path_to_config("some_path", None, None)

  def test_add_correct_path_to_config_parent_dir_doesnt_exist(self):
    """Test add_correct_value_to_config() fails if parent dir doesn't exist."""
    self.uut = self._create_manager_object()
    err_regex = "Parent directory of /some/path.txt for some_key doesn't exist"
    with mock.patch.object(os.path, "isdir", return_value=False):
      with self.assertRaisesRegex(errors.DeviceError, err_regex):
        self.uut._add_correct_path_to_config("some_key", "/some/path.txt",
                                             "some/default/path")

  def test_add_correct_path_to_config_file_doesnt_exist(self):
    """Test that add_correct_value_to_config() raises if file doesn't exist."""
    self.uut = self._create_manager_object()
    err_regex = "File /some/path.txt for some_key doesn't exist"
    with mock.patch.object(os.path, "isdir", return_value=True):
      with mock.patch.object(os.path, "exists", return_value=False):
        with self.assertRaisesRegex(errors.DeviceError, err_regex):
          self.uut._add_correct_path_to_config("some_key", "/some/path.txt",
                                               "some/default/path")

  def test_log_handlers_no_stdout_logging(self):
    """Verify stdout log handler is disabled when stdout_logging = False."""
    gc.collect()  # remove_handler can also get called by Manager.__del__
    with mock.patch.object(gdm_logger, "remove_handler") as mock_remove_handler:
      self.uut = self._create_manager_object(stdout_logging=False)
      mock_remove_handler.assert_called_once_with(gdm_logger._stdout_handler)

  def test_create_required_folders_success(self):
    required_folders = ["mock", "mock2", "mock3", "mock3/mock4"]
    required_folders = [
        os.path.join(self.artifacts_directory, folder)
        for folder in required_folders
    ]
    for folder in required_folders:
      if os.path.exists(folder):
        os.rmdir(folder)
    # By mocking REQUIRED_FOLDERS, the necessary config folder won't get created
    # and manager creation fails when checking for configs like gdm.json.
    os.makedirs(config_gdm.CONFIG_DIRECTORY, exist_ok=True)
    with mock.patch.object(config_gdm, "REQUIRED_FOLDERS", required_folders):
      self._create_manager_object()
    self.assertTrue(
        os.path.exists(
            os.path.join(self.artifacts_directory, "mock3", "mock4")),
        "Required folder should exist but doesn't")
    permission = oct(os.stat(required_folders[0]).st_mode)[-3:]
    self.assertEqual(
        permission, manager._EXPECTED_FOLDER_PERMISSIONS,
        "Permission of existing required file is {} but should be {}".format(
            permission, manager._EXPECTED_FOLDER_PERMISSIONS))

  def test_permissions_issue_raises_appropriate_message(self):
    required_folders = [os.path.join(self.artifacts_directory, "mock5")]
    for folder in required_folders:
      if os.path.exists(folder):
        os.rmdir(folder)
    # should be able to handle making folders and leaving existing ones alone
    with mock.patch.object(config_gdm, "REQUIRED_FOLDERS", required_folders):
      with mock.patch.object(os, "chmod", side_effect=OSError("x", "y")):
        mock_stat_result = mock.Mock()
        mock_stat_result.st_mode = int("400", 8)
        with mock.patch.object(os, "stat", return_value=mock_stat_result):
          with self.assertRaisesRegex(errors.DeviceError, "sudo chmod"):
            self._create_manager_object()

  def test_transport_process_exceptions_are_reraised(self):
    """Test capturing and re-raising exceptions in transport processes."""
    device_manager = manager.Manager()
    log_path = "/tmp/dummy_log.txt"
    device_switchboard = switchboard.SwitchboardDefault(
        "test_device", device_manager._exception_queue, [], log_path)
    transport = fake_transport.FakeTransport(
        fail_open=True, open_on_start=False)
    transport_num = device_switchboard.add_transport_process(transport)
    device_switchboard.start_transport_process(transport_num)
    with self.assertRaisesRegex(errors.DeviceError,
                                fake_transport.EXCEPTION_MESSAGE):
      device_switchboard.open_transport(transport_num)

  def test_supported_capability_interfaces_not_empty(self):
    """Check that the dict of supported capability interfaces is not empty."""
    self.assertTrue(manager.Manager.get_all_supported_capability_interfaces())

  def test_supported_capability_flavors_not_empty(self):
    """Check that the dict of supported capability flavors is not empty."""
    self.assertTrue(manager.Manager.get_all_supported_capability_flavors())

  def test_supported_capability_interfaces_are_read_only(self):
    """Check that the dict of supported capability interfaces is read-only."""
    interfaces_dict = manager.Manager.get_all_supported_capability_interfaces()
    interfaces_dict["foo"] = "bar"
    self.assertNotIn("foo",
                     manager.Manager.get_all_supported_capability_interfaces())

  def test_no_reference_loops(self):
    """Test deleting last reference to object triggers garbage collection."""
    manager_kwargs = {
        "device_file_name": self.files["device_file_name"],
        "device_options_file_name": self.files["device_options_file_name"],
        "gdm_config_file_name": self.files["gdm_config_file_name"],
        "testbeds_file_name": self.files["testbeds_file_name"],
        "log_directory": self.artifacts_directory,
        "gdm_log_file": self._create_log_path()
    }
    # Call to signal.signal() from Manager.__init__ seems to create a reference
    # loop. Alternatively, gc.collect() can be called right after Manager
    # instance creation.
    with mock.patch.object(signal, "signal"):
      self.verify_no_reference_loops(manager.Manager, (), manager_kwargs)

  def test_atexit_handler_not_called_if_object_is_dead(self):
    """Test handler registered via atexit() does nothing if object not live."""
    gc.collect()  # Ensure existing garbage doesn't interfere
    gc.disable()  # Ensure __del__ isn't called by periodic GC
    try:
      with mock.patch.object(atexit, "register") as mock_register:
        uut, close_calls, del_calls = self._create_manager_gc_helper_objects()
        uut_id = id(uut)
        atexit_handler = mock_register.call_args[0][0]
      self.assertEqual(0, close_calls[uut_id])
      self.assertEqual(0, del_calls[uut_id])
      del uut
      self.assertEqual(1, close_calls[uut_id])
      self.assertEqual(1, del_calls[uut_id])
      atexit_handler()  # Manually simulate call by atexit
      self.assertEqual(1, close_calls[uut_id])
      self.assertEqual(1, del_calls[uut_id])
    finally:
      gc.enable()

  def test_atexit_handler_called_if_object_is_live(self):
    """Test that atexit calls close() if object is still live."""
    gc.collect()  # Ensure existing garbage doesn't interfere
    gc.disable()  # Ensure __del__ isn't called by periodic GC
    try:
      with mock.patch.object(atexit, "register") as mock_register:
        uut, close_calls, del_calls = self._create_manager_gc_helper_objects()
        uut_id = id(uut)
        atexit_handler = mock_register.call_args[0][0]
      self.assertEqual(0, close_calls[uut_id])
      self.assertEqual(0, del_calls[uut_id])
      atexit_handler()  # Manually simulate call by atexit
      self.assertEqual(1, close_calls[uut_id])
      self.assertEqual(0, del_calls[uut_id])
      del uut
      self.assertEqual(2, close_calls[uut_id])
      self.assertEqual(1, del_calls[uut_id])
    finally:
      gc.enable()

  def test_get_supported_device_capabilities(self):
    """Test that the call uses the correct device class."""
    mock_capabilities = ["cap1, cap2"]
    with mock.patch.object(
        fake_devices.FakeSSHDevice,
        "get_supported_capabilities",
        return_value=mock_capabilities) as mock_get_capabilities:
      self.assertEqual(
          manager.Manager.get_supported_device_capabilities("sshdevice"),
          mock_capabilities)
      mock_get_capabilities.assert_called_once()

  def test_device_has_capabilities(self):
    """Test that the call uses the correct device class."""
    caps = ["cap1", "cap2"]
    with mock.patch.object(
        fake_devices.FakeSSHDevice, "has_capabilities",
        return_value=True) as mock_has_capabilities:
      self.assertIs(
          manager.Manager.device_has_capabilities("sshdevice", caps), True)
      mock_has_capabilities.assert_called_once_with(caps)

  def test_get_supported_device_capability_flavors(self):
    """Test underlying NestDeviceBase method is called on appropriate class."""
    mock_capability_flavors = set([str, dict])  # Set of some class objects
    with mock.patch.object(
        fake_devices.FakeSSHDevice,
        "get_supported_capability_flavors",
        return_value=mock_capability_flavors) as mock_method:
      self.assertEqual(
          manager.Manager.get_supported_device_capability_flavors("sshdevice"),
          [dict, str])
      mock_method.assert_called_once()

  def test_process_exceptions_missing_queue(self):
    """Test failure if _exception_queue deleted before _process_exceptions."""
    self.uut = self._create_manager_object()
    self.uut.close()
    with self.assertRaisesRegex(errors.DeviceError, "Exception queue deleted"):
      self.uut._process_exceptions(None, None)

  @mock.patch.object(host_utils, "_download_key")
  @mock.patch.object(host_utils, "_set_key_permissions")
  def test_download_keys(self, mock_set_key_permissions, mock_download_key):
    """Test download_keys downloading missing keys."""
    mock_key_1 = data_types.KeyInfo(
        "foo_key", type=data_types.KeyType.SSH, package="foo_package")
    mock_key_2 = data_types.KeyInfo(
        "bar_key", type=data_types.KeyType.SSH, package="foo_package")
    self.uut = self._create_manager_object()
    with mock.patch.object(extensions, "keys", new=[mock_key_1, mock_key_2]):
      with mock.patch.object(os.path, "exists", side_effect=[True, False]):
        self.uut.download_keys()
    mock_download_key.assert_called_once_with(mock_key_2)
    mock_set_key_permissions.assert_called()

  def _create_log_path(self):
    return os.path.join(self.artifacts_directory,
                        self._testMethodName + "-gdm.txt")

  def _create_mgr_obj_active_create_switchboard(self,
                                                gdm_log_file=None,
                                                debug_level=None,
                                                stream_debug=False,
                                                stdout_logging=True):
    if gdm_log_file is None:
      gdm_log_file = self._create_log_path()
    with mock.patch.object(multiprocessing_utils.get_context(), "Queue"):
      man_instance = manager.Manager(
          device_file_name=self.files["device_file_name"],
          device_options_file_name=self.files["device_options_file_name"],
          gdm_config_file_name=self.files["gdm_config_file_name"],
          testbeds_file_name=self.files["testbeds_file_name"],
          log_directory=self.artifacts_directory,
          gdm_log_file=gdm_log_file,
          debug_level=debug_level,
          stream_debug=stream_debug,
          stdout_logging=stdout_logging)
    return man_instance

  def _create_manager_object(self,
                             gdm_log_file=None,
                             debug_level=None,
                             stream_debug=False,
                             stdout_logging=True):
    man_instance = self._create_mgr_obj_active_create_switchboard(
        gdm_log_file=gdm_log_file,
        debug_level=debug_level,
        stream_debug=stream_debug,
        stdout_logging=stdout_logging)
    self.mock_switchboard = mock.MagicMock(spec=switchboard.SwitchboardDefault)
    self.mock_switchboard.device_name = "FakeDevice"
    man_instance.create_switchboard = mock.MagicMock(
        return_value=self.mock_switchboard)
    return man_instance

  def _create_manager_gc_helper_objects(self):
    close_calls = collections.defaultdict(int)
    del_calls = collections.defaultdict(int)
    gc_helper_class = self.make_gc_helper_class(manager.Manager)
    manager_kwargs = {
        "device_file_name": self.files["device_file_name"],
        "device_options_file_name": self.files["device_options_file_name"],
        "gdm_config_file_name": self.files["gdm_config_file_name"],
        "testbeds_file_name": self.files["testbeds_file_name"],
        "log_directory": self.artifacts_directory,
        "gdm_log_file": self._create_log_path()
    }
    extra_gc_kwargs = {
        "close_calls": close_calls,
        "del_calls": del_calls,
        "logger": self.logger
    }
    manager_kwargs.update(extra_gc_kwargs)
    mgr_gc_helper = gc_helper_class(**manager_kwargs)
    # Call to signal.signal() from Manager.__init__ seems to create a reference
    # loop. Get rid of it before testing.
    gc.collect()
    return mgr_gc_helper, close_calls, del_calls


if __name__ == "__main__":
  unit_test_case.main()
