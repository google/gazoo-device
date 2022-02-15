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

"""Utilities for adding an alias that will log a message and call a method or return a property."""
# Deprecation notice for Sphinx documentation
SPHINX_DEPRECATION_NOTICE = ('This {attr_type} has been deprecated. See '
                             '"{new_name}".')


def _get_nested_attr(obj, name):
  """Get an attribute that may or may not be nested within an object.

  This will get an attribute of obj or or an attribute that is in an object
  that is in obj.

  Args:
      obj (object): The object to check for the attribute with the given name.
      name (str): The name of the attribute to get. name can be either an
        attribute of obj or an object.attribute where object is part of obj.

  Returns:
      object: The method or property that may have been nested inside of other
      objects.
  """
  attr_list = name.split('.')
  for attr in attr_list:
    obj = getattr(obj, attr, None)
  return obj


def add_deprecated_attribute(cls, old_name, new_name, is_method):
  """Add a single deprecated property or method to a class.

  The "old_name" that is provided will be
  added to the provided class as an alias to the "new_name". Then each time
  the attribute with
  "old_name" is used it will log a deprecated message and return as if the
  "new_name" attribute
  was called.

  Note: This must be called for a class and not for an instance of a class
  since dynamically
        adding a property cannot be done for an instance of a class.

  Args:
      cls (class): The class to add the attribute to.
      old_name (str): The name of the old attribute that will be added as an
        alias for "new_name".
      new_name (str): The new of the new attribute.
      is_method (bool): True if the attribute is a method, or False for a
        property.
  """

  def wrapper(obj, *args, **kwargs):
    """A wrapper function that is called for the added attribute.

    Args:
        obj (object): The object that contains the attribute.
        *args: The required arguments for the method.
        **kwargs: The keyword arguments for the method.

    Returns:
        value: The property or what was returned from the method.
    """
    # Log a deprecated message here after we have announced capabilities are ready.
    attr = _get_nested_attr(obj, new_name)
    if is_method:
      return attr(*args, **kwargs)
    else:
      return attr

  # mark deprecated for documentation
  wrapper.__deprecated__ = new_name
  wrapper.__doc__ = SPHINX_DEPRECATION_NOTICE.format(
      attr_type='method' if is_method else 'property', new_name=new_name)

  if is_method:
    setattr(cls, old_name, wrapper)
  else:
    setattr(cls, old_name, property(wrapper))


def add_deprecated_attributes(cls, attribute_list):
  """Add each attribute in a list of tuples to the class provided.

  Note: This must be called for a class and not for an instance of a class
  since dynamically adding a property cannot be done for an instance of a class.

  Args:
      cls (class): The class to add the attribute to.
      attribute_list (list): A list of tuples with the attributes to add where
        the tuple has: old_name, new_name, is_method
  """
  for old_name, new_name, is_method in attribute_list:
    add_deprecated_attribute(cls, old_name, new_name, is_method)
