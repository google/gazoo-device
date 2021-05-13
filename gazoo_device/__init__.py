# Copyright 2021 Google LLC
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

"""Gazoo Device Manager (gdm) is a single interface for device interactions.

It manages communication and setup of smart devices to simplify daily tasks
(software updating a unit, getting logs) as well as serving as a device driver
for automated (python) tests.

Areas of focus: ease of use (including ease of installation, setup, updating),
robustness, scalability.

Examples of functionality:
* Detecting and setting up devices when they are attached (create config
  files automatically).
* Setting up shared permissions/file locations so all users can access test
  hardware (if they can log onto the pc).
* Sharing a single device UART for logging and commands, to allow logs to be
  streamed "live" during a test while still sending commands/responses during a
  test.

Command Line Interface (CLI):
There two groups of commands.
"Manager" commands operate on local config files on the pc.
  The command may talk to devices (detect), but they don't change the
  state of the device (i.e. read-only).
  The command may change the config files stored on the pc, to detect
  new devices, add an alias, etc.
  For manager commands, the format is
    "gdm <command> <device> [<additional arguments>]".
    For example: "gdm log cambrionix-1234".
"Device" commands talk to or configure connected devices.
  This includes upgrade, reboot, etc.
  For device commands, the format is
    "gdm issue <device> - <command> [<arguments>]".
  For example: "gdm issue cambrionix-1234 - reboot".

You can get more details on a particular command at the command line with
"gdm man DEVICENAME COMMAND" (does not require a connected device) or
"gdm issue DEVICENAME - COMMAND -- --help" (requires a connected device).
For example: "gdm issue cambrionix-1234 - reboot -- --help"
             "gdm man cambrionix reboot"

Refer to https://github.com/google/gazoo-device for full documentation.
"""
import gc
import logging
import multiprocessing
import os
import signal
import sys

from gazoo_device import _version
from gazoo_device import gazoo_device_controllers
from gazoo_device import gdm_logger
from gazoo_device import manager
from gazoo_device import package_registrar
from gazoo_device.utility import common_utils

Manager = manager.Manager
register = package_registrar.register
version = _version.version
__version__ = _version.version

# Defend against inadvertent basicConfig, which adds log noise
logging.getLogger().addHandler(logging.NullHandler())


# Ensure that atexit handlers run when killed by SIGTERM
def graceful_exit(*args, **kwargs):  # pylint: disable=unused-argument
  raise SystemExit(0)


signal.signal(signal.SIGTERM, graceful_exit)

if sys.platform == "darwin" and sys.version_info >= (3, 8):
  # Workaround for b/160958582: Python >= 3.8 defaults to "spawn" start method
  # on Macs. GDM isn't compatible with "spawn" yet, so use the "fork" method
  # instead.
  multiprocessing.set_start_method("fork", force=True)

# Set up logger
gdm_logger.initialize_logger()


def _after_fork():
  """Re-enables garbage collection in both parent & child process."""
  gc.enable()


def _before_fork():
  """Collects garbage, disables periodic GC, and flushes logger messages.

  This ensures that the logging thread is not logging anything during os.fork()
  calls. If the logging thread is logging during an os.fork() call, child
  processes may be forked with an acquired stdout lock, which will cause a
  deadlock when the child process finishes. Child processes attempt to flush the
  stdout buffer before exiting and will hang indefinitely if forked with an
  acquired stdout buffer lock.
  """
  gc.disable()
  gc.collect()
  gdm_logger.flush_queue_messages()


# Periodic GC is active in child processes created via os.fork.
# Trigger a collection in the parent process prior to forking to prevent
# parent process's garbage from being copied over to the child and later being
# collected in each process. See b/150018610.
common_utils.register_at_fork(before=_before_fork,
                              after_in_parent=_after_fork,
                              after_in_child=_after_fork)

# Register device classes and capabilities built into GDM
package_registrar.register(gazoo_device_controllers)
