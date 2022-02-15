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

"""Base class for GDM functional tests."""
import logging
import os.path  # pylint: disable=unused-import

from gazoo_device.tests.functional_tests.utils import suite_filter
from gazoo_device.utility import retry
from gazoo_device.tests import functional_tests

_CREATION_TIMEOUT = 120
_RECONNECT_TIMEOUT = 60
_CREATION_SLEEP = 10
DIRECTORY = os.path.abspath(os.path.dirname(functional_tests.__file__))
_CONFIG_DIRS = (os.path.join(DIRECTORY,"configs"),)

DeviceType = suite_filter.DeviceType


class GDMTestBase(suite_filter.SuiteFilterBase):
  """Base class for GDM functional test suites."""
  _CONFIG_DIRS = _CONFIG_DIRS
  device = None
  testing_properties = None

  def setup_class(self) -> None:
    """Initiate device and upgrade as needed."""
    super().setup_class()
    self.testing_properties = self.user_params
    self.device = retry.retry(
        func=self.register_controller,
        func_args=(self._CONTROLLER_MODULE,),
        timeout=_CREATION_TIMEOUT,
        interval=_CREATION_SLEEP,
        reraise=True)[0]
    if hasattr(self.device, "firmware_version"):
      firmware_version = self.device.get_property("firmware_version")
      logging.info("DUT: %s, firmware version: %s", self.device_name,
                   firmware_version)

  def setup_test(self) -> None:
    """Starts a new log for the device."""
    super().setup_test()
    if hasattr(self.device, "start_new_log"):  # auxiliary devices do not log
      self.device.start_new_log(log_name_prefix=self.get_full_test_name())

  def teardown_test(self) -> None:
    """Ensures device is connected."""
    if self.device:
      self.device.check_device_connected()
    super().teardown_test()

  def teardown_class(self) -> None:
    """Close device as needed."""
    if self.device:
      self.device.close()


def main(*args, **kwargs):
  return mobly_base.main(*args, **kwargs)
