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

"""Implementation of the embedded script capability for DLI powerswitch.

Allows more precision to operations invloving time senstivity to avoid
any latencies incured due to REST API calls over DLI powerswitch.
"""
from typing import Any, Callable, Sequence

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import embedded_script_base

logger = gdm_logger.get_logger()

API_ENDPOINTS = {
    "GET_RUNNING_THREADS": "script/threads/",
    "START_SCRIPT": "script/start/",
    "TERMINATE_SCRIPT": "script/stop/"
}
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-CSRF": "x"
}


class EmbeddedScriptDliPowerswitch(embedded_script_base.EmbeddedScriptBase):
  """Implementation of the embedded_script capability."""

  def __init__(self, ip_address: str, base_url: str, device_name: str,
               http_fn: Callable[..., str]):
    """Initializes an instance of the embedded script capability.

    Args:
        ip_address: The IP address of the Powerswitch.
        base_url: Base url for REST api.
        device_name: Name of the device this capability is attached.
        http_fn: A function to send GET and POST http commands.
    """
    super().__init__(device_name=device_name)
    self._ip_address = ip_address
    self._base_url = base_url
    self._http_fn = http_fn

  def get_current_running_threads(self) -> str:
    """Returns current running threads over powerswitch.

    Returns:
      threads: Formatted with thread ids and script name. Response received
        from callable is expected to have JSON text. If there are threads
        running response like '{9:{label:test_script (admin via web ui) ON 2}}'
        can be expected. If no threads running an empty JSON text '{}' can be
        expected
    """

    threads_url = (self._base_url.format(ip=self._ip_address) +
                   API_ENDPOINTS["GET_RUNNING_THREADS"])
    threads = self._http_fn(method="GET", url=threads_url, headers=HEADERS)
    return threads

  @decorators.CapabilityLogDecorator(logger)
  def run(
      self, script_name: str, script_args: Sequence[Any] = ()) -> str:
    """Runs the embedded script over powerswitch.

    Script needs to be deployed over powerswitch manually before using run.
    Method returns numeric value for thread id in form of string.
    example - '21'. The same id can be passed to terminate method as it is
    to stop the execution of script .
    Args:
      script_name: Name of the script to run.
      script_args: Sequence of arguments if any consumed by script in order.

    Returns:
      str: Formatted GET/POST HTTP response.
    """
    script_url = (self._base_url.format(ip=self._ip_address) +
                  API_ENDPOINTS["START_SCRIPT"])
    script_arguments = ",".join(map(str, script_args))
    data = [{
        "user_function":
            script_name,
        "source":
            f"{script_name}({script_arguments})"
    }]
    response = self._http_fn(
        method="POST", url=script_url, headers=HEADERS, json_data=data)
    return response

  @decorators.CapabilityLogDecorator(logger)
  def terminate(self, thread_id: str = "all") -> str:
    """Terminates the thread executing the script.

    Terminates thread with provided thread_id, if no thread_id provided
    terminates all threads under execution.

    Args:
      thread_id: Id of thread executing the script.
        Defaults to 'all', terminating all threads under execution.

    Returns:
      str: Formatted GET/POST HTTP response.
    """
    script_url = (self._base_url.format(ip=self._ip_address) +
                  API_ENDPOINTS["TERMINATE_SCRIPT"])
    data = [thread_id]
    response = self._http_fn(
        method="POST", url=script_url, headers=HEADERS, json_data=data)
    return response

