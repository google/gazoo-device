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

"""Unit tests for the embedded_script_dli_powerswitch capability."""
from unittest import mock

from gazoo_device.auxiliary_devices import dli_powerswitch
from gazoo_device.capabilities import embedded_script_dli_powerswitch

from gazoo_device.tests.unit_tests.utils import unit_test_case


class EmbeddedScriptDliPowerswitchTests(unit_test_case.UnitTestCase):
  """Unit tests for embedded_script capability for DLI powerswitch."""

  def setUp(self):
    super().setUp()
    self._name = "powerswitch-1234"
    self._ip_address = "123.45.67.89"
    self._base_url = dli_powerswitch.HTTP_FRAMEWORK
    self._headers = embedded_script_dli_powerswitch.HEADERS
    self._api_endpoints = embedded_script_dli_powerswitch.API_ENDPOINTS
    self._write_command = mock.MagicMock()
    self.uut = embedded_script_dli_powerswitch.EmbeddedScriptDliPowerswitch(
        ip_address=self._ip_address,
        base_url=self._base_url,
        device_name=self._name,
        http_fn=self._write_command
        )

  def test_001_script_run_with_args(self):
    """Verify run_script is called successfully with arguments."""
    script_name = "fake_script"
    script_args = [1, "abc", 1345]
    script_arguments = ",".join(map(str, script_args))
    url = (self._base_url.format(ip=self._ip_address) +
           self._api_endpoints["START_SCRIPT"])
    data = [{
        "user_function":
            script_name,
        "source":
            "{script_name}({script_arguments})".format(
                script_name=script_name, script_arguments=script_arguments)
    }]
    kwargs = {
        "method": "POST",
        "url": url,
        "headers": self._headers,
        "json_data": data
    }

    self.uut.run(script_name=script_name, script_args=script_args)
    self.assertTrue(self.uut._http_fn.called)
    self.assertEqual(kwargs, self.uut._http_fn.call_args[1])

  def test_002_script_run_without_args(self):
    """Verify run_script is called successfully without arguments."""
    script_name = "fake_script"
    script_arguments = ""
    url = (self._base_url.format(ip=self._ip_address) +
           self._api_endpoints["START_SCRIPT"])
    data = [{
        "user_function":
            script_name,
        "source":
            "{script_name}({script_arguments})".format(
                script_name=script_name, script_arguments=script_arguments)
    }]
    kwargs = {
        "method": "POST",
        "url": url,
        "headers": self._headers,
        "json_data": data
    }

    self.uut.run(script_name=script_name)
    self.assertTrue(self.uut._http_fn.called)
    self.assertEqual(kwargs, self.uut._http_fn.call_args[1])

  def test_003_terminate_script(self):
    """Verify terminate_script is called for all threads successfully."""
    url = (self._base_url.format(ip=self._ip_address) +
           self._api_endpoints["TERMINATE_SCRIPT"])
    data = ["all"]
    kwargs = {
        "method": "POST",
        "url": url,
        "headers": self._headers,
        "json_data": data
    }
    self.uut.terminate()
    self.assertTrue(self.uut._http_fn.called)
    self.assertEqual(kwargs, self.uut._http_fn.call_args[1])

  def test_004_terminate_script_with_thread_id(self):
    """Verify terminate_script is called for given thread successfully."""
    url = (self._base_url.format(ip=self._ip_address) +
           self._api_endpoints["TERMINATE_SCRIPT"])
    data = ["007"]
    kwargs = {
        "method": "POST",
        "url": url,
        "headers": self._headers,
        "json_data": data
    }
    self.uut.terminate(thread_id="007")
    self.assertTrue(self.uut._http_fn.called)
    self.assertEqual(kwargs, self.uut._http_fn.call_args[1])

if __name__ == "__main__":
  unit_test_case.main()
