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

"""Utilities for pty process communications."""
import glob
import os

from gazoo_device import errors


def get_build_path_from_command(command: str) -> str:
  """Returns the directory path from a pty process launch command.

  Args:
    command: The pty process launch command.
  """
  return os.path.dirname(command.split()[0])


def get_launch_command(build_path: str,
                       *,
                       device_image_path_pattern: str,
                       launch_command_template: str,
                       **launch_command_kwargs) -> str:
  """Returns the launch command string from the given command template.

  Args:
    build_path: The path to the simulator build directory.
    device_image_path_pattern: The glob path pattern to device image file,
      can be relative to the build path.
    launch_command_template: The string template to launch command, only
      named formatting values are allowed, e.g. "cmd {device_dir_path}".
    **launch_command_kwargs: Extra keyword values for launch_command_template.
  """
  if not os.path.isabs(device_image_path_pattern):
    device_image_path_pattern = os.path.join(build_path,
                                             device_image_path_pattern)
  device_image_paths = glob.glob(device_image_path_pattern)
  device_image_path = None
  if device_image_paths:
    device_image_path = device_image_paths[0]
  else:
    raise errors.DeviceError("get_launch_command didn't find any simulator "
                             f"images in {device_image_path_pattern}.")
  device_image_dir_path = os.path.dirname(device_image_path)
  if build_path.endswith("/"):
    build_path = build_path[:-1]
  return launch_command_template.format(
      build_dir_path=build_path,
      device_image_dir_path=device_image_dir_path,
      **launch_command_kwargs)
