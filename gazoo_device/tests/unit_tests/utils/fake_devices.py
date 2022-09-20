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
"""Methods and classes for faking devices in unit tests."""
import copy
import os.path
from typing import Callable, List
from unittest import mock

import gazoo_device
from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.base_classes import ssh_device
from gazoo_device.capabilities import usb_hub_default
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests import utils
from gazoo_device.tests.unit_tests.utils import fake_responder

_DEFAULT_CONFIG = {
    "persistent": {
        "name": "sshdevice-1234",
        "device_type": "sshdevice",
        "serial_number": "123456",
        "console_port_name": "123.456.78.9",
        "wpan_mac_address": "123456",
        "model": "Development",
    },
    "options": {
        "usb_port": None,
        "usb_hub": None,
        "alias": None,
    },
    "skip_recover_device": False,
    "make_device_ready": "on",
    "log_name_prefix": "",
    "filters": None,
}
_FILTER_DIRECTORY = os.path.join(os.path.dirname(utils.__file__), "filters")
_LOGGER = gdm_logger.get_logger()
_TEST_ARTIFACTS_DIR = os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR", "/tmp")
_DEFAULT_NAME = "sshdevice-1234"


class FakeSSHDevice(ssh_device.SshDevice):
  """Fake SSH device (primary device) for testing purposes."""
  _DEFAULT_FILTERS = (os.path.join(_FILTER_DIRECTORY, "basic.json"),)
  DEVICE_TYPE = "sshdevice"
  _OWNER_EMAIL = "gdm-authors@google.com"
  DETECT_MATCH_CRITERIA = {}
  responder_debug = False  # print out responder logs

  def __init__(self,
               manager=None,
               device_config=None,
               log_directory=None,
               log_file_name=None,
               name=_DEFAULT_NAME):

    if not manager:
      if not log_directory:
        log_directory = _TEST_ARTIFACTS_DIR
      manager = create_mock_manager(log_directory)
    if not device_config:
      device_config = create_default_device_config(name)
    self._fake_responder = fake_responder.FakeResponder()
    super().__init__(
        manager=manager,
        device_config=device_config,
        log_file_name=log_file_name,
        log_directory=log_directory)

  @decorators.health_check
  def check_device_responsiveness(self):
    return True

  @decorators.LogDecorator(_LOGGER)
  def factory_reset(self):
    pass

  @decorators.DynamicProperty
  def firmware_version(self):
    return "some_version"

  @classmethod
  def is_connected(cls, device_config):
    return True

  @decorators.PersistentProperty
  def platform(self):
    return "Linux"

  @decorators.LogDecorator(_LOGGER)
  def reboot(self, no_wait, method):
    del no_wait, method  # Unused

  @decorators.CapabilityDecorator(usb_hub_default.UsbHubDefault)
  def usb_hub(self):
    """Returns a usb_hub capability to send commands."""
    return self.lazy_init(
        usb_hub_default.UsbHubDefault,
        device_name=self.name,
        get_manager=self.get_manager,
        hub_name=self.props["optional"].get("usb_hub"),
        device_port=self.props["optional"].get("usb_port"),
        get_switchboard_if_initialized=self.switchboard)


class FakePtyDevice(FakeSSHDevice):
  """Fake primary PTY device for testing purposes."""
  DEVICE_TYPE = "ptydevice"
  COMMUNICATION_TYPE = "PtyProcessComms"
  _COMMUNICATION_KWARGS = {}
  PTY_PROCESS_COMMAND_CONFIG = {
      "device_image_path_pattern": os.path.join("*", "some_firmware.img"),
      "launch_command_template": "some_dir/some_binary --some_arg {param}",
  }


