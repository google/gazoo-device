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

"""Gazoo Device Manager Fire - CLI using Python Fire and Python API for testing Gazoo devices."""
from __future__ import absolute_import
from __future__ import print_function
import fire
import sys
from gazoo_device import errors
from gazoo_device import fire_manager
from gazoo_device import fire_patch
from gazoo_device import gdm_logger
from gazoo_device import version

logger = gdm_logger.get_gdm_logger()

VERSION_FLAG = "-v"
FLAG_MARKER = "--"
OMIT_FLAGS = ["help"]


def get_flags(args):
    """Parse flags out of array of CLI args.

    Args:
        args (arr): array of arguments provided by the user.

    Returns:
        dict: dictionary of flags to pass to the CLI.

    Note:
        Flags in OMIT_FLAGS dict will not be returned.
    """
    flags = {}
    for arg in args:
        if arg.startswith(FLAG_MARKER):
            flag_name = arg[len(FLAG_MARKER):]
            if flag_name and flag_name not in OMIT_FLAGS:
                flags[flag_name] = True
        else:
            break  # ignore flags after initial CLI call
    return flags


def main(command=None):
    """Main function for Gazoo Device (gazoo_device) package.

    Args:
        command (string): command to pass to Python Fire.

    Returns:
        int: 0 if success, 2 if not.
    """
    retval = 0
    if VERSION_FLAG in sys.argv or (command and VERSION_FLAG in command):
        logger.info('Gazoo Device Manager {}'.format(version))
        return retval

    # parse flags out of commands
    # e.g. "gdm --debug - devices" -> flags = {"debug": True}, commands = ["-", "devices"]
    if command:
        args = command.split()
    else:
        args = sys.argv[1:]
    flags = get_flags(args)
    commands = [arg for arg in args if arg[len(FLAG_MARKER):] not in flags.keys()]

    # instantiate FireManager instance with provided flags
    manager_inst = fire_manager.FireManager(**flags)

    # execute CLI with commands
    try:
        fire_patch.apply_patch()
        fire.Fire(manager_inst, commands, name='gdm')
    except (ValueError, errors.GazooDeviceError) as err:
        logger.error((repr(err)))
        retval = 1
    except KeyboardInterrupt:
        retval = 2
    finally:
        manager_inst.close()

    return retval


if __name__ == '__main__':
    main()
