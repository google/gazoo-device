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

"""Module for patching Python fire library."""
from __future__ import print_function
import sys
from fire import core
from fire import completion
from fire import inspectutils


def display(lines, out):
    """Display text to user.

    Args:
        lines (str): lines of text to display
        out (object): file object used by interpreter for output

    Note:
        original behavior: lines displayed in scrollable window, similar to "less" shell command.
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
        class_attrs (dict): determines how class members will be treated for visibility,
                            defaulting to GetClassAttrsDict.
        verbose (bool): whether to include private members.

    Returns:
      list: of tuples (member_name, member) of all members of the component.

    Note:
        original behavior: component members are collected using inspect.getmembers.
        behavior with patch: component members are collected using _safely_get_members.
    """
    if isinstance(component, dict):
        members = component.items()
    else:
        members = _safely_get_members(component)

    # if class_attrs has not been provided, compute it.
    if class_attrs is None:
        try:
            class_attrs = inspectutils.GetClassAttrsDict(component)  # g3 fire
        except AttributeError:
            class_attrs = completion.GetClassAttrsDict(component)

    return [
        (member_name, member) for member_name, member in members
        if completion.MemberVisible(component, member_name, member, class_attrs=class_attrs,
                                    verbose=verbose)
    ]


def get_member(component, args):
    """Returns a member (function, property, etc.) of a component by consuming CLI arguments.

    Args:
        component (object): the component from which to get the member.
        args (list): arguments from which to consume in the search for the member.

    Returns:
        tuple: (member, consumed_args, remaining_args)
            member: the member that was found by consuming args.
            consumed_args: the args that were consumed by getting this member.
            remaining_args: the remaining args that haven't been consumed yet.

    Raises:
        FireError: if the provided arguments do not correspond to a component member.

    Note:
        original behavior: component members are collected using inspect.getmembers.
        behavior with patch: component members are collected using _safely_get_members.
    """
    arg = args[0]
    arg_names = [
        arg,
        arg.replace('-', '_'),  # treat '-' as '_'.
    ]

    for arg_name in arg_names:
        members = dict(_safely_get_members(component, member_names=[arg_name]))
        if arg_name in members:
            return members[arg_name], [arg], args[1:]

    raise core.FireError('Could not consume arg:', arg)


def apply_patch():
    """Applies monkey patch by attaching custom functions to the Python Fire module."""
    core.Display = display
    core._GetMember = get_member
    completion.VisibleMembers = visible_members


def _safely_get_members(component, member_names=None):
    """Gather stable members of a component.

    Args:
        component (object): The component from which to get the members from.
        member_names (list): List of names of members to gather.

    Returns:
        list: of stable component members as tuples (member name, member instance).

    Note:
        This function was designed to silence exceptions thrown by unstable devices when all
        device properties were previously accessed by inspect.getmembers.
    """
    all_member_names = dir(component)
    member_names = member_names or all_member_names

    members = []
    for attr_name in member_names:
        if attr_name in all_member_names:
            try:
                attribute = getattr(component, attr_name)
                members.append((attr_name, attribute))
            except Exception:
                pass  # ignore members that raise exceptions

    return members
