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

"""Helper functions for running Python subprocesses."""

import os
import select
import subprocess
import time
from typing import Sequence, Tuple

from gazoo_device import gdm_logger

logger = gdm_logger.get_logger()

_POLL_DELAY = .2


def run_and_stream_output(cmd_args: Sequence[str],
                          timeout: float) -> Tuple[int, str]:
  """Runs commands and streams the output at the same time.

  Python subprocess cannot capture and stream the output at the same time.
  Here we use Popen to pipe the output and log the output simultaneously.

  Args:
    cmd_args: Command args in a sequence.
    timeout: The timeout for running the commands.

  Returns:
    Tuple of (return code, string output).
    The caller is responsible for verifying that the subprocess invocation is
    successful by checking that the return code is zero and that the output
    doesn't contain any lines indicating a failure.

  Raises:
    subprocess.TimeoutExpired: If the subprocess time outs.
  """
  full_output = []
  logger.info("Calling host command {} with timeout {:0.1f}s. "
              "Streaming command output...".format(cmd_args, timeout))
  start_time = time.time()
  with subprocess.Popen(cmd_args,
                        encoding="utf-8",
                        errors="replace",
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT) as proc:
    os.set_blocking(proc.stdout.fileno(), False)
    end_time = start_time + timeout

    # Keep checking whether the process is terminated by Popen.poll().
    # If the process is still running then we dump and store all the output.
    while proc.poll() is None and time.time() < end_time:
      readable, _, _ = select.select([proc.stdout], [], [], _POLL_DELAY)
      if readable:
        output = readable[0].read()
        logger.info(output.rstrip())
        full_output.append(output)

    # Check the process return_code using Popen.wait(1). If the process is
    # not yet ended then it will raise the TimeoutExpired exception.
    try:
      return_code = proc.wait(timeout=1)
    except subprocess.TimeoutExpired:
      proc.terminate()
      if proc.poll() is None:
        proc.kill()
      raise

  logger.info("Host command {} completed in {:0.1f}s with return code {}."
              .format(cmd_args, time.time() - start_time, return_code))
  return return_code, "".join(full_output)
