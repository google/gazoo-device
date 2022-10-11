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
import contextlib
import logging
import os.path  # pylint: disable=unused-import
from typing import Type

from gazoo_device import manager
from gazoo_device.tests.functional_tests.utils import suite_filter
from gazoo_device.utility import retry
from gazoo_device.tests import functional_tests

_CREATION_TIMEOUT = 120
_RECONNECT_TIMEOUT = 60
_CREATION_SLEEP = 10
DIRECTORY = os.path.abspath(os.path.dirname(functional_tests.__file__))
_CONFIG_DIRS = (os.path.join(DIRECTORY,"configs"),)

DeviceType = suite_filter.DeviceType


def whether_implements_matter_endpoint(
    device_class: Type[DeviceType],
    device_name: str,
    endpoint_name: str) -> bool:
  """Returns whether the device implements the matter endpoint."""
  if not device_class.has_capabilities(["matter_endpoints"]):
    return False

  with contextlib.closing(manager.Manager()) as mgr:
    with mgr.create_and_close_device(device_name) as device:
      return device.matter_endpoints.has_endpoints([endpoint_name])


class GDMTestBase(suite_filter.SuiteFilterBase):
  """Base class for GDM functional test suites."""
  _CONFIG_DIRS = _CONFIG_DIRS

  def __init__(self, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    self.devices = []
    self.device = None
    self.testing_properties = None

  def setup_class(self) -> None:
    """Creates a device instance."""
    super().setup_class()
    self.testing_properties = self.user_params
    self.devices = retry.retry(
        func=self.register_controller,
        func_args=(self._CONTROLLER_MODULE,),
        timeout=_CREATION_TIMEOUT,
        interval=_CREATION_SLEEP,
        reraise=True)
    self.device = self.devices[0]
    # Check attribute presence on the class rather than the instance to avoid
    # accessing the property during the check.
    for i, device in enumerate(self.devices):
      if hasattr(type(device), "firmware_version"):
        firmware_version = device.get_property(
            "firmware_version", raise_error=False)
        logging.info("DUT %s: %s, firmware version: %s", i, device.name,
                     firmware_version)

  def setup_test(self) -> None:
    """Starts a new log for the device."""
    super().setup_test()
    if hasattr(self.device, "start_new_log"):  # auxiliary devices do not log
      self.device.start_new_log(log_name_prefix=self.get_full_test_name())

  def teardown_test(self) -> None:
    """Ensures devices are connected."""
    for device in self.devices:
      device.check_device_connected()
    super().teardown_test()

  def teardown_class(self) -> None:
    """Close devices as needed."""
    for device in self.devices:
      device.close()
    self.devices = []
    self.device = None
    super().teardown_class()


def main(*args, **kwargs):
  return mobly_base.main(*args, **kwargs)
