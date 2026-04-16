# Copyright 2023 Google LLC
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

"""Docker queries sent to devices during detection to determine their device type."""
import logging
import subprocess
from typing import Callable
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.detect_criteria import base_detect_criteria
import immutabledict

_DOCKER_COMMANDS = immutabledict.immutabledict({
    "PRODUCT_NAME": "docker ps --filter id={} --format {{{{.Names}}}}",
})


class DockerQuery(base_detect_criteria.QueryEnum):
  PRODUCT_NAME = "product_name"


def _docker_product_name_query(
    address: str, detect_logger: logging.Logger,
    create_switchboard_func: Callable[..., switchboard_base.SwitchboardBase]
) -> str:
  """Gets product name from docker device."""
  del create_switchboard_func  # Unused by _docker_product_name_query
  try:
    name = subprocess.check_output(
        _DOCKER_COMMANDS["PRODUCT_NAME"].format(address).split())
    name = name.decode()
  except subprocess.CalledProcessError as err:
    detect_logger.info(
        "_docker_product_name_query failed for %s: %r", address, err,
        exc_info=True)
    return ""
  return name
