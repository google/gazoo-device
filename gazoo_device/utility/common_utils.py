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

"""Common reusable utility functions."""
import re
import weakref


class MethodWeakRef(object):
  """Allows creating weak references to instance methods.

  Note:
      using weakref.ref() on an instance method directly returns a dead
      reference. See https://stackoverflow.com/questions/599430.
  """

  def __init__(self, instance_method):
    """Create a weak reference to an instance (bound) method.

        Args:
            instance_method (method): instance (bound) method.
    """
    self._func = instance_method.__func__
    self._instance_weakref = weakref.ref(instance_method.__self__)

  def __call__(self, *args, **kwargs):
    """Calls the instance method if the instance is still alive."""
    instance = self._instance_weakref()
    if instance is not None:
      self._func(instance, *args, **kwargs)


def generate_name(_object):
  """Generates a snake_case name (str) for the given object.

  Args:
      _object (object): any python object which has a non-empty __name__
        attribute.

  Raises:
      ValueError: _object does not have __name__ attribute, or __name__ is "".

  Returns:
      str: snake_case name for the object.
  """
  object_name = getattr(_object, "__name__", "")
  if not object_name:
    raise ValueError(
        "Object {} must have a non-empty __name__ attribute.".format(_object))

  if "_" in object_name:  # Presumably already snake_case
    return object_name.lower()
  else:  # Presumably TitleCase
    return title_to_snake_case(object_name)


def get_value_from_json(json_data, key_sequence, raise_if_absent=True):
  """Extracts a value from a JSON dictionary via provided series of keys.

  This function allows easy extraction of a value stored in a nested
  dictionary structure, with validation of the existence of the necessary
  keys at each level of nesting.

  Args:
      json_data (dict): the response object from which the value will be
        extracted.
      key_sequence (list): an ordered list of string keys representing the
        path through the dictionary necessary to reach the desired value.
                           Ex. to extract foo['baz']['a'] the call would look
                             like: get_value_from_json(foo, ['baz', 'a'])  and
                             would return 'some text' given the example data
                             above.
      raise_if_absent (bool): if False, return None if a key is not present.
        if True, raise KeyError if a key is not present.

  Returns:
      object: the requested JSON field.

  Raises:
      KeyError: If the provided response message doesn't contain the necessary
      keys/values AND if raise_if_absent is True.
  """
  current_dict = json_data
  key_text = ""
  for key in key_sequence:
    if key in current_dict:
      current_dict = current_dict[key]
    else:
      if raise_if_absent:
        raise KeyError(
            "Unable to find key '{}' in json_data{}: json_data = {}".format(
                key, key_text, json_data))
      else:
        return None
    key_text += "['{}']".format(key)
  return current_dict


def title_to_snake_case(s):
  """Convert TitleCase string to snake_case.

  Args:
      s (str): TitleCase string.

  Returns:
      str: snake_case string.

  Raises:
      ValueError: provided string contains underscores.

  Note:
      consecutive capital characters are supported ("ABc"), but underscores
      are not.
  """
  if "_" in s:
    raise ValueError(
        "{} is not a TitleCase string (found underscores).".format(s))

  word_starts = [pos for pos in range(len(s)) if _is_new_word(s, pos)
                ] + [len(s)]
  words = [
      s[word_starts[idx]:word_starts[idx + 1]].lower()
      for idx in range(len(word_starts) - 1)
  ]
  return "_".join(words)


def _is_new_word(s, pos):
  """Returns whether a new words starts at s[pos] in a TitleCase string."""
  return (pos == 0 or (s[pos].isupper() and
                       (not s[pos - 1].isupper() or
                        (pos + 1 < len(s) and not s[pos + 1].isupper()))))


def extract_posix_portable_characters(string: str) -> str:
  """Extracts posix fully portable characters from a string.

  Args:
    string: String to extract characters from.

  Returns:
    String of characters with all non-posix portable characters removed.
  """
  return re.sub(r"[^a-zA-Z0-9._\-]", "", string)
