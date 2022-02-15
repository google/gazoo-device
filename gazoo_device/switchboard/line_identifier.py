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

"""Used to identify device output lines as Log, Response, or Unknown.

AllUnknownIdentifier (default) which classifies all lines
from all ports as unknown and accepts them for every line_type provided.

AllLogIdentifier classifies all lines from all ports as log lines and only
accepts them for "all" or "log" line_type values.

AllResponseIdentifier classifies all lines from all ports as response lines
and only accepts them for "all" or "response" line_type values.

PortLogIdentifier classifies lines from a particular port as log lines.
All others are responses.

RegexLogIdentifier classifies lines that match a regex as log lines.
All others are unknown.

RegexResponseIdentifier classifies lines that match a regex as response lines.
All others are unknown.
"""
import abc
import re
from typing import Optional

from typing_extensions import Literal

LINE_TYPE_ALL = "all"
LINE_TYPE_LOG = "log"
LINE_TYPE_RESPONSE = "response"
LINE_TYPE = Literal[LINE_TYPE_ALL, LINE_TYPE_LOG, LINE_TYPE_RESPONSE]


class LineIdentifier(abc.ABC):
  """Base class used to identify device output lines as Log, Response, or Unknown."""

  @abc.abstractmethod
  def accept(self, port, line, line_type):
    """Returns True if line is identified to be part of line_type requested.

    Args:
        port (int): which transport line came from.
        line (str): device output
        line_type (str): line type requested. Options ("all", "log",
          "response")

    Returns:
        bool: whether or not line matches request type.
    """


class AllLogIdentifier(LineIdentifier):
  """Identifies all output as logs."""

  def accept(self, port, line, line_type):
    """Identifies all lines from all ports as log lines."""

    return line_type in [LINE_TYPE_ALL, LINE_TYPE_LOG]


class AllResponseIdentifier(LineIdentifier):
  """Identifies all output as responses."""

  def accept(self, port, line, line_type):
    return line_type in [LINE_TYPE_ALL, LINE_TYPE_RESPONSE]


class AllUnknownIdentifier(LineIdentifier):
  """Identifies all output as unknown."""

  def accept(self, port, line, line_type):
    return True


class PortLogIdentifier(LineIdentifier):
  """Identifies all output from certain ports as logs.

  Note:
      Output from all other ports is considered a reponse.
  """

  def __init__(self, log_ports=None):
    """Identifies lines from log ports as logs.

    Args:
        log_ports (list): ports to identify as logging ports.
    """
    if not log_ports:
      log_ports = [1]
    self.log_ports = log_ports

  def accept(self, port, line, line_type):
    if port in self.log_ports:
      return line_type in [LINE_TYPE_ALL, LINE_TYPE_LOG]
    else:
      return line_type in [LINE_TYPE_ALL, LINE_TYPE_RESPONSE]


class RegexIdentifier(LineIdentifier):
  """Identifies output based on a log or a response regex (or both)."""

  def __init__(self, log_pattern: Optional[str] = None,
               response_pattern: Optional[str] = None) -> None:
    """Initializes a RegexIdentifier.

    Args:
      log_pattern: Regular expression which matches logs.
      response_pattern: Regular expression which matches command responses.
    """
    if log_pattern is None and response_pattern is None:
      raise ValueError("log_pattern or response_pattern must be specified.")
    if log_pattern is not None:
      self._log_pattern = re.compile(log_pattern)
    else:
      self._log_pattern = None
    if response_pattern is not None:
      self._response_pattern = re.compile(response_pattern)
    else:
      self._response_pattern = None

  def accept(self, port: int, line: str, line_type: LINE_TYPE) -> bool:
    """Returns whether the given line should be accepted."""
    if line_type == LINE_TYPE_ALL:
      return True

    if line_type == LINE_TYPE_LOG:
      if self._log_pattern is not None:
        return bool(re.search(self._log_pattern, line))
      else:
        return not bool(re.search(self._response_pattern, line))

    if line_type == LINE_TYPE_RESPONSE:
      if self._response_pattern is not None:
        return bool(re.search(self._response_pattern, line))
      else:
        return not bool(re.search(self._log_pattern, line))

    return True


class RegexLogIdentifier(RegexIdentifier):
  """Identifies all output as logs if regex matches else its Unknown."""

  def __init__(self, log_pattern: str) -> None:
    super().__init__(log_pattern=log_pattern)


class RegexResponseIdentifier(RegexIdentifier):
  """Identifies all output as response if regex matches else its Unknown."""

  def __init__(self, response_pattern: str) -> None:
    super().__init__(response_pattern=response_pattern)


class MultiportIdentifier(LineIdentifier):
  """Generic line identifier for several ports.

  Each port uses a different identifier.
  MultiportIdentifier delegates to the appropriate identifier.
  """

  def __init__(self, identifiers):
    """Initializes the MultiportIdentifier.

    Args:
        identifiers (list): list of LineIdentifier objects.
    """
    self._identifiers = identifiers

  def accept(self, port, line, line_type):
    """Returns whether the given line should be accepted (True) or discarded (False)."""
    if port >= len(self._identifiers):
      return True
    return self._identifiers[port].accept(
        port=port, line=line, line_type=line_type)
