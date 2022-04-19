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

"""Utilities for handling OS signals."""
import contextlib
import dataclasses
import signal
import sys
import types
from typing import NoReturn, Optional

from gazoo_device import gdm_logger

_LOGGER = gdm_logger.get_logger()

# Any unique exit code works here. To help indicate termination by a signal,
# follow the "signal -> exit code" mapping employed by Bash:
# https://tldp.org/LDP/abs/html/exitcodes.html.
_BASH_SIGTERM_EXIT_CODE = 128 + signal.SIGTERM.value


def handle_sigterm(
    signal_number: int, frame: Optional[types.FrameType]) -> NoReturn:
  """Raises a SystemExit exception with _BASH_SIGTERM_EXIT_CODE return code."""
  del signal_number, frame  # Unused.
  sys.exit(_BASH_SIGTERM_EXIT_CODE)


@dataclasses.dataclass
class _SignalReceiver:
  """Receives a signal and stores the signal state: received or not received."""
  received: bool = False

  def handle_signal(
      self, signal_number: int, frame: Optional[types.FrameType]) -> None:
    """Handles a signal."""
    del signal_number, frame  # Unused.
    # Can't log receipt of the signal because logging library calls may not be
    # reentrant: https://docs.python.org/3/library/logging.html#thread-safety.
    self.received = True


@contextlib.contextmanager
def postpone_sigterm_until_completion():
  """Postpones handling of SIGTERM until completion of the context block."""
  signal_receiver = _SignalReceiver()
  previous_sigterm_handler = signal.getsignal(signal.SIGTERM)
  signal.signal(signal.SIGTERM, signal_receiver.handle_signal)
  _LOGGER.info(
      "Postponing SIGTERM handling until completion of the critical section.")
  try:
    yield
  finally:
    _LOGGER.info(
        "Critical section completed. Resuming SIGTERM signal handling.")
    if previous_sigterm_handler is not None:
      signal.signal(signal.SIGTERM, previous_sigterm_handler)
    else:
      signal.signal(signal.SIGTERM, signal.SIG_DFL)
    if signal_receiver.received:
      _LOGGER.info("A SIGTERM was received during the critical section. "
                   f"Exiting with exit code {_BASH_SIGTERM_EXIT_CODE}.")
      sys.exit(_BASH_SIGTERM_EXIT_CODE)
