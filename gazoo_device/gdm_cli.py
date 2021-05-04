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

"""Gazoo Device Manager CLI.

The CLI is generated dynamically by Python Fire:
https://github.com/google/python-fire.
"""
import sys
from typing import Dict, Optional, Sequence

import fire

import gazoo_device
from gazoo_device import errors
from gazoo_device import extensions
from gazoo_device import fire_manager
from gazoo_device import fire_patch
from gazoo_device import gdm_logger
from gazoo_device import package_registrar

logger = gdm_logger.get_logger()

VERSION_FLAG = "-v"
FLAG_MARKER = "--"
OMIT_FLAGS = ["help"]
_CLI_NAME = "gdm"


def execute_command(command: Optional[str] = None,
                    cli_name: str = _CLI_NAME) -> int:
  """Executes the CLI command through Python Fire.

  Args:
    command: Passed to Python Fire. If None, sys.argv are used instead.
    cli_name: Name of the CLI executable ("gdm").

  Returns:
    Error code: 0 if command was successful, non-zero otherwise.
  """
  # Parse flags out of commands. E.g. "gdm --debug - devices" ->
  # flags = {"debug": True}, commands = ["-", "devices"].
  if command:
    args = command.split()
  else:
    args = sys.argv[1:]
  flags = _get_flags(args)
  commands = [arg for arg in args if arg[len(FLAG_MARKER):] not in flags.keys()]

  # Instantiate FireManager instance with provided flags
  manager_inst = fire_manager.FireManager(**flags)

  # Execute CLI command
  exit_code = 0
  try:
    fire_patch.apply_patch()
    fire.Fire(manager_inst, commands, name=cli_name)
  except (ValueError, errors.DeviceError) as err:
    logger.error((repr(err)))
    exit_code = 1
  except KeyboardInterrupt:
    exit_code = 2
  finally:
    manager_inst.close()

  return exit_code


def _get_flags(args: Sequence[str]) -> Dict[str, bool]:
  """Parses flags out of array of CLI args.

  Flags in OMIT_FLAGS dict will not be returned.

  Args:
    args: CLI arguments provided by the user.

  Returns:
    Parsed flags to pass to the CLI.
  """
  flags = {}
  for arg in args:
    if arg.startswith(FLAG_MARKER):
      flag_name = arg[len(FLAG_MARKER):]
      if flag_name and flag_name not in OMIT_FLAGS:
        flags[flag_name] = True
    else:
      break  # Ignore flags after initial CLI call
  return flags


def main(command: Optional[str] = None) -> int:
  """Main function for Gazoo Device Manager (gazoo_device) package.

  Args:
    command: Passed to Python Fire. If None, sys.argv are used instead.

  Returns:
    Error code: 0 if command was successful, non-zero otherwise.
  """
  package_registrar.import_and_register_cli_extension_packages()

  if VERSION_FLAG in sys.argv or (command and VERSION_FLAG in command):
    logger.info(f"Gazoo Device Manager {gazoo_device.version}")
    package_versions = extensions.get_registered_package_info()
    logger.info(f"Registered extension packages: {package_versions}")
    return 0

  return execute_command(command)


if __name__ == "__main__":
  main()
