# Copyright 2021 Google LLC
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

"""Fake Gazoo Device Base class."""
import os.path

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.tests.unit_tests import utils

_FILTER_DIRECTORY = os.path.join(os.path.dirname(utils.__file__), "filters")

logger = gdm_logger.get_logger()


class FakeGazooDeviceBase(gazoo_device_base.GazooDeviceBase):
  """A dummy valid concrete primary device class."""
  _DEFAULT_FILTERS = [
      os.path.join(_FILTER_DIRECTORY, "basic.json"),
  ]

  @classmethod
  def is_connected(cls, device_config):
    return True

  @decorators.DynamicProperty
  def firmware_version(self):
    return "some_version"

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
  def health_checks(self):
    return []

  @decorators.LogDecorator(logger)
  def check_device_ready(self):
    raise NotImplementedError("check_device_ready is an abstract method.")

  @decorators.LogDecorator(logger)
  def factory_reset(self):
    raise NotImplementedError("factory_reset is an abstract method.")

  @decorators.LogDecorator(logger)
  def get_detection_info(self):
    raise NotImplementedError("get_detection_info is an abstract method.")

  @decorators.LogDecorator(logger)
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

  @decorators.LogDecorator(logger)
  def wait_for_bootup_complete(self, timeout=None):
    raise NotImplementedError("wait_for_bootup_complete is an abstract method.")
