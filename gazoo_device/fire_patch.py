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

"""Module for patching Python fire library."""
import sys

import fire


def display(lines, out):
  """Display text to user.

  Args:
      lines (str): lines of text to display
      out (object): file object used by interpreter for output
  Note:
      original behavior: lines displayed in scrollable window, similar to
        "less" shell command.
      behavior with patch: lines printed to the console in standard format.
  """
  if not (out is sys.stdout or out is sys.stderr):
    out = sys.stdout
  text = '\n'.join(lines) + '\n'
  out.write(text)


def visible_members(component, class_attrs=None, verbose=False):
  """Returns a list of the members of the given component.

  Args:
      component (object): the component whose members to list.
      class_attrs (dict): determines how class members will be treated for
        visibility, defaulting to GetClassAttrsDict.
      verbose (bool): whether to include private members.

  Returns:
    list: of tuples (member_name, member) of all members of the component.

  Note:
      original behavior: component members are collected using
      inspect.getmembers.
      behavior with patch: component members are collected using
      _safely_get_members.
  """
  if isinstance(component, dict):
    members = component.items()
  else:
    members = _safely_get_members(component)

  # if class_attrs has not been provided, compute it.
  if class_attrs is None:
    # pytype: disable=module-attr
    try:
      class_attrs = fire.inspectutils.GetClassAttrsDict(component)
    except AttributeError:
      class_attrs = fire.completion.GetClassAttrsDict(component)
    # pytype: enable=module-attr

  return [(
      member_name, member
  ) for member_name, member in members if fire.completion.MemberVisible(
      component, member_name, member, class_attrs=class_attrs, verbose=verbose)]


def apply_patch():
  """Applies monkey patch by attaching custom functions to the Python Fire module."""
  fire.core.Display = display
  fire.completion.VisibleMembers = visible_members


def _safely_get_members(component):
  """Gather stable members of a component.

  Args:
      component (object): The component from which to get the members from.

  Returns:
      list: of stable component members as tuples (member name, member
      instance).

  Note:
      This function was designed to silence exceptions thrown by unstable
      devices when all
      device properties were previously accessed by inspect.getmembers.
  """
  members = []
  for attr_name in dir(component):
    try:
      attribute = getattr(component, attr_name)
      members.append((attr_name, attribute))
    except Exception:
      pass  # ignore members that raise exceptions

  return members
