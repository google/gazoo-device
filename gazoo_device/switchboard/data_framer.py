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

"""DataFramer based classes transforms incoming raw data into partial and complete lines.

The NewlineFramer (default) splits incoming raw data into partial and complete lines
at newline character boundaries.

The InterwovenLogFramer finds and extracts log lines interwoven with responses
using the log line regex provided.

Notes:
A complete line returned by all DataFramer based classes
should include the trailing newline
character as is.

Partial lines are typically those raw bytes that remain which
don't have a trailing newline character.
"""
from __future__ import absolute_import
import re
import six
from six.moves import range
import abc


class DataFramer(six.with_metaclass(abc.ABCMeta), object):
    """Abstract class for transforming raw device input into discreet lines."""

    @abc.abstractmethod
    def get_lines(self, raw_data, begin=0, end=None):
        """Yields each line from the raw_data provided from begin to end.

        Args:
            raw_data (str): to split into framed lines
            begin (int): index to the first character to start looking for newlines
            end (int): index to the last character to look for newline characters

        Yields:
            str: A partial or complete framed line found in the raw_data provided.

        Note:
            The begin argument allows for a slight optimization by skipping
            past previous partial line in search of the next newline character.
        """


def _validate_end_and_begin_are_valid(begin, end, string_len):
    """Validate begin and end are in the right range and are integers.

    Args:
        begin (int): character position to start searching for newlines from.
        end (int): end character position to stop searching for newlines from.
        string_len (int): length of the string to search for newlines.

    Raises:
       ValueError: if begin or end are not valid intput.
    """
    if not isinstance(begin, int):
        raise ValueError("Expected begin to be an integer found {}".
                         format(type(begin)))
    elif begin < 0 or begin > string_len:
        raise ValueError("Expected begin value to be >= 0 and <= {}, found {}".
                         format(string_len, begin))
    elif end is not None:
        if not isinstance(end, int):
            raise ValueError("Expected end to be an integer found {}".
                             format(type(end)))
        elif end < 0 or end > string_len:
            raise ValueError("Expected end value to be >= 0 and <= {}, found {}".
                             format(string_len, end))
        elif begin > end:
            raise ValueError("Expected end value {} to be <= begin value {}".
                             format(end, begin))


def split_newlines_only(string, begin=0, end=None, keepends=True, cleanends=False):
    """Generates substrings of string up to and including newline characters only.

    Args:
        string (str): to extract substrings from.
        begin (int): character to start searching for newlines from, not the
                     first character of the first substring returned.
        end (int): end character to stop searching for newlines from
        keepends (bool): flag indicating newline character should be returned
                         as part of substring returned.
        cleanends (bool): flag indicating trailing line return and line feeds
                          should be stripped off and replaced with a line feed.

    Raises:
        ValueError: if begin or end < 0 or > than length of the string

    Yields:
        str: Generates substrings of string from 0 to len(string) for each
             newline character found and optionally including the newline
             character.

    Note:
        The begin argument allows for skipping characters that you know won't
        contain newline characters. The first substring returned will always be
        from the first character of the string to the first newline character
        found or the end of the string if no newline characters exist.
        If the end argument is None then the length of the string will be used
        instead. If the end argument is specified and is less than the length
        of the string then this function will yield all characters from end to
        the length of the string as the last substring.
    """
    string_len = len(string)
    _validate_end_and_begin_are_valid(begin, end, string_len)
    if end is None:
        end = string_len
    start_index = 0
    if cleanends:
        pre_line_return = begin
        # If begin > 0 might need to find pre_line_return spot in string
        for i in range(begin, 0, -1):
            if string[i] != "\r" and string[i] != "\n":
                pre_line_return = i + 1
                break
    end_offset = 1 if keepends else 0
    for i in range(begin, end):
        if cleanends and string[i] != "\r" and string[i] != "\n":
            pre_line_return = i + 1
        if string[i] == "\n":
            if cleanends:
                yield string[start_index:pre_line_return] + string[i:i + end_offset]
            else:
                yield string[start_index:i + end_offset]
            start_index = i + 1
            if start_index == end:
                break
    else:
        yield string[start_index:]


class InterwovenLogFramer(DataFramer):
    """Finds and extract out of order logs that are interwoven with responses."""

    def __init__(self, log_line_pattern, add_newline=False, keepends=True, cleanends=True):
        """Initializes LogFramer with the log line pattern provided.

        Args:
            log_line_pattern (str): to use to match and extract log lines from
                                    response lines.
            add_newline (bool): add a newline character to the extracted log line
            keepends (bool): flag indicating that trailing LF should be returned
            cleanends (bool): flag indicating that trailing CR and LF should be
                              replaced with LF only.

        Note:
            The log_line_pattern should contain a single regular expression
            group that contains the complete log line, including the newline
            character (or use add_newline to add one), to be extracted from the
            response line.

            The cleanends flag will strip off all CR and LF characters at the
            end of the line. If keepends is True the LF character will be
            returned. This is done before the log_line_pattern logic is
            performed so that add_newline only adds a LF character to the
            log_line string matched if enabled.
        """
        self.add_newline = add_newline
        self.keepends = keepends
        self.cleanends = cleanends
        self.log_line_re = re.compile(log_line_pattern)

    def get_lines(self, raw_data, begin=0, end=None):
        """Yields each deframed line from the raw_data provided from begin to end.

        Args:
            raw_data (str): to split into framed lines
            begin (int): index to the first character to start looking for newlines
            end (int): index to the last character to look for newline characters

        Yields:
            str: A partial or complete framed line found in the raw_data provided.

        Note:
            The begin argument allows for a slight optimization by skipping
            past previous partial line in search of the next newline character.
        """

        for raw_line in split_newlines_only(raw_data,
                                            begin=begin,
                                            end=end,
                                            keepends=self.keepends,
                                            cleanends=self.cleanends):
            if raw_line[-1] != "\n":
                yield raw_line
            else:
                match = self.log_line_re.search(raw_line)
                if match:
                    line1 = match.group(1)
                    if self.add_newline:
                        line1 += u"\n"
                    yield line1
                    line2 = raw_line[:match.start()] + raw_line[match.end():]
                    if line2:
                        yield line2
                else:
                    yield raw_line


class NewlineFramer(DataFramer):
    """Splits lines at each newline character.

    Note:
        This is the default DataFramer.
    """

    def __init__(self, keepends=True, cleanends=True):
        """Initializes NewlineFramer with the options specified.

        Args:
            keepends (bool): flag indicating that trailing LF should be returned
            cleanends (bool): flag indicating that trailing CR and LF should be
                              replaced with LF only.

        Note:
            The cleanends flag will strip off all CR and LF characters at the
            end of the line. If keepends is True the LF character will be
            returned. No LF characters are added in the process.
        """
        self.keepends = keepends
        self.cleanends = cleanends

    def get_lines(self, raw_data, begin=0, end=None):
        """Returns each deframed line from the raw_data provided from begin to end.

        Args:
            raw_data (str): to split into framed lines
            begin (int): index to the first character to start looking for newlines
            end (int): index to the last character to look for newline characters

        Returns:
            generator: A generator function that can be used to split raw_data
                       into partial or complete framed lines on newline
                       characters.

        Note:
            The begin argument allows for a slight optimization by skipping
            past previous partial line in search of the next newline character.
        """

        return split_newlines_only(raw_data,
                                   begin=begin,
                                   end=end,
                                   keepends=self.keepends,
                                   cleanends=self.cleanends)
