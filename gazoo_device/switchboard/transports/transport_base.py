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

"""TransportBase is the standard GDM device transport interface.

Device transports perform device communications. Device transports are used by
TransportProcess instances.
"""
import abc
import copy
from typing import Any, Dict, List, Optional, Union

from gazoo_device.switchboard import transport_properties


class TransportBase(abc.ABC):
  """Interface for transport classes.

  Transport class instances must be serializable until they're opened.
  """

  def __init__(self,
               auto_reopen: bool = False,
               open_on_start: bool = True) -> None:
    """Initializes the transport interface.

    Args:
      auto_reopen: Flag indicating transport should be reopened if
        unexpectedly closed.
      open_on_start: Flag indicating transport should be open on
        TransportProcess start.
    """
    if not hasattr(self, "_properties"):
      self._properties = {}
    self._properties.update({
        transport_properties.AUTO_REOPEN: auto_reopen,
        transport_properties.OPEN_ON_START: open_on_start
    })

  @abc.abstractmethod
  def is_open(self) -> bool:
    """Returns True if the transport is open.

    Returns:
        bool: True if transport is open, False otherwise.
    """

  @abc.abstractmethod
  def _open(self) -> None:
    """Opens the transport using properties provided during __init__.

    Override in derived classes.
    """

  @abc.abstractmethod
  def _close(self) -> None:
    """Closes the transport. Override in derived classes."""

  @abc.abstractmethod
  def _read(self,
            size: int = 1,
            timeout: Optional[float] = None) -> Union[bytes, str]:
    """Returns bytes read up to size within the specified timeout.

    Args:
      size: Maximum number of bytes to read within timeout seconds.
      timeout: Maximum seconds to wait to read bytes or indefinitely if None.

    Returns:
      Bytes or unicode read from the transport.
      Empty string if no bytes were read or the timeout was reached.
    """

  @abc.abstractmethod
  def _write(self, data: str, timeout: Optional[float] = None) -> int:
    """Writes the data provided within timeout seconds.

    Args:
      data: Bytes to be written out within timeout seconds.
      timeout: Maximum seconds to wait to write bytes or indefinitely if None.

    Returns:
      Number of bytes written.
    """

  def __del__(self) -> None:
    """Closes the transport on garbage collection."""
    self.close()

  def get_property(self, key: str, value: Optional[Any] = None) -> Any:
    """Returns property matching key specified or value if not set.

    Args:
      key: Property to retrieve.
      value: Default value to return if the property doesn't exist.

    Returns:
      The property value for key specified or value if key doesn't exist.
    """
    return self._properties.get(key, value)

  def get_all_properties(self) -> Dict[str, Any]:
    """Returns dictionary of property key-value pairs.

    Returns:
      A deep copy of all properties.
    """
    return copy.deepcopy(self._properties)

  def get_property_list(self) -> List[str]:
    """Returns a list of property keys that exist and can be set/retrieved.

    Returns:
      Property keys that can be set or retrieved.
    """
    return list(self._properties.keys())

  def set_property(self, key: str, value: Any) -> None:
    """Sets the property specified to the value provided.

    Args:
      key: Property to set.
      value: Value to set the property to.

    Raises:
      KeyError: If property key doesn't exist.
    """
    if key not in self._properties:
      raise KeyError("Property {} doesn't exist for {}.".format(
          key, self.__class__.__name__))
    self._properties[key] = value

  def open(self):
    """Opens the transport if not open already."""
    if self.is_open():
      return None

    self._open()

  def close(self):
    """Closes the transport if it's open."""
    if not self.is_open():
      return None

    self._close()

  def read(self,
           size: int = 1,
           timeout: Optional[float] = None) -> Optional[Union[bytes, str]]:
    """Returns bytes read up to size within the specified timeout.

    Args:
      size: Maximum number of bytes to read within timeout seconds.
      timeout: Maximum seconds to wait to read bytes or indefinitely if None.

    Returns:
      Bytes or unicode read from the transport.
      Empty string if no bytes were read or the timeout was reached.
      None if the transport isn't open.
    """
    if not self.is_open():
      return None

    return self._read(size, timeout)

  def write(self, data: str, timeout: Optional[float] = None) -> Optional[int]:
    """Writes the data provided within timeout seconds if transport is open.

    Args:
      data: Bytes to be written out within timeout seconds.
      timeout: Maximum seconds to wait to write bytes or indefinitely if None.

    Returns:
      Number of bytes written if the transport is open.
      None if the transport isn't open.
    """
    if not self.is_open():
      return None

    return self._write(data, timeout)
