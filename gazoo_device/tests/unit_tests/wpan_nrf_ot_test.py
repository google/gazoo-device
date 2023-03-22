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
"""Capability unit test for wpan_nrf_ot module."""

from gazoo_device.auxiliary_devices import nrf_openthread
from gazoo_device.tests.unit_tests.capability_tests.mixins import wpan_cli_based_test
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.tests.unit_tests.utils import nrf_openthread_device_logs


class WpanNrfOtTest(
    fake_device_test_case.FakeDeviceTestCase,
    wpan_cli_based_test.WpanOtTestMixin,
):
  """Unit test for WpanNrfOt."""

  def setUp(self):
    """Sets up fake device instance."""
    super().setUp()
    self.setup_fake_device_requirements("nrfopenthread-1234")
    self.fake_responder.behavior_dict = {
        **nrf_openthread_device_logs.DEFAULT_BEHAVIOR,
    }
    self.uut = nrf_openthread.NrfOpenThread(
        self.mock_manager,
        self.device_config,
        log_directory=self.artifacts_directory,
    )

  def use_neighbor_table_v2(self):
    """Makes fake responder switch to neighbor table v2."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.NEIGHBOR_TABLE_V2_BEHAVIOR
    )

  def use_neighbor_table_v3(self):
    """Makes fake responder switch to neighbor table v3."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.NEIGHBOR_TABLE_V3_BEHAVIOR
    )

  def use_state_disabled(self):
    """Makes fake responder switch to disabled state."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses(
            [{"cmd": "state", "resp": "disabled\nDone\n", "code": 0}]
        )
    )

  def use_ifconfig_up(self):
    """Makes fake responder ifconfig returns up."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses(
            [{"cmd": "ifconfig", "resp": "up\nDone\n", "code": 0}]
        )
    )

  def use_ifconfig_down(self):
    """Makes fake responder ifconfig returns down."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses(
            [{"cmd": "ifconfig", "resp": "down\nDone\n", "code": 0}]
        )
    )

  def use_cli_normal_output(self):
    """Makes fake responder cli return normal output."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "normal output",
            "resp": "line 1\nline 2\nDone\n",
            "code": 0,
        }])
    )

  def use_cli_error_output(self):
    """Makes fake responder cli return error output."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "error output",
            "resp": "line 1\nline 2\nError 1: error\n",
            "code": 0,
        }])
    )

  def use_cli_malformed_output(self):
    """Makes fake responder cli return malformed output."""
    self.fake_responder.behavior_dict.update(
        nrf_openthread_device_logs.make_device_responses([{
            "cmd": "malformed output",
            "resp": "Malformed output\n",
            "code": 0,
        }])
    )

  def test_csl_period(self):
    """Verifies csl_period on success."""
    self.assertEqual(self.uut.wpan.csl_period, 3125)

  def test_set_csl_period(self):
    """Verifies set_csl_period on success."""
    self.uut.wpan.set_csl_period(3125)

  def test_csl_timeout(self):
    """Verifies csl_timeout on success."""
    self.assertEqual(self.uut.wpan.csl_timeout, 100)

  def test_set_csl_timeout(self):
    """Verifies set_csl_timeout on success."""
    self.uut.wpan.set_csl_timeout(100)


if __name__ == "__main__":
  fake_device_test_case.main()
