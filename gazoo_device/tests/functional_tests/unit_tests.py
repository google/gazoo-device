"""Unit tests for functional test suites and functional test configs."""
from absl.testing import absltest
import gazoo_device

import os
from gazoo_device.tests import functional_tests


class FunctionalTestSuiteAndConfigUnitTests(absltest.TestCase):
  """Unit tests for functional test suites and functional test configs."""

  def test_all_devices_have_a_functional_test_config(self):
    """Checks that there is a test config for every supported device type."""
    supported_device_types = gazoo_device.Manager.get_supported_device_types()
    expected_configs = {f"{device_type}_test_config.json"
                        for device_type in supported_device_types}

    config_dir = os.path.join(
        os.path.abspath(os.path.dirname(functional_tests.__file__)),
        "configs")
    _, _, config_dir_files = os.walk(config_dir)
    configs = [file for file in config_dir_files if file.endswith(".json")]

    self.assertEqual(expected_configs, set(configs))


if __name__ == "__main__":
  absltest.main()
