# Copyright 2020 Google LLC
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

"""Gazoo Device Manager (gdm) is a single utility for control of a variety of smart devices.

It manages communication and setup of Gazoo devices to simplify daily tasks (software updating
a unit, getting logs) as well as serving as a device driver for automated (python) tests.
Areas of focus: ease of use (including ease of installation, setup, updating), robustness,
and scalability.

Examples of functionality:
    * Detecting and setting up devices when they are attached (create config files automatically).
    * Setting up shared permissions/file locations so all users can access test hardware (if they
      can log onto the pc).
    * Sharing a single device UART for logging and commands, to allow logs to be streamed "live"
      during a test while still sending commands/responses during a test.

Command Line Interface (CLI):
    There are several groups of commands.
        "Manager" commands operate on local config files on the pc.
            The command may talk to devices (detect), but they don't change the state of the
            device (i.e. read-only)
            The command may change the config files stored on the pc, to detect new devices,
            add an alias, etc.
        "Device" commands talk to or modify a Gazoo device.
            This includes upgrade, reboot, etc.
            For manager commands, the format is "gdm <command> <device> [<additional arguments>]".
            For example: gdm log cambrionix-1234.
            For device commands, the format is "gdm issue <device> - <command> [<arguments>]".
            For example: gdm issue cambrionix-1234 - reboot.

    You can get more details on a particular command at the command line with
    "gdm SomeCmd -h"
    For example::  gdm upgrade -h

Python API:
    ToDo: Add more API overview docs...
    Note: help(someCmd) will show the docstring for that command.
    Please comment about commands that have a confusing/missing
    docstring and we will improve it.

"""
from __future__ import absolute_import
import gc
import logging
import multiprocessing
import os
import signal
import sys
from gazoo_device import gdm_logger
from gazoo_device.base_classes import *  # pylint: disable=wildcard-import
from gazoo_device.primary_devices import *  # pylint: disable=wildcard-import
from gazoo_device.device_detector import DeviceDetector
from gazoo_device.manager import Manager
import gazoo_device.utility.common_utils
import gazoo_device.utility.reflection_utils

from gazoo_device._version import version
__version__ = version

# Defend against inadvertent basicConfig, which adds log noise
logging.getLogger().addHandler(logging.NullHandler())


# Ensure that atexit handlers run when killed by SIGTERM
def graceful_exit(*args, **kwargs):  # pylint: disable=unused-argument
    raise SystemExit(0)


signal.signal(signal.SIGTERM, graceful_exit)


if sys.platform == "darwin" and sys.version_info >= (3, 8):
    # Workaround for b/160958582: Python >= 3.8 defaults to "spawn" start method on Macs.
    # GDM isn't compatible with "spawn" yet, so force "fork" method on Macs until then.
    multiprocessing.set_start_method("fork", force=True)


# Set up logger
gdm_logger.initialize_logger()


def _after_fork():
    """Re-enable garbage collection in both parent & child process."""
    gc.enable()


def _before_fork():
    """Collect garbage, disable periodic GC until after fork, and flush logger messages.

    Note:
        This ensures logging thread is not logging anything during os.fork() call.
        If logging thread is logging during os.fork() call, children may be forked with an
        acquired stdout lock, which will cause a deadlock when the child process finishes.
        Child processes attempt to flush the stdout buffer before exiting. If a child process
        is forked with an acquired stdout buffer lock, it will hang indefinitely when trying to
        flush stdout because it cannot acquire the lock.
    """
    gc.disable()
    gc.collect()
    gdm_logger.flush_queue_messages()


# Periodic GC is active in child processes created via os.fork.
# Trigger a collection in the parent process prior to forking to prevent parent process's
# garbage from being copied over to the child and later being collected in each process.
# See b/150018610.
gazoo_device.utility.common_utils.register_at_fork(before=_before_fork,
                                                   after_in_parent=_after_fork,
                                                   after_in_child=_after_fork)

# Dynamically identify all device classes and capabilities supported by GDM
gazoo_device.utility.reflection_utils.identify_all_supported_classes()
