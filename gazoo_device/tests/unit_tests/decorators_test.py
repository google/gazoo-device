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

"""Unit tests for decorators.py."""
import inspect
import logging
import os
import sys

from absl.testing import parameterized
from gazoo_device import decorators
from gazoo_device import errors
from gazoo_device.tests.unit_tests.utils import unit_test_case


class NamedDevice:

  def __init__(self, device_name):
    self.name = device_name


class ShinyNewError(errors.DeviceError):
  pass


class _WithRepr:
  """A class where __repr__ works."""

  def __repr__(self):
    return "Representation"


class _WithoutReprWithStr:
  """A class where __repr__ doesn't work, but __str__ does."""

  def __repr__(self):
    raise ValueError("Something went wrong")

  def __str__(self):
    return "String"


class _WithoutReprWithoutStr:
  """A class where neither __repr__ nor __str__ works."""

  def __repr__(self):
    raise ValueError("Something went wrong")

  def __str__(self):
    raise ValueError("Something went wrong")


class _TestClass:
  """A class with a variety of method signatures."""

  @classmethod
  def class_method(cls):
    """A class method without any arguments."""

  def instance_method_with_positional_arg(self, positional_arg):
    """An instance method with a positional argument."""
    del positional_arg  # Unused.

  def instance_method_with_keyword_arg(self, keyword_arg="foo"):
    """An instance method with a keyword argument."""
    del keyword_arg  # Unused.

  def instance_method_with_positional_and_keyword_arg(
      self, positional_arg, keyword_arg="foo"):
    """An instance method with a positional and a keyword argument."""
    del positional_arg, keyword_arg  # Unused.


def _test_function(positional_arg, keyword_arg="foo"):
  """A function with a positional and a keyword argument."""
  del positional_arg, keyword_arg  # Unused.


_TestClassInstance = _TestClass()


