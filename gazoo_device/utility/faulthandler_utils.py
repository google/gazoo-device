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

"""Utility module for using the faulthandler.

This module installs fault handlers which dump tracebacks for all active threads
periodically and whenever SIGTERM is received. This is useful for debugging
unexpected process terminations and hanging processes.
"""
# import atexit
# import datetime
import faulthandler
import io
import os

from gazoo_device.utility import signal_utils

_FAULTHANDLER_PERIOD_S = 60 * 5


def _stop_traceback_dumps(file: io.TextIOWrapper) -> None:
  """Stops traceback dumps and removes file if empty or sigterm hasn't occurred.

  This function will run at the end of the process only if there is no unhandled
  signal. Since sigerm is handled by GDM, it will also run on receiving sigterm
  signal. For more details, refer to b/262596084.
  - We want to preserve faulthandler logs in the event we have a hung process
  that is killed by a sigterm signal.
  - We want to remove faulthandler logs if the process exited gracefully since
  there is no use for the faulthandler logs of a process that exited
  gracefully.

  Args:
    file: File containing the faulthandlers logs.
  """
  faulthandler.cancel_dump_traceback_later()
  file.close()
  if not os.stat(file.name).st_size or not signal_utils.has_sigterm_occurred():
    os.remove(file.name)


def set_up_faulthandler(folder: str,
                        log_file_name_prefix: str = "",
                        repeat_timeout_s: int = _FAULTHANDLER_PERIOD_S) -> None:
  """Sets up faulthandler for logging."""
  # TODO(b/268778945): Disable faulthandler to investigate
  del folder
  del log_file_name_prefix
  del repeat_timeout_s
  return
  # Setup periodic traceback dumping to investigate hanging issues.
  # pid = os.getpid()
  # time_string = datetime.datetime.now().isoformat().replace(":", "-")
  # os.makedirs(folder, exist_ok=True)
  # prefix = "periodic_stack_trace_dumps"
  # if log_file_name_prefix:
  #   prefix += "_" + log_file_name_prefix
  # file_handle = open(
  #     os.path.join(folder, f"{prefix}_{pid}_{time_string}.log"), "w")
  # faulthandler.enable(file=file_handle)
  # faulthandler.dump_traceback_later(
  #     repeat=True, timeout=repeat_timeout_s, file=file_handle)
  # atexit.register(_stop_traceback_dumps, file_handle)
