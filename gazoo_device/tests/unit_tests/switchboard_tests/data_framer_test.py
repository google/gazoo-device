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

"""Tests the data_framer.py module."""
import types

from gazoo_device.switchboard import data_framer
from gazoo_device.tests.unit_tests.utils import unit_test_case


class DataFramerTests(unit_test_case.UnitTestCase):

  def test_000_data_framer_construct_destruct(self):
    """Test constructing and destructing of DataFramer classes."""
    uut2 = data_framer.InterwovenLogFramer("")
    del uut2

    uut3 = data_framer.NewlineFramer()
    del uut3

  def test_010_data_framer_split_newlines_only_raises_errors(self):
    """Test _split_newlines_only raises errors on bad arguments."""
    # begin != int
    gen = data_framer.split_newlines_only("", begin=1.0)
    with self.assertRaisesRegex(ValueError,
                                r"Expected begin to be an integer found"):
      next(gen)

    # begin < 0 test
    gen = data_framer.split_newlines_only("", begin=-1)
    with self.assertRaisesRegex(ValueError,
                                r"Expected begin value to be >= 0 and <="):
      next(gen)

    # begin >= len(string) test
    gen = data_framer.split_newlines_only("", begin=1)
    with self.assertRaisesRegex(ValueError,
                                r"Expected begin value to be >= 0 and <="):
      next(gen)

    # end != int
    gen = data_framer.split_newlines_only("", end=1.0)
    with self.assertRaisesRegex(ValueError,
                                r"Expected end to be an integer found"):
      next(gen)

    # end < 0 test
    gen = data_framer.split_newlines_only("", end=-1)
    with self.assertRaisesRegex(ValueError,
                                r"Expected end value to be >= 0 and <="):
      next(gen)

    # end >= len(string) test
    gen = data_framer.split_newlines_only("", end=1)
    with self.assertRaisesRegex(ValueError,
                                r"Expected end value to be >= 0 and <="):
      next(gen)

    # begin > end test
    gen = data_framer.split_newlines_only("1", begin=1, end=0)
    with self.assertRaisesRegex(ValueError, r"Expected end value"):
      next(gen)

  def test_011_data_framer_split_newlines_only_yields_substrings(self):
    """Test _split_newlines_only yields substrings."""
    # empty string test
    empty_string = ""
    gen = data_framer.split_newlines_only(empty_string)
    self._verify_split(gen, [empty_string])

    # no newline returns full string
    no_newline_string = "no newlines at all\r"
    gen = data_framer.split_newlines_only(no_newline_string)
    self._verify_split(gen, [no_newline_string])

    # one newline with multiple line returns returns one substring
    one_newline_string = "\rone newline only\r\r\n"
    gen = data_framer.split_newlines_only(one_newline_string)
    self._verify_split(gen, [one_newline_string])

    # two substrings returns two substrings
    two_substrings = one_newline_string + no_newline_string
    gen = data_framer.split_newlines_only(two_substrings)
    self._verify_split(gen, [one_newline_string, no_newline_string])

    # no newline with begin == len(string) still returns full string
    no_newline_string = "no newlines at all\r"
    gen = data_framer.split_newlines_only(
        no_newline_string, begin=len(no_newline_string))
    self._verify_split(gen, [no_newline_string])

    # no newline with end == 1 still returns full string
    no_newline_string = "no newlines at all\r"
    gen = data_framer.split_newlines_only(no_newline_string, end=1)
    self._verify_split(gen, [no_newline_string])

    # one newline with multiple line returns with keepends=False
    no_newline_at_end = one_newline_string[:-1]
    gen = data_framer.split_newlines_only(one_newline_string, keepends=False)
    self._verify_split(gen, [no_newline_at_end])

    # one newline with multiple line returns with keepends=False
    # and cleanends=True
    no_line_returns_or_newline_at_end = one_newline_string.rstrip()
    gen = data_framer.split_newlines_only(
        one_newline_string, keepends=False, cleanends=True)
    self._verify_split(gen, [no_line_returns_or_newline_at_end])

    # one newline with multiple line returns with keepends=True
    # and cleanends=True
    new_line_only_at_end = one_newline_string.rstrip() + "\n"
    gen = data_framer.split_newlines_only(
        one_newline_string, keepends=True, cleanends=True)
    self._verify_split(gen, [new_line_only_at_end])

    # line return and line feed only string test with keepends=False
    # and cleanends=True
    line_return_string = "\r\n"
    gen = data_framer.split_newlines_only(
        line_return_string, keepends=False, cleanends=True)
    self._verify_split(gen, [line_return_string.rstrip()])

    # line return and line feed only string test with keepends=True
    # and cleanends=True
    line_return_string = "\r\n"
    gen = data_framer.split_newlines_only(
        line_return_string, keepends=True, cleanends=True)
    self._verify_split(gen, [line_return_string.rstrip() + "\n"])

    # two line returns and a line feed string with begin = second line feed
    partial_string = "hi\r\r\r\r\r\r"
    double_line_return_string = partial_string + "\r\n"
    gen = data_framer.split_newlines_only(
        double_line_return_string, begin=len(partial_string), cleanends=True)
    self._verify_split(gen, [double_line_return_string.rstrip() + "\n"])

  def test_030_log_framer_yields_partial_line(self):
    """Test LogFramer class yields partial line without newline."""
    log_line = "my custom log line"
    log_line_pattern = "({}\n)".format(log_line)
    uut = data_framer.InterwovenLogFramer(log_line_pattern)

    lines = uut.get_lines(log_line)
    line = next(lines)
    self.assertEqual(log_line, line,
                     "Expected line {!r} found {!r}".format(log_line, line))
    with self.assertRaises(StopIteration):
      next(lines)

  def test_031_log_framer_yields_two_lines_on_split_match(self):
    """Test LogFramer yields two lines when log line splits response line."""
    response_line = "response start"
    log_line = "my custom log line\n"
    log_line_pattern = "({})".format(log_line)
    uut = data_framer.InterwovenLogFramer(log_line_pattern)

    raw_data = "{}{}".format(response_line, log_line)
    lines = uut.get_lines(raw_data)
    line1 = next(lines)
    line2 = next(lines)
    self.assertEqual(log_line, line1,
                     "Expected line {!r} found {!r}".format(log_line, line1))
    self.assertEqual(
        response_line, line2,
        "Expected line {!r} found {!r}".format(response_line, line2))
    with self.assertRaises(StopIteration):
      next(lines)

  def test_032_log_framer_yields_one_line_on_full_match(self):
    """Test LogFramer class yields one line for full matching log line."""
    log_line = "my custom log line\n"
    log_line_pattern = "({})".format(log_line)
    uut = data_framer.InterwovenLogFramer(log_line_pattern)

    lines = uut.get_lines(log_line)
    line = next(lines)
    self.assertEqual(log_line, line,
                     "Expected line {!r} found {!r}".format(log_line, line))
    with self.assertRaises(StopIteration):
      next(lines)

  def test_033_log_framer_yields_recombined_lines(self):
    """Test LogFramer class yields recombined line with newline added."""
    response_start = "response start"
    response_end = " end\n"
    response_line = "{}{}".format(response_start, response_end)
    log_line = "my custom log line"
    log_line_pattern = "({})".format(log_line)
    uut = data_framer.InterwovenLogFramer(log_line_pattern, add_newline=True)

    raw_data = "{}{}{}".format(response_start, log_line, response_end)
    lines = uut.get_lines(raw_data)
    line1 = next(lines)
    line2 = next(lines)
    self.assertEqual(log_line + "\n", line1,
                     "Expected line {!r} found {!r}".format(log_line, line1))
    self.assertEqual(
        response_line, line2,
        "Expected line {!r} found {!r}".format(response_line, line2))
    with self.assertRaises(StopIteration):
      next(lines)

  def test_034_log_framer_yields_response_line_only(self):
    """Test LogFramer class yields non-matching response line as is."""
    log_line_pattern = r"(my custom log line\n)"
    uut = data_framer.InterwovenLogFramer(log_line_pattern)

    response_line = "some non-matching response line\n"
    lines = uut.get_lines(response_line)
    line = next(lines)
    self.assertEqual(
        response_line, line,
        "Expected line {!r} found {!r}".format(response_line, line))
    with self.assertRaises(StopIteration):
      next(lines)

  def test_040_newline_framer_returns_generator(self):
    """Test LogResponseIdentifier class accepts all lines."""
    uut = data_framer.NewlineFramer()

    lines = uut.get_lines("", begin=0)
    self.assertIsInstance(
        lines, types.GeneratorType,
        "Expected GeneratorType found {}".format(type(lines)))

  def _verify_split(self, generator, expected_list):
    for expected in expected_list:
      substring = next(generator)
      self.assertEqual(
          expected, substring,
          "Expected {!r} to match substring {!r}".format(expected, substring))
    with self.assertRaises(StopIteration):
      next(generator)


if __name__ == "__main__":
  unit_test_case.main()