class LogDecoratorSuite(unit_test_case.UnitTestCase):
  """Unit tests for decorators."""

  def setUp(self):
    super().setUp()
    self._create_logger()

  def test_function_name_stays_same(self):
    """Decorator must not change __name__ and __doc__ of the function."""

    class FakeDevice(NamedDevice):

      @decorators.LogDecorator(self.test_logger)
      def some_method(self):
        """Some docstring."""
        pass

    test_device = FakeDevice("SomeDevice")
    test_device.some_method()

    self.assertEqual(test_device.some_method.__name__, "some_method")
    self.assertEqual(test_device.some_method.__doc__, "Some docstring.")

  def test_function_return_value_stays_same(self):
    """Decorator must not change return value of the function."""

    class FakeDevice(NamedDevice):

      @decorators.LogDecorator(self.test_logger)
      def some_method_with_return(self, return_value):
        return return_value

    test_device = FakeDevice("SomeDevice")

    method_return_value = 5
    result = test_device.some_method_with_return(method_return_value)

    self.assertEqual(result, method_return_value)

  def test_function_signature_stays_same(self):
    """Decorator must not change the function signature."""

    decorator = decorators.LogDecorator(self.test_logger)

    class FakeDevice(NamedDevice):

      def some_method_with_params(self, posparam, kwparam="kwparamval"):
        pass

    test_device = FakeDevice("SomeDevice")

    decorated_method = decorator(test_device.some_method_with_params)

    signature_undecorated = inspect.getfullargspec(
        test_device.some_method_with_params)
    signature_decorated = inspect.getfullargspec(
        decorators.unwrap(decorated_method))

    self.assertEqual(signature_decorated, signature_undecorated)

  def test_silence_no_logs(self):
    """No log messages should be printed in silence mode."""

    class FakeDevice(NamedDevice):

      @decorators.LogDecorator(self.test_logger, level=decorators.NONE)
      def some_method(self):
        return 1 + 1

    test_device = FakeDevice("SomeDevice")
    test_device.some_method()

    with open(self.log_file) as lf:
      file_contents = lf.read()

    self.assertFalse(file_contents)

  def test_silence_no_skip_message(self):
    """No skip message should be printed in silence mode."""
    skip_reason = "Skipping method some_method_raises_skip"

    class FakeDevice(NamedDevice):

      @decorators.LogDecorator(self.test_logger, level=decorators.NONE)
      def some_method_raises_skip(self):
        raise decorators.SkipExceptionError(skip_reason)

    test_device = FakeDevice("SomeDevice")
    test_device.some_method_raises_skip()

    with open(self.log_file) as lf:
      file_contents = lf.read()

    self.assertFalse(file_contents)

  def test_silence_exceptions_wrapped(self):
    """Exceptions should still be wrapped in silence mode."""
    error_msg = "Provided Foo was too Bar."
    exc_msg = "ValueError: " + error_msg

    class FakeDevice(NamedDevice):

      @decorators.LogDecorator(self.test_logger, level=decorators.NONE)
      def some_method_raises(self):
        raise ValueError(error_msg)

    test_device = FakeDevice("SomeDevice")

    self.assertRaisesRegex(errors.DeviceError, exc_msg,
                           test_device.some_method_raises)

  def test_log_messages_printed(self):
    """Decorator should print messages on method start and successful finish."""
    device_name = "SomeDevice"
    self.test_logger.setLevel(decorators.INFO)

    class FakeDevice(NamedDevice):

      @decorators.LogDecorator(self.test_logger, level=decorators.INFO)
      def some_method(self):
        return 1 + 1

    test_device = FakeDevice(device_name)
    test_device.some_method()

    with open(self.log_file) as lf:
      file_contents = lf.read()

    start_msg = "{} starting {}.{}".format(device_name, FakeDevice.__name__,
                                           test_device.some_method.__name__)
    success_rx = r"{} {}.{} returned {}. It took \d+s.".format(
        device_name, FakeDevice.__name__, test_device.some_method.__name__, 2)
    self.assertIn(start_msg, file_contents)
    self.assertRegex(file_contents, success_rx)

  def test_class_name_for_inherited_methods(self):
    """Tests method class name retrieval for an inherited method."""
    device_name = "SomeDevice"
    self.test_logger.setLevel(decorators.INFO)

    class FakeDeviceParent(NamedDevice):

      @decorators.LogDecorator(self.test_logger, level=decorators.INFO)
      def some_method(self):
        return 1 + 1

    class FakeDeviceChild(FakeDeviceParent):
      pass

    test_device = FakeDeviceChild(device_name)
    test_device.some_method()

    with open(self.log_file) as lf:
      file_contents = lf.read()

    start_msg = "{} starting {}.{}".format(device_name,
                                           FakeDeviceParent.__name__,
                                           test_device.some_method.__name__)
    success_rx = r"{} {}.{} returned {}. It took \d+s.".format(
        device_name, FakeDeviceParent.__name__,
        test_device.some_method.__name__, 2)
    self.assertIn(start_msg, file_contents)
    self.assertRegex(file_contents, success_rx)
    self.assertNotIn(FakeDeviceChild.__name__, file_contents)

  def test_class_name_for_overridden_methods(self):
    """Tests method class name retrieval for an overridden inherited method."""
    device_name = "SomeDevice"
    self.test_logger.setLevel(decorators.INFO)

    class FakeDeviceParent(NamedDevice):

      @decorators.LogDecorator(self.test_logger, level=decorators.INFO)
      def some_method(self):
        return 1 + 1

    class FakeDeviceChild(FakeDeviceParent):

      @decorators.LogDecorator(self.test_logger, level=decorators.INFO)
      def some_method(self):
        return super().some_method()

    test_device = FakeDeviceChild(device_name)
    test_device.some_method()

    with open(self.log_file) as lf:
      file_contents = lf.read()

    for class_name in [FakeDeviceParent.__name__, FakeDeviceChild.__name__]:
      start_msg = "{} starting {}.{}".format(device_name, class_name,
                                             test_device.some_method.__name__)
      success_rx = r"{} {}.{} returned {}. It took \d+s.".format(
          device_name, class_name, test_device.some_method.__name__, 2)
      self.assertIn(start_msg, file_contents)
      self.assertRegex(file_contents, success_rx)

  def test_skip_message_printed(self):
    """Tests that decorator prints a skip message."""
    device_name = "SomeDevice"
    skip_reason = "Skipping method some_method_raises_skip"

    class FakeDevice(NamedDevice):

      @decorators.LogDecorator(self.test_logger)
      def some_method_raises_skip(self):
        raise decorators.SkipExceptionError(skip_reason)

    test_device = FakeDevice(device_name)
    test_device.some_method_raises_skip()

    with open(self.log_file) as lf:
      file_contents = lf.read()

    start_msg = "{} starting {}.{}".format(
        device_name, FakeDevice.__name__,
        test_device.some_method_raises_skip.__name__)
    success_rx = (r"{} {}.{} returned .*. It took \d+s.".format(
        device_name, FakeDevice.__name__,
        test_device.some_method_raises_skip.__name__))
    skip_msg = ("{} {}.{} skipped. {}".format(
        device_name, FakeDevice.__name__,
        test_device.some_method_raises_skip.__name__, skip_reason))
    self.assertIn(start_msg, file_contents)
    self.assertNotRegex(file_contents, success_rx)
    self.assertIn(skip_msg, file_contents)

  def test_exceptions_wrapped(self):
    """Tests wrapping exceptions in DeviceError."""
    device_name = "SomeDevice"
    error_msg = "Provided Foo was too Bar."
    exc_msg = "ValueError: " + error_msg

    class FakeDevice(NamedDevice):

      @decorators.LogDecorator(self.test_logger)
      def some_method_raises(self):
        raise ValueError(error_msg)

    test_device = FakeDevice(device_name)
    with self.assertRaisesRegex(errors.DeviceError, exc_msg):
      test_device.some_method_raises()

  def test_exceptions_wrapped_different_wrap_type(self):
    """Tests wrapping exceptions in a custom wrap_type."""
    device_name = "SomeDevice"
    error_msg = "Provided Foo was too Bar."
    exc_msg = "ValueError: " + error_msg
    wrap_type = ShinyNewError

    class FakeDevice(NamedDevice):

      @decorators.LogDecorator(self.test_logger, wrap_type=wrap_type)
      def some_method_raises(self):
        raise ValueError(error_msg)

    test_device = FakeDevice(device_name)
    with self.assertRaisesRegex(wrap_type, exc_msg):
      test_device.some_method_raises()

  def test_raise_subclass_of_deviceerror(self):
    """Tests wrapping of errors which are subclasses of DeviceError."""
    device_name = "Dummy_device"
    err_reason = "Dummy error"

    class FakeDevice(NamedDevice):

      @decorators.LogDecorator(self.test_logger)
      def some_method_raises(self):
        raise errors.DfuModeError(device_name, err_reason)

    test_device = FakeDevice(device_name)
    self.assertRaisesRegex(errors.DfuModeError, err_reason,
                           test_device.some_method_raises)

  def test_log_messages_printed_no_device_name_available(self):
    """Tests falling back to the default device name, DEFAULT_DEVICE_NAME."""
    device_name = decorators.DEFAULT_DEVICE_NAME

    class FakeDevice:

      @decorators.LogDecorator(self.test_logger)
      def some_method(self):
        return 1 + 1

    test_device = FakeDevice()
    test_device.some_method()

    with open(self.log_file) as lf:
      file_contents = lf.read()

    start_msg = "{} starting {}.{}".format(device_name, FakeDevice.__name__,
                                           test_device.some_method.__name__)
    success_rx = r"{} {}.{} returned {}. It took \d+s.".format(
        device_name, FakeDevice.__name__, test_device.some_method.__name__, 2)
    self.assertIn(start_msg, file_contents)
    self.assertRegex(file_contents, success_rx)

  def test_different_device_name_attribute(self):
    """Test device name attribute that's not 'self.name'."""
    device_name = "CoolDevice"

    class FakeDevice:

      @decorators.LogDecorator(
          self.test_logger, name_attr="some_device_name_attr")
      def some_method(self):
        return 1 + 1

    test_device = FakeDevice()
    test_device.some_device_name_attr = device_name

    test_device.some_method()

    with open(self.log_file) as lf:
      file_contents = lf.read()

    start_msg = "{} starting {}.{}".format(device_name, FakeDevice.__name__,
                                           test_device.some_method.__name__)
    success_rx = r"{} {}.{} returned {}. It took \d+s.".format(
        device_name, FakeDevice.__name__, test_device.some_method.__name__, 2)
    self.assertIn(start_msg, file_contents)
    self.assertRegex(file_contents, success_rx)

  def test_debug_level_not_in_info_logger(self):
    """Test that debug messages are omitted from logger with INFO level."""
    self.test_logger.setLevel(decorators.INFO)

    class FakeDevice(NamedDevice):

      @decorators.LogDecorator(self.test_logger, level=decorators.DEBUG)
      def some_method(self):
        return 1 + 1

    test_device = FakeDevice("SomeDevice")
    test_device.some_method()

    with open(self.log_file) as lf:
      file_contents = lf.read()

    self.assertFalse(file_contents)

  def test_info_level_in_debug_logger(self):
    """Test that INFO messages are present in logger with DEBUG level."""
    self.test_logger.setLevel(decorators.DEBUG)
    device_name = "SomeDevice"

    class FakeDevice(NamedDevice):

      @decorators.LogDecorator(self.test_logger, level=decorators.INFO)
      def some_method(self):
        return 1 + 1

    test_device = FakeDevice(device_name)
    test_device.some_method()

    with open(self.log_file) as lf:
      file_contents = lf.read()

    start_msg = "{} starting {}.{}".format(device_name, FakeDevice.__name__,
                                           test_device.some_method.__name__)
    success_rx = r"{} {}.{} returned {}. It took \d+s.".format(
        device_name, FakeDevice.__name__, test_device.some_method.__name__, 2)
    self.assertIn(start_msg, file_contents)
    self.assertRegex(file_contents, success_rx)

  def test_cannot_decorate_non_methods(self):
    """Tests than an error is raised if a non-method is decorated."""
    decorator = decorators.LogDecorator(self.test_logger)

    def func():
      pass

    lambda_func = lambda: None

    invalid_values = [
        func, lambda_func, "string", None, 5, 5.0, {}, [], (),
        set()
    ]

    for val in invalid_values:
      with self.assertRaises(TypeError):
        decorator(val)

  def test_cannot_decorate_static_method(self):
    """Test that methods decorated with @staticmethod cannot be decorated."""
    decorator = decorators.LogDecorator(self.test_logger)

    class SomeClass:

      @staticmethod
      def foo():
        pass

    instance = SomeClass()

    with self.assertRaisesRegex(
        TypeError, r".*Decorating static methods is not supported"):
      decorator(SomeClass.foo)

    with self.assertRaisesRegex(
        TypeError, r".*Decorating static methods is not supported"):
      decorator(instance.foo)

  def test_cannot_decorate_class_method(self):
    """Test that methods decorated with @classmethod cannot be decorated."""
    decorator = decorators.LogDecorator(self.test_logger)

    class SomeClass:

      @classmethod
      def foo(cls):
        pass

    instance = SomeClass()

    with self.assertRaisesRegex(TypeError,
                                r".*Decorating class methods is not supported"):
      decorator(SomeClass.foo)

    with self.assertRaisesRegex(TypeError,
                                r".*Decorating class methods is not supported"):
      decorator(instance.foo)

  def test_unwrap_not_a_function(self):
    """Test unwrap on an object which is not a function."""
    someint = 1
    self.assertEqual(someint, decorators.unwrap(someint))

  def test_unwrap_function_not_decorated(self):
    """Test unwrap on a function which has not been decorated."""

    def foo():
      pass

    self.assertEqual(foo, decorators.unwrap(foo))

  def test_unwrap_decorated_method(self):
    """Test unwrap on a decorated method."""
    decorator = decorators.LogDecorator(self.test_logger)

    class FakeDevice(NamedDevice):

      def some_method(self):
        pass

    test_device = FakeDevice("SomeDevice")

    undecorated_method = test_device.some_method
    decorated_method = decorator(undecorated_method)

    self.assertEqual(undecorated_method, decorators.unwrap(decorated_method))

  def test_arg_to_str_for_repr(self):
    """Tests _arg_to_str() for an object where __repr__ works."""
    self.assertEqual(decorators._arg_to_str(_WithRepr()), "Representation")

  def test_arg_to_str_for_str(self):
    """Tests _arg_to_str() for object where __repr__ fails but __str__ works."""
    self.assertEqual(decorators._arg_to_str(_WithoutReprWithStr()), "String")

  def test_arg_to_str_no_description(self):
    """Tests _arg_to_str() for object where both __repr__ and __str__ fail."""
    self.assertEqual(
        decorators._arg_to_str(_WithoutReprWithoutStr()), "<No description>")

  @parameterized.named_parameters(
      ("no_print_args", False, logging.INFO,
       _TestClassInstance.instance_method_with_positional_arg,
       ("foo",), {}, ""),
      ("debug_arg_length_clipping", True, logging.DEBUG,
       _TestClassInstance.instance_method_with_positional_arg,
       ("a" * 10000,), {},
       "(positional_arg='{})".format(
           "a" * (decorators._MAX_ARG_REPR_LENGTH_DEBUG - 1) + "...")),
      ("info_arg_length_clipping", True, logging.INFO,
       _TestClassInstance.instance_method_with_positional_arg,
       ("a" * 10000,), {},
       "(positional_arg='{})".format(
           "a" * (decorators._MAX_ARG_REPR_LENGTH_INFO - 1) + "...")),
      ("function_with_positional_and_keyword_arg", True, logging.INFO,
       _test_function, ("foo",), {"keyword_arg": "bar"},
       "(positional_arg='foo', keyword_arg='bar')"),
      ("class_method_no_args", True, logging.INFO,
       _TestClass.class_method, (), {}, "()"),
      ("instance_method_positional_arg", True, logging.INFO,
       _TestClassInstance.instance_method_with_positional_arg,
       ("foo",), {}, "(positional_arg='foo')"),
      ("instance_method_keyword_arg", True, logging.INFO,
       _TestClassInstance.instance_method_with_keyword_arg,
       (), {"keyword_arg": "bar"}, "(keyword_arg='bar')"),
      ("instance_method_with_positional_and_keyword_arg", True, logging.INFO,
       _TestClassInstance.instance_method_with_positional_and_keyword_arg,
       ("foo",), {"keyword_arg": "bar"},
       "(positional_arg='foo', keyword_arg='bar')"))
  def test_get_args_and_kwargs_str(
      self, print_args, log_level, method_or_function, args, kwargs, expected):
    """Tests _get_args_and_kwargs_str()."""
    self.assertEqual(
        decorators._get_args_and_kwargs_str(
            print_args=print_args,
            log_level=log_level,
            method_signature=inspect.signature(method_or_function),
            method_args=args,
            method_kwargs=kwargs),
        expected)

  def _create_logger(self):
    self.test_logger = logging.getLogger(self._testMethodName)
    self.log_file = os.path.join(self.artifacts_directory,
                                 self._testMethodName + ".log")
    file_handler = logging.FileHandler(self.log_file, "w")
    self.addCleanup(file_handler.close)

    self.test_logger.addHandler(file_handler)
    self.test_logger.addHandler(logging.StreamHandler(sys.stdout))
    self.test_logger.setLevel(logging.DEBUG)


if __name__ == "__main__":
  unit_test_case.main()
