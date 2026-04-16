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

"""Utility module for using the multiprocessing library."""
import contextlib
import logging
import multiprocessing
import os
import sys
from typing import Generator, Optional
from gazoo_device import config

_MP_CONTEXT = multiprocessing.get_context("spawn")


def _get_logger() -> logging.Logger:
  """Returns the Gazoo Device Manager logger. Same as gdm_logger.get_logger().

  We can't import gdm_logger in this module to avoid a circular import.
  """
  return logging.getLogger(config.LOGGER_NAME)


def get_context() -> multiprocessing.context.SpawnContext:
  """Returns a multiprocessing context (forkserver- or spawn-based)."""
  return _MP_CONTEXT


def if_spawn_run_and_exit():
  """If this is a spawned process, hijacks process execution logic via exec().

  No-op in the open-source version.
  """


def _get_multiprocessing_spawn_executable() -> Optional[str]:
  """Returns decoded multiprocessing.spawn.get_executable()."""
  executable = multiprocessing.spawn.get_executable()
  if executable is not None:
    executable = os.fsdecode(executable)
  return executable


@contextlib.contextmanager
def configure_switchboard_multiprocessing() -> Generator[None, None, None]:
  """Configures multiprocessing for Switchboard processes."""
  spawn_executable_before = _get_multiprocessing_spawn_executable()
  try:
    yield
  finally:
    multiprocessing.spawn.set_executable(spawn_executable_before)


def configure_multiprocessing() -> None:
  """Configures multiprocessing. No-op in the open source version."""
