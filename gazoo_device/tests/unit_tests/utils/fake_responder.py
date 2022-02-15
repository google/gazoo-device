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
import logging
import re

from gazoo_device import config
from gazoo_device import errors
from gazoo_device.switchboard import expect_response
from gazoo_device.switchboard import line_identifier
from gazoo_device.switchboard import switchboard

ExpectResponse = expect_response.ExpectResponse
logger = logging.getLogger(__name__)
stderr_handler = logging.StreamHandler()
logger.addHandler(stderr_handler)
logger.setLevel(logging.INFO)


class FakeResponder:
  """Mocks device communication at Switchboard level."""

  def __init__(self, behavior_dict=None, response="", debug=False):
    self.behavior_dict = {} if behavior_dict is None else behavior_dict.copy()
    self.response = response
    self.debug = debug

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
             mode=switchboard.MODE_TYPE_ANY):
    """Mock implementation of Switchboard.expect."""
    del timeout, searchwindowsize, expect_type  # Unused.
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
        return ExpectResponse(
            index=index,
            before=response[:min(starts)],
            after=response[min(starts):],
            match=matches[index],
            time_elapsed=0.1)

      else:  # return timedout
        return ExpectResponse(None, response, "", None, 0.1, timedout=True)

    if mode == "all":
      remaining = [
          pattern_list[i]
          for i in range(len(pattern_list))
          if matches[i] is None
      ]
      match_list = [match for match in matches if match]
      if remaining:
        return ExpectResponse(
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
        return ExpectResponse(
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
          return ExpectResponse(
              index=i - 1,
              before=response[:index],
              after=response[index:],
              match=None,
              time_elapsed=.1,
              timedout=True,
              match_list=match_list,
              remaining=remaining_list)
      index = starts[-1]
      return ExpectResponse(
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
