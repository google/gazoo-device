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

"""Unit tests for functional test suites and functional test configs."""
import json

from absl.testing import absltest
from absl.testing import parameterized
import gazoo_device
from gazoo_device.tests.functional_tests.utils import gdm_test_base
from gazoo_device.tests.functional_tests.utils import suite_filter


class ConfigsBaseTest(parameterized.TestCase):
  """Unit tests for functional test configs."""
  MODULE_NAME = None

  def test_all_devices_have_a_functional_test_config(self):
    """Checks that there is a test config for every supported device type."""
    config_dirs = gdm_test_base._CONFIG_DIRS
    supported_classes = gazoo_device.Manager.get_all_supported_device_classes()
    supported_device_types = [
        device_class.DEVICE_TYPE
        for device_class in supported_classes
        if self.MODULE_NAME in device_class.__module__
    ]
    missing_configs = []
    invalid_configs = []
    missing_key_configs = []
    for device_type in supported_device_types:
      device_name = device_type + "-0000"
      try:
        test_config = suite_filter._get_test_config(
            device_name=device_name, config_dirs=config_dirs)
      except FileNotFoundError as err:
        missing_configs.append(str(err))
      except json.JSONDecodeError:
        invalid_configs.append(device_type)
      required_keys = tuple(label.value for label in suite_filter.TestLabel)
      if not all(key in test_config for key in required_keys):
        missing_key_configs.append(device_type)
    if missing_configs:
      self.fail(f"The following device types are missing: {missing_configs}")
    if invalid_configs:
      self.fail(f"The following configs are invalid: {invalid_configs}")
    if missing_key_configs:
      self.fail("The following device types are missing required keys"
                f"{required_keys}: {missing_key_configs}")

if __name__ == "__main__":
  absltest.main()
