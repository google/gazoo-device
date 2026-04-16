# Copyright 2023 Google LLC
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

r"""Generic expect responders to use.

This is for use in creating side effects for send_and_expect, expect,
click_and_expect, etc.
It allows a user to mock out device responses without expertise in how
expect/expectResponse logic works.
It also allows the user to easily change the behavior between tests as
necessary.

Todo: Refactor expect in the future to be able to be a side effect itself.

Fake responder requires:
- a behavior_dict of logline/response lines generated when a particular
  command/action is given.
- a response, which is simply a loading of responses for when no particular
  action is given.

Note: Both can be empty to imitate a non-responsive device.

Initialization (typically in test setup):
  self.fake_responder = fake_responder.FakeResponder(
    unit_tests.utils.some_device_logs.DEFAULT_BEHAVIOR,
    unit_tests.utils.some_device_logs.DEFAULT_LOG_RESPONSE)

 self.mock_switchboard = MagicMock(spec=switchboard.SwitchboardDefault)
 self.mock_switchboard.device_name = self.uut_name
 self.mock_switchboard.expect.side_effect = self.fake_responder.expect
 self.mock_switchboard.send_and_expect.side_effect = (
   self.fake_responder.send_and_expect)
 ... or whatever else needs to be mocked

 self.mock_manager._create_switchboard.return_value = self.mock_switchboard


Structure:

Each entry in the behavior_dict is a command: response key-value pair.
Note that the value can either be:
- a string (for when just one consistent response is needed)
- an iterator (for when several different responses are needed)

Example (for a Linux device with a " # " shell prompt):
{
  "\n": "\n # ",
  "echo hello_world\n": "hello_world\n # ",
  "cat some_file\n":
    "cat some_file\n"
    "file line 1\n"
    "file line 2\n"
    "\n # ",
}

If you need to simulate several sequential responses to a command (for example,
during a reboot or waiting for wifi to come online), you can use an iterator of
responses. fake_responder will cycle through each of them.

{
  "reboot\n": iter([
      "System is shutting down\n",
      "Starting bootup\n",
      "Bootup complete\n",
      " # ",
  ]),
}

To change fake_responder's behavior between tests, modify .behavior_dict and
.response attributes. For example, to imitate a non-responsive device for a
single test:
  self.fake_responder.response = ""
  del self.fake_responder.behavior_dict["some-command\n"]

Example of use: see unit_tests/test_raspbian_device.py.
"""
from collections.abc import Iterator
import copy
import difflib
import logging
import re
from typing import Mapping, Union

from gazoo_device import config
from gazoo_device import errors
from gazoo_device.switchboard import expect_response
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard import switchboard
import immutabledict

_immutabledict = immutabledict.immutabledict
_ResponseType = Union[str, Iterator[str]]
_ExpectResponse = expect_response.ExpectResponse
logger = logging.getLogger(__name__)
stderr_handler = logging.StreamHandler()
logger.addHandler(stderr_handler)
logger.setLevel(logging.INFO)


