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

"""Embedded script interface for powerswitch.

This class defines the API to manage script over powerswitch.
"""
import abc
from typing import Any, Sequence

from gazoo_device.capabilities.interfaces import capability_base


class EmbeddedScriptBase(capability_base.CapabilityBase):
  """Abstract base class defining the API for the embedded script capability."""

  @abc.abstractmethod
  def run(
      self, script_name: str, script_args: Sequence[Any] = ()) -> str:
    """Runs the embedded script over powerswitch.

    Args:
      script_name: Name of the script to run.
      script_args: List of arguments if any consumed by script in order.

    Returns:
      response: Formatted GET/POST HTTP response.
    """

  @abc.abstractmethod
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