class FakeGazooDeviceBase(gazoo_device_base.GazooDeviceBase):
  """A dummy valid concrete primary device class."""
  _DEFAULT_FILTERS = (os.path.join(_FILTER_DIRECTORY, "basic.json"),)

  @classmethod
  def is_connected(cls, device_config):
    return True

  @decorators.DynamicProperty
  def firmware_version(self):
    return "some_version"

  @decorators.LogDecorator(_LOGGER)
  def get_console_configuration(self):
    return None

  @decorators.PersistentProperty
  def os(self):
    return "Linux"

  @decorators.DynamicProperty
  def dynamic_bad(self):
    raise NotImplementedError("blah")

  @decorators.PersistentProperty
  def platform(self):
    return "SomethingPlatform"

  @decorators.PersistentProperty
  def health_checks(self) -> List[Callable[[], None]]:
    return []

  @decorators.LogDecorator(_LOGGER)
  def check_device_ready(self):
    raise NotImplementedError("check_device_ready is an abstract method.")

  @decorators.LogDecorator(_LOGGER)
  def factory_reset(self):
    raise NotImplementedError("factory_reset is an abstract method.")

  @decorators.LogDecorator(_LOGGER)
  def get_detection_info(self):
    raise NotImplementedError("get_detection_info is an abstract method.")

  @decorators.LogDecorator(_LOGGER)
  def reboot(self, no_wait=False, method="shell"):
    raise NotImplementedError("reboot is an abstract method.")

  def shell(self,
            command: str,
            command_name: str = "shell",
            timeout: float = 30.0,
            port: int = 0,
            searchwindowsize: int = 2000,
            include_return_code: bool = False) -> str:
    del self, command, command_name, timeout, port, searchwindowsize
    del include_return_code  # Unused: dummy implementation
    return "some_shell_response"

  @decorators.LogDecorator(_LOGGER)
  def wait_for_bootup_complete(self, timeout=None):
    raise NotImplementedError("wait_for_bootup_complete is an abstract method.")


def create_default_device_config(uut_name):
  """Creates default device_config to pass into device class initialization."""
  if "-" not in uut_name:
    raise RuntimeError(
        "device name {} needs to be in format <device_type>-<device-id>")
  new_config = copy.deepcopy(_DEFAULT_CONFIG)
  new_config["persistent"]["name"] = uut_name
  new_config["persistent"]["device_type"] = uut_name.split("-")[0]
  return new_config


def create_mock_manager(
    artifacts_directory: str) -> gazoo_device.manager.Manager:
  """Create a mock manager to use with unit tests."""
  mock_manager = mock.MagicMock(spec=gazoo_device.manager.Manager)
  # pylint: disable=protected-access
  mock_manager._open_devices = {}
  mock_manager._devices = {}
  # pylint: enable=protected-access
  mock_manager.other_devices = {}
  mock_manager.log_directory = artifacts_directory
  return mock_manager


def create_mock_switchboard(
    name: str, manager: gazoo_device.manager.Manager,
    responder: fake_responder.FakeResponder) -> switchboard.SwitchboardDefault:
  """Returns a mock switchboard.

  Tests can use the responder to manipulate the device I/O.

  Args:
    name: id of the mock device
    manager: gazoo_device manager, ideally a mock.
    responder: instance of fake_responder
  """

  mock_switchboard = mock.MagicMock(spec=switchboard.SwitchboardDefault)
  mock_switchboard.healthy = True
  mock_switchboard.health_checked = True
  mock_switchboard.device_name = name
  mock_switchboard.number_transports = 2
  mock_switchboard.send_and_expect.side_effect = responder.send_and_expect
  mock_switchboard.expect.side_effect = responder.expect
  mock_switchboard.click_and_expect.side_effect = responder.click_and_expect
  mock_switchboard.press_and_expect.side_effect = responder.press_and_expect
  mock_switchboard.release_and_expect.side_effect = responder.release_and_expect

  def _mock_create_switchboard(**kwargs):
    # pylint: disable=protected-access
    mock_switchboard._force_slow = kwargs.get("force_slow", False)
    # pylint: enable=protected-access
    return mock_switchboard

  manager.create_switchboard = mock.Mock(side_effect=_mock_create_switchboard)
  return mock_switchboard
