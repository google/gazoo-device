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
import signal
import sys

from gazoo_device import _version
from gazoo_device import gazoo_device_controllers
from gazoo_device import gdm_logger
from gazoo_device import manager
from gazoo_device import mobly_controller
from gazoo_device import package_registrar
from gazoo_device.utility import multiprocessing_utils
from gazoo_device.utility import signal_utils

Manager = manager.Manager
register = package_registrar.register
version = _version.version
__version__ = _version.version

# For Mobly integration
MOBLY_CONTROLLER_CONFIG_NAME = "GazooDevice"
create = mobly_controller.create
destroy = mobly_controller.destroy
get_info = mobly_controller.get_info
get_manager = mobly_controller.get_manager

multiprocessing_utils.configure_multiprocessing()

# Defend against inadvertent basicConfig, which adds log noise
logging.getLogger().addHandler(logging.NullHandler())

# Ensure that 'finally' clauses and atexit handlers run when killed by SIGTERM.
signal.signal(signal.SIGTERM, signal_utils.handle_sigterm)


# Set up logger
gdm_logger.initialize_logger()


# Register device classes and capabilities built into GDM
package_registrar.register(gazoo_device_controllers)
