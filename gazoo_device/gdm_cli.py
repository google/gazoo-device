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

"""Gazoo Device Manager CLI.

The CLI is generated dynamically by Python Fire:
https://github.com/google/python-fire.
"""
import sys
from typing import Dict, NoReturn, Optional, Sequence

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


def _create_manager_for_cli(
    manager_kwargs: Dict[str, bool]) -> fire_manager.FireManager:
  """Returns a Manager instance to be used by the CLI.

  Args:
    manager_kwargs: FireManager __init__ keyword arguments.

  The Manager class used by the CLI includes CLI-only methods from FireManager
  and CLI-only methods from Manager CLI mixins provided by extension packages.
  """
  extended_manager_class = type(
      "ExtendedFireManager",
      (*extensions.manager_cli_mixins, fire_manager.FireManager),
      {})
  logger.debug("ExtendedFireManager method resolution order: "
               f"{extended_manager_class.__mro__}")
  return extended_manager_class(**manager_kwargs)


def _execute_command(command: Optional[str] = None,
                     cli_name: str = _CLI_NAME) -> int:
  """Executes the CLI command through Python Fire."""
  # Parse flags out of commands. E.g. "gdm --debug - devices" ->
  # flags = {"debug": True}, commands = ["-", "devices"].
  if command:
    args = command.split()
  else:
    args = sys.argv[1:]
  flags = _get_flags(args)
  commands = [arg for arg in args if arg[len(FLAG_MARKER):] not in flags.keys()]
  manager_inst = _create_manager_for_cli(flags)

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


def main(command: Optional[str] = None, cli_name: str = _CLI_NAME) -> NoReturn:
  """Main function for Gazoo Device Manager (gazoo_device) package.

  Args:
    command: Passed to Python Fire. If None, sys.argv are used instead.
    cli_name: Name of the CLI executable ("gdm").

  Raises:
    SystemExit: always calls sys.exit(<return code>).
  """
  package_registrar.import_and_register_cli_extension_packages()

  if VERSION_FLAG in sys.argv or (command and VERSION_FLAG in command):
    logger.info(f"Gazoo Device Manager {gazoo_device.version}")
    package_versions = extensions.get_registered_package_info()
    logger.info(f"Registered extension packages: {package_versions}")
    sys.exit(0)

  sys.exit(_execute_command(command, cli_name))


if __name__ == "__main__":
  main()
