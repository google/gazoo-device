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
"""Utility module for interaction with ssh."""

import contextlib
import os
import subprocess
import tempfile
from typing import Generator

from gazoo_device import data_types
from gazoo_device import gdm_logger
from gazoo_device.utility import host_utils
from gazoo_device.utility import retry

logger = gdm_logger.get_logger()


@contextlib.contextmanager
def port_forward(username: str,
                 address: str,
                 key_info: data_types.KeyInfo,
                 remote_port: int,
                 remote_host: str = "localhost") -> Generator[str, None, None]:
  """Initializes an SSH port forward.

  Args:
    username: username which scp should use.
    address: IP address of the device.
    key_info: SSH key to use.
    remote_port: Remote port to forward to.
    remote_host: Remote host to forward to.

  Yields:
    The path of local unix socket which is forwarded to the remote.
  """
  with tempfile.TemporaryDirectory() as tempdir:
    local = f"{tempdir}/ssh_forward"
    remote = f"{remote_host}:{remote_port}"
    key_args = (["-i", host_utils.get_key_path(key_info)]
                if key_info is not None else [])
    ssh_command = [
        "ssh", "-N", *host_utils.DEFAULT_SSH_OPTIONS, *key_args,
        f"{username}@{address}", f"-L{local}:{remote}"
    ]
    logger.debug(f"Forking ssh command {ssh_command}")

    with subprocess.Popen(ssh_command) as process:
      try:
        retry.retry(lambda: os.path.exists(local), is_successful=lambda x: x)
        yield local
      finally:
        process.terminate()
        try:
          process.wait(timeout=1)
        except subprocess.TimeoutExpired:
          process.kill()
          raise
