# Copyright 2021 Google LLC
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

is_open(): Returns true if transport is open

open(): Opens transport using properties provided during initialization

close(): Closes transport

read(size=1, timeout=None): Reads up to size bytes from device and
returns them or None if no bytes are read and timeout != None.

write(data, timeout=None): Writes bytes to device and returns the number
of bytes written or None if no bytes were written and timeout != None.

get_property(key, value=None): Returns a transport property identified by
key or if the property doesn't exist yet returns value provided.

get_all_properties(): Returns a deepcopy dictionary of all properties keys
and values currently set.

get_property_list(): Returns the list of property keys

set_property(key, value): Sets a transport property identified by key to
the value provided.
"""
import abc
import copy

import six

from gazoo_device.switchboard import transport_properties


class TransportBase(six.with_metaclass(abc.ABCMeta, object)):
  """Interface for transport classes."""

  def __init__(self, auto_reopen=False, open_on_start=True):
    """Initialize the transport interface.

    Args:
        auto_reopen (bool): flag indicating transport should be reopened if
          unexpectedly closed.
        open_on_start (bool): flag indicating transport should be open on
          TransportProcess start.
    """
    if not hasattr(self, "_properties"):
      self._properties = {}
    self._properties.update({
        transport_properties.AUTO_REOPEN: auto_reopen,
        transport_properties.OPEN_ON_START: open_on_start
    })

  @abc.abstractmethod
  def is_open(self):
    """Returns True if the transport is open.

    Returns:
        bool: True if transport is open, False otherwise.
    """

  @abc.abstractmethod
  def _open(self):
    """Open the transport.

    Override in derived classes.

    Note: use properties provided during __init__.
    """

  @abc.abstractmethod
  def _close(self):
    """Close the transport. Override in derived classes."""

  @abc.abstractmethod
  def _read(self, size=1, timeout=None):
    """Returns bytes read up to max_bytes within timeout in seconds specified.

    Args:
        size (int): maximum number of bytes to read within timeout seconds
        timeout (float): maximum seconds to wait to read bytes or
          indefinitely if timeout=None. Default: None

    Returns:
        str: bytes read from transport
             or "" if no bytes were read
             or "" if timeout was reached
    """

  @abc.abstractmethod
  def _write(self, data, timeout=None):
    """Writes the data provided within timeout seconds.

    Args:
        data (str): bytes to be written out within timeout seconds
        timeout (float): maximum seconds to wait to write bytes or
          indefinitely if timeout=None. Default: None

    Returns:
        int: number of bytes written
    """

  def __del__(self):
    """Close the transport on garbage collection."""
    self.close()

  def get_property(self, key, value=None):
    """Returns property matching key specified or value if not set.

    Args:
        key (str): of the property to attempt to retrieve
        value (object): default value to return if the property doesn't exist

    Returns:
        object: The property value for key specified or value if key doesn't
        exist.
    """
    return self._properties.get(key, value)

  def get_all_properties(self):
    """Returns dictionary of property key-value pairs.

    Returns:
        dict: a deepcopy of all properties as a key value pair
    """
    return copy.deepcopy(self._properties)

  def get_property_list(self):
    """Returns a list of property keys that exist and can be set/retrieved.

    Returns:
        list: of property keys that can be set or retrieved.
    """
    return list(self._properties.keys())

  def set_property(self, key, value):
    """Sets the property specified to the value provided.

    Args:
        key (str): of the property to set
        value (object): of the property to set

    Raises:
        KeyError: when key property doesn't exist
    """
    if key not in self._properties:
      raise KeyError("Property {} doesn't exist for {}.".format(
          key, self.__class__.__name__))
    self._properties[key] = value

  def open(self):
    """Open the transport if not open already.

    Note: use properties provided during __init__.
    """
    if self.is_open():
      return None

    self._open()

  def close(self):
    """Closes the transport if it's open."""
    if not self.is_open():
      return None

    self._close()

  def read(self, size=1, timeout=None):
    """Returns bytes read up to max_bytes within timeout in seconds specified.

    Args:
        size (int): maximum number of bytes to read within timeout seconds
        timeout (float): maximum seconds to wait to read bytes or
          indefinitely
                         if timeout=None. Default: None

    Returns:
        str: bytes read from transport
             or None if transport is NOT open
             or "" if no bytes were read
             or "" if timeout was reached

    Note:
        If transport is not opened this method will always return None
    """
    if not self.is_open():
      return None

    return self._read(size, timeout)

  def write(self, data, timeout=None):
    """Writes the data provided within timeout seconds if transport is open.

    Args:
        data (str): bytes to be written out within timeout seconds
        timeout (float): maximum seconds to wait to write bytes or
          indefinitely
                         if timeout=None. Default: None

    Returns:
        int: number of bytes written or None if no bytes were written
    """
    if not self.is_open():
      return None

    return self._write(data, timeout)
