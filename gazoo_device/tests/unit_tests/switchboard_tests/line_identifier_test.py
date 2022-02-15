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

"""Tests the line_identifier.py module."""
from gazoo_device.switchboard import line_identifier
from gazoo_device.tests.unit_tests.utils import unit_test_case

_LOG_LINE_REGEX = (
    r"^([A-Z|a-z]{3}\s{1,2}[0-9]{1,2}\s[0-9]{2}:[0-9]{2}:[0-9]{2}\s.*\n)")
_RESPONSE_LINE_REGEX = "root@123456789AB#"
_FAKE_LOG_LINE = (
    "Jan  1 19:45:18 some log line\n")
_FAKE_RESPONSE_AND_LOG_LINE = (
    "root@123456789AB# Jan  1 19:45:18 some log line\n")
_FAKE_RESPONSE = "root@123456789AB#\n"

TYPE_ALL = line_identifier.LINE_TYPE_ALL
TYPE_LOG = line_identifier.LINE_TYPE_LOG
TYPE_RESPONSE = line_identifier.LINE_TYPE_RESPONSE


class LineIdentifierTests(unit_test_case.UnitTestCase):
  """Unit tests for line_identifier.py."""

  def test_000_line_identifier_construct_destruct(self):
    """Test constructing and destructing of LineIdentifier classes."""
    uut2 = line_identifier.AllLogIdentifier()
    del uut2

    uut3 = line_identifier.RegexLogIdentifier("")
    del uut3

    uut4 = line_identifier.PortLogIdentifier()
    del uut4

    uut5 = line_identifier.AllResponseIdentifier()
    del uut5

    uut6 = line_identifier.AllUnknownIdentifier()
    del uut6

    uut7 = line_identifier.MultiportIdentifier([
        line_identifier.AllResponseIdentifier(),
        line_identifier.AllUnknownIdentifier()
    ])
    del uut7

  def test_001_all_log_identifier(self):
    """Test LogIdentifier class."""
    uut = line_identifier.AllLogIdentifier()
    reject_inputs = [[0, "", TYPE_RESPONSE], [1, "", TYPE_RESPONSE]]
    accept_inputs = [[0, "", TYPE_LOG], [1, "", TYPE_LOG], [0, "", TYPE_ALL],
                     [1, "", TYPE_ALL]]
    self._test_state_machine(uut, "AllLogIdentifier", reject_inputs,
                             accept_inputs)

  def test_002_all_response_identifier(self):
    uut = line_identifier.AllResponseIdentifier()
    reject_inputs = [[0, "", TYPE_LOG], [1, "", TYPE_LOG]]
    accept_inputs = [[0, "", TYPE_RESPONSE], [1, "", TYPE_RESPONSE],
                     [0, "", TYPE_ALL], [1, "", TYPE_ALL]]
    self._test_state_machine(uut, "AllResponseIdentifier", reject_inputs,
                             accept_inputs)

  def test_003_all_unknown_identifier(self):
    uut = line_identifier.AllUnknownIdentifier()
    reject_inputs = []
    accept_inputs = [[0, "", TYPE_LOG], [1, "", TYPE_LOG],
                     [0, "", TYPE_RESPONSE], [1, "", TYPE_RESPONSE],
                     [0, "", TYPE_ALL], [1, "", TYPE_ALL]]
    self._test_state_machine(uut, "AllUnknownIdentifier", reject_inputs,
                             accept_inputs)

  def test_004_port_log_identifier(self):
    """Test LogResponseIdentifier class accepts all lines."""
    log_ports = [1]
    uut = line_identifier.PortLogIdentifier(log_ports)
    reject_inputs = [[0, "", TYPE_LOG], [1, "", TYPE_RESPONSE]]
    accept_inputs = [[1, "", TYPE_LOG], [0, "", TYPE_RESPONSE],
                     [1, "", TYPE_ALL], [0, "", TYPE_ALL]]

    self._test_state_machine(uut, "PortLogIdentifier", reject_inputs,
                             accept_inputs)

  def test_005_regex_log_identifier(self):
    """Tests RegexLogIdentifier."""
    uut = line_identifier.RegexLogIdentifier(_LOG_LINE_REGEX)

    reject_inputs = [[0, _FAKE_LOG_LINE, TYPE_RESPONSE],
                     [0, _FAKE_RESPONSE, TYPE_LOG],
                     [0, _FAKE_RESPONSE_AND_LOG_LINE, TYPE_LOG]]
    accept_inputs = [[0, _FAKE_LOG_LINE, TYPE_LOG],
                     [0, _FAKE_LOG_LINE, TYPE_ALL],
                     [0, _FAKE_RESPONSE, TYPE_ALL],
                     [0, _FAKE_RESPONSE, TYPE_RESPONSE]]

    self._test_state_machine(uut, "RegexLogIdentifier",
                             reject_inputs, accept_inputs)

  def test_006_regex_response_identifier(self):
    """Tests RegexResponseIdentifier."""
    uut = line_identifier.RegexResponseIdentifier(_RESPONSE_LINE_REGEX)

    reject_inputs = [[0, _FAKE_LOG_LINE, TYPE_RESPONSE],
                     [0, _FAKE_RESPONSE, TYPE_LOG]]
    accept_inputs = [[0, _FAKE_LOG_LINE, TYPE_LOG],
                     [0, _FAKE_LOG_LINE, TYPE_ALL],
                     [0, _FAKE_RESPONSE, TYPE_ALL],
                     [0, _FAKE_RESPONSE, TYPE_RESPONSE]]

    self._test_state_machine(uut, "RegexResponseIdentifier",
                             reject_inputs, accept_inputs)

  def test_007_regex_identifier(self):
    """Tests RegexIdentifier with both log and response patterns provided."""
    uut = line_identifier.RegexIdentifier(
        log_pattern=_LOG_LINE_REGEX, response_pattern=_RESPONSE_LINE_REGEX)

    reject_inputs = [[0, _FAKE_LOG_LINE, TYPE_RESPONSE],
                     [0, _FAKE_RESPONSE, TYPE_LOG],
                     [0, _FAKE_RESPONSE_AND_LOG_LINE, TYPE_LOG]]
    accept_inputs = [[0, _FAKE_LOG_LINE, TYPE_LOG],
                     [0, _FAKE_LOG_LINE, TYPE_ALL],
                     [0, _FAKE_RESPONSE, TYPE_ALL],
                     [0, _FAKE_RESPONSE, TYPE_RESPONSE]]

    self._test_state_machine(uut, "RegexIdentifier",
                             reject_inputs, accept_inputs)

  def test_009_multiport_identifier(self):
    """Test that MultiportIdentifier delegates to the appropriate identifier for each port."""
    uut = line_identifier.MultiportIdentifier([
        line_identifier.AllLogIdentifier(),
        line_identifier.AllResponseIdentifier()
    ])
    reject_inputs = [(0, "foo", TYPE_RESPONSE), (1, "foo", TYPE_LOG)]
    accept_inputs = [(0, "foo", TYPE_LOG), (0, "foo", TYPE_ALL),
                     (1, "foo", TYPE_RESPONSE), (1, "foo", TYPE_ALL),
                     (2, "foo", TYPE_ALL), (2, "foo", TYPE_RESPONSE),
                     (2, "foo", TYPE_LOG)]
    self._test_state_machine(uut, "MultiportIdentifier", reject_inputs,
                             accept_inputs)

  def _test_state_machine(self, log_id_instance, name, rejected_inputs,
                          accepted_inputs):
    for port, line, line_type in rejected_inputs:
      self.assertFalse(
          log_id_instance.accept(port, line, line_type),
          "{} should have {} line {} on port {} for type {}".format(
              name, "rejected", line, port, line_type))

    for port, line, line_type in accepted_inputs:
      self.assertTrue(
          log_id_instance.accept(port, line, line_type),
          "{} should have {} line {} on port {} for type {}".format(
              name, "accepted", line, port, line_type))


if __name__ == "__main__":
  unit_test_case.main()
