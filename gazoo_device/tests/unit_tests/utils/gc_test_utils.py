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

"""Mixin with test methods to verify that a class has no reference loops."""
import collections
import gc

from gazoo_device.tests.unit_tests.utils import unit_test_case


class GCTestUtilsMixin(unit_test_case.UnitTestCase):
  """Test methods to verify that a class does not contain reference loops."""

  def make_gc_helper_class(self, uut_class):
    """Creates a subclass of uut_class with close, __del__ method wrappers."""

    class GCHelper(uut_class):
      """Adds wrappers to keep track of calls to .close() and __del__."""

      def __init__(self, *args, **kwargs):
        """Initialize GCHelper.

        Args:
            *args (tuple): positional args to pass to Manager.
            **kwargs (dict): keyword args to pass to Manager. Must contain
              "close_calls" (dict), "del_calls" (dict), and "logger" (Logger).
              The call dicts will contain the following entries:
              {<object ID>: <number of calls to method>}.
        """
        self.close_calls = kwargs.pop("close_calls")
        self.del_calls = kwargs.pop("del_calls")
        self._logger = kwargs.pop("logger")

        super().__init__(*args, **kwargs)

      def close(self):
        self.close_calls[id(self)] = self.close_calls.get(id(self), 0) + 1
        self._logger.info("close() called on object {}".format(id(self)))

        super().close()

      def __del__(self):
        self.del_calls[id(self)] = self.del_calls.get(id(self), 0) + 1
        self._logger.info("__del__ called on object {}".format(id(self)))

        super().__del__()

    return GCHelper

  def verify_no_reference_loops(self, uut_class, uut_args, uut_kwargs):
    """Test that deleting the last reference to the object deletes the instance.

    Args:
        uut_class (type): class instance of which should be tested
        uut_args (tuple): positional arguments to uut_class.__init__
        uut_kwargs (dict): keyword arguments to uut_kwargs.__init__
    """
    gc.collect()  # Ensure existing garbage doesn't interfere
    gc.disable()  # Ensure __del__ isn't called by periodic GC

    try:
      close_calls = collections.defaultdict(int)
      del_calls = collections.defaultdict(int)
      patched_uut_class = self.make_gc_helper_class(uut_class)

      uut_kwargs["close_calls"] = close_calls
      uut_kwargs["del_calls"] = del_calls
      uut_kwargs["logger"] = self.logger
      uut = patched_uut_class(*uut_args, **uut_kwargs)
      uut_id = id(uut)

      self.assertEqual(0, close_calls[uut_id])
      self.assertEqual(0, del_calls[uut_id])

      del uut
      self.assertEqual(1, close_calls[uut_id])
      self.assertEqual(1, del_calls[uut_id])
    finally:
      gc.enable()
