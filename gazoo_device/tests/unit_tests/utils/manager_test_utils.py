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

"""Code shared by Manager unit tests: manager_test.py, fire_manager_test.py."""
import datetime
import json
import os
import shutil
from unittest import mock

from gazoo_device import gdm_logger
from gazoo_device import package_registrar
from gazoo_device.auxiliary_devices import cambrionix
from gazoo_device.switchboard import log_process
from gazoo_device.tests.unit_tests.utils import fake_devices
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import usb_config
import immutabledict

FAKE_DEVICES = {
    "devices": {
        "sshdevice-0000": {
            "serial_number": "00000000",
            "name": "sshdevice-0000",
            "device_type": "sshdevice",
            "model": "linux",
            "console_port_name": "123.123.78.9",
        },
        "sshdevice-0001": {
            "serial_number": "00000001",
            "name": "sshdevice-0001",
            "device_type": "sshdevice",
            "model": "linux",
            "console_port_name": "123.123.78.0",
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
        },
    },
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
            "alias": "",
        },
    },
}

USB_INFO_DICT = immutabledict.immutabledict({
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
            serial_number="12345", address="360av3", product_name="Android"),
})

ANOTHER_MESSAGE_LINE = "{} [APPL] This is another message\n"
NO_MATCH_LINE = "{} [BOOT] Non-matching line\n"
STATE_LINE = "{} [APPL] Some other message with group data {}\n"
UNIQUE_MESSAGE_LINE = "{} [APPL] Some unique message\n"


def create_dict(a_dict, file_path):
  with open(file_path, "w+") as open_file:
    json.dump(a_dict, open_file)


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
  create_dict(FAKE_DEVICES, files["device_file_name"])
  create_dict(FAKE_DEVICE_OPTIONS, files["device_options_file_name"])
  create_dict(fake_gdm_config, files["gdm_config_file_name"])
  create_dict({"testbeds": {}}, files["testbeds_file_name"])
  create_dict({}, fake_gdm_config["device_file_name"])
  create_dict({}, fake_gdm_config["device_options_file_name"])
  create_dict({"testbeds": {}}, fake_gdm_config["testbeds_file_name"])
  return fake_gdm_config, files


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


class ManagerTestsSetup(unit_test_case.UnitTestCase):
  """Common setup and helper methods for Manager & FireManager unit tests."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    gdm_logger.initialize_logger()
    package_registrar.register(cambrionix)
    package_registrar.register(fake_devices)

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
    if self.uut is not None:
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