class FakeResponder:
  """Mocks device communication at Switchboard level."""

  def __init__(
      self,
      behavior_dict: Mapping[str, _ResponseType] = _immutabledict(),
      response: str = "",
      debug: bool = False) -> None:
    """Initializes a FakeResponder instance.

    Args:
      behavior_dict: Behavior dictionary to emulate device communication. Keys
        are commands sent by GDM, formatted precisely as GDM would (e.g.
        including trailing and/or leading newlines). Values are responses to
        return, either a string for a constant response, or a string iterator
        for a variable response. Only immutable dicts are accepted to prevent
        inadvertent modifications to the constant storing the behavior
        dictionary.
      response: Default log response to return if there's no matching entry in
        the behavior_dict, or for expect() calls waiting for a log or response
        line without a command. This can be a string for a constant response, or
        a string iterator for a variable response.
      debug: Whether to enable debug messages from fake responder.
    """
    # Deepcopy to avoid unintentional modifications to the original
    # behavior_dict (if a mutable mapping is used). Convert to a mutable dict to
    # allow test cases to modify the value stored in FakeResponder.
    self.behavior_dict = dict(copy.deepcopy(behavior_dict))
    self.response = response
    self.debug = debug
    # When there's no matching behavior, FakeResponder returns a timeout and
    # includes a debugging help message in its response. This may not work for
    # tests sensitive to the contents of the response on timeouts.
    # disable_response_timeout_help_message can be used to disable this.
    self.disable_response_timeout_help_message = False

  def debug_print(self, msg):
    if self.debug:
      logger.info("FAKE_IO: %s", msg)

  def click_and_expect(self,
                       button,
                       pattern_list,
                       duration=0.5,
                       timeout=30.0,
                       searchwindowsize=config.SEARCHWINDOWSIZE,
                       expect_type="log",
                       port=0,
                       mode="any"):
    """Mock implementation of Switchboard.click_and_expect."""
    del duration, timeout, searchwindowsize, expect_type, port  # Unused.
    self.debug_print("Click and expect {}".format(button))
    output = self._command_and_expect_parser(button, pattern_list, mode)
    return output

  def release_and_expect(self,
                         button,
                         pattern_list,
                         timeout=30.0,
                         searchwindowsize=config.SEARCHWINDOWSIZE,
                         expect_type="log",
                         port=0,
                         mode="any"):
    """Mock implementation of Switchboard.release_and_expect."""
    del timeout, searchwindowsize, expect_type, port  # Unused.
    self.debug_print("Release and expect {}".format(button))
    output = self._command_and_expect_parser(button, pattern_list, mode)

    return output

  def send_and_expect(self,
                      command,
                      pattern_list,
                      timeout=30.0,
                      searchwindowsize=config.SEARCHWINDOWSIZE,
                      expect_type=line_identifier.LINE_TYPE_RESPONSE,
                      mode=switchboard.MODE_TYPE_ANY,
                      port=0,
                      slow=False,
                      add_newline=True,
                      newline="\n",
                      command_tries=1,
                      raise_for_timeout=False):
    """Mock implementation of Switchboard.send_and_expect."""
    # Delete unused arguments.
    del timeout, searchwindowsize, expect_type, port, slow, command_tries
    cmd = switchboard._ensure_has_newline(  # pylint: disable=protected-access
        command, add_newline=add_newline, newline=newline)
    self.debug_print("Send and expect on cmd {}:".format(repr(cmd)))
    output = self._command_and_expect_parser(cmd, pattern_list, mode)
    if output and output.timedout and raise_for_timeout:
      raise errors.DeviceError(
          "send_and_expect timed out\n"
          "command: {}\nRemaining patterns: {}\nOutput: {}"
          .format(command, "\n".join(output.remaining), output.before))
    return output

  def expect(self,
             pattern_list,
             timeout=30.0,
             searchwindowsize=config.SEARCHWINDOWSIZE,
             expect_type=line_identifier.LINE_TYPE_ALL,
             mode=switchboard.MODE_TYPE_ANY,
             raise_for_timeout: bool = False):
    """Mock implementation of Switchboard.expect."""
    del searchwindowsize, expect_type  # Unused.
    response = self.response
    self.debug_print("expect")
    if isinstance(pattern_list, str):
      raise RuntimeError(
          "FAKE_IO pattern_list {!r} is a string instead of list".format(
              pattern_list))
    if isinstance(response, str):
      response_str = response
    else:
      try:  # handle multiple sequential responses with iterators
        response_str = next(response)
      except TypeError:
        raise TypeError(
            "FAKE_IO Expecting response to be a string or an iterator. "
            f"Instead it is: {type(response)} ({response!r})")
    self.debug_print("\tMode: {}, Pattern_list: {}".format(mode, pattern_list))
    self.debug_print("\tFake Response: {!r}".format(response_str))

    output = self._expect_parser(pattern_list, response_str, mode)
    if output.timedout and raise_for_timeout:
      raise errors.DeviceError(
          "{} expect timed out after waiting {}s for {!r} remaining patterns"
          .format("fakedevice-1234", timeout, ", ".join(output.remaining)))
    self.debug_print("\tExpect timedout: {}\t".format(output.timedout))
    return output

  def press_and_expect(self,
                       button,
                       pattern_list,
                       wait=0.0,
                       timeout=30.0,
                       searchwindowsize=config.SEARCHWINDOWSIZE,
                       expect_type="log",
                       port=0,
                       mode="any"):
    """Mock implementation of Switchboard.press_and_expect."""
    del wait, timeout, searchwindowsize, expect_type, port  # Unused.
    self.debug_print("press and expect {}:".format(repr(button)))
    output = self._command_and_expect_parser(button, pattern_list, mode)
    return output

  def do_and_expect(self,
                    func,
                    func_args,
                    func_kwargs,
                    pattern_list,
                    timeout=30.0,
                    searchwindowsize=config.SEARCHWINDOWSIZE,
                    expect_type=line_identifier.LINE_TYPE_ALL,
                    mode=switchboard.MODE_TYPE_ANY,
                    raise_for_timeout=False,
                    include_func_response=False):
    """Mock implementation of Switchboard.do_and_expect."""
    del timeout, searchwindowsize, expect_type  # Unused.
    func_name = getattr(func, "__name__", repr(func))
    self.debug_print("Do and expect {}".format(func_name))

    if not callable(func):
      raise errors.DeviceError(
          "do_and_expect failed. Function: {} is not callable.".format(
              func_name))

    func_ret = func(*func_args, **func_kwargs)
    expect_ret = self._command_and_expect_parser(
        func_name, pattern_list, mode)

    if expect_ret and expect_ret.timedout and raise_for_timeout:
      raise errors.DeviceError(
          "do_and_expect timed out\n"
          "Function: {}\nRemaining patterns: {}\nOutput: {}"
          .format(func_name,
                  "\n".join(expect_ret.remaining),
                  expect_ret.before))

    if include_func_response:
      return expect_ret, func_ret
    else:
      return expect_ret

  def _command_and_expect_parser(self, cmd, pattern_list, mode):
    """Returns responses for <something>_and_expect() mock calls.

    Args:
        cmd (str):
        pattern_list (list): list of pattern_list typically passed in via
          expect
        mode (str): "any", "all", "sequential".

    Raises:
      RuntimeError if response not iter or string.
    Note:
        uses pre-loaded self.behavior_dict or self.response to find
        responses.
    """

    if cmd in self.behavior_dict:
      response = self.behavior_dict[cmd]
    else:
      self.debug_print("\tNo entry in behavior dict for {!r}".format(cmd))
      response = self.response

    if isinstance(response, str):
      response_str = response
    else:
      try:  # handle multiple sequential responses with iterators
        response_str = next(response)
      except TypeError:
        raise TypeError(
            "FAKE_IO Expecting response to be a string or an iterator. "
            f"Instead it is: {type(response)} ({response!r})")
    if (cmd not in self.behavior_dict and
        not self.disable_response_timeout_help_message):
      response_str += (
          "------- https://github.com/google/gazoo-device: returning the default response. "
          f"No command {cmd!r} in the behavior dictionary. "
          f"Close matches: {difflib.get_close_matches(cmd, self.behavior_dict)}"
      )
    self.debug_print("\tMode: {}, Pattern_list: {}".format(mode, pattern_list))
    self.debug_print(
        "\tFake response from behavior dict: {!r}".format(response_str))

    output = self._expect_parser(
        pattern_list=pattern_list, response=response_str, mode=mode, cmd=cmd)

    self.debug_print("\tExpect timedout: {}\t".format(output.timedout))
    return output

  def _expect_parser(self, pattern_list, response, mode, cmd=""):
    """Mock implementation of Switchboard.expect()."""
    try:
      matches = [
          re.search(pattern, response, re.MULTILINE | re.DOTALL)
          for pattern in pattern_list
      ]
    except Exception as err:
      raise RuntimeError(
          "FAKE_RESPONDER unable to parse. "
          "Command: {}, Pattern: {!r}, response: {!r}, error: {!r}"
          .format(cmd, pattern_list, response, err))
    starts = [
        int(match.start()) if match else len(response) for match in matches
    ]

    if mode == "any":
      if any(match for match in matches):  # match is None if not matched
        index = starts.index(min(starts))  # find first match
        return _ExpectResponse(
            index=index,
            before=response[:min(starts)],
            after=response[min(starts):],
            match=matches[index],
            time_elapsed=0.1)

      else:  # return timedout
        return _ExpectResponse(None, response, "", None, 0.1, timedout=True)

    if mode == "all":
      remaining = [
          pattern_list[i]
          for i in range(len(pattern_list))
          if matches[i] is None
      ]
      match_list = [match for match in matches if match]
      if remaining:
        return _ExpectResponse(
            index=None,
            before="",
            after="",
            match=None,
            time_elapsed=.1,
            timedout=True,
            match_list=match_list,
            remaining=remaining)

      else:
        last_i = max(starts)
        return _ExpectResponse(
            index=None,
            before=response[:last_i],
            after=response[last_i:],
            match=None,
            time_elapsed=.1,
            match_list=matches,
            remaining=[])

    elif mode == "sequential":

      for i, response_i in enumerate(starts):
        if not self._sequential_match(i, response_i, starts, len(response)):
          remaining_list = pattern_list[i:]
          match_list = matches[:i]
          index = starts[i - 1]
          return _ExpectResponse(
              index=i - 1,
              before=response[:index],
              after=response[index:],
              match=None,
              time_elapsed=.1,
              timedout=True,
              match_list=match_list,
              remaining=remaining_list)
      index = starts[-1]
      return _ExpectResponse(
          index=index,
          before=response[:index],
          after=response[index:],
          match=matches[-1],
          time_elapsed=.1,
          match_list=matches,
          remaining=[])
    else:
      raise Exception("unrecognized mode")

  def _sequential_match(self, pattern_i, response_i, starts_list,
                        not_found_int):
    """Returns True if sequential expect should match."""
    if response_i == not_found_int:  # match not found
      return False
    if pattern_i == 0:  # first of the pattern_list
      return True
    if starts_list[pattern_i - 1] == starts_list[pattern_i]:
      # different patterns but same match index
      return True

    # Check that this match is found after the previous
    return starts_list[pattern_i - 1] < starts_list[pattern_i]
