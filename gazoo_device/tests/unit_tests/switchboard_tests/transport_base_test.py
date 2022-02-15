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

"""Tests the GDM transport interface module (TransportBase)."""
from gazoo_device.switchboard import transport_properties
from gazoo_device.switchboard.transports import transport_base
from gazoo_device.tests.unit_tests.utils import unit_test_case


class FakeBadTransport(transport_base.TransportBase):
  """Doesn't define _write() method and thus cannot be instantiated."""

  def is_open(self):
    pass

  def _open(self):
    pass

  def _close(self):
    pass

  def _read(self, size=1, timeout=None):
    pass


class FakeGoodTransport(transport_base.TransportBase):

  def __init__(self, someprop=None, auto_reopen=False, open_on_start=True):
    super().__init__(auto_reopen, open_on_start)
    self._properties.update({"somekey": someprop})
    self.hooks_called = {
        "is_open": False,
        "_open": False,
        "_close": False,
        "_read": False,
        "_write": False
    }
    self.is_transport_open = False

  def is_open(self):
    self.hooks_called["is_open"] = True
    return self.is_transport_open

  def _open(self):
    self.hooks_called["_open"] = True
    self.is_transport_open = True

  def _close(self):
    self.hooks_called["_close"] = True
    self.is_transport_open = False

  def _read(self, size=1, timeout=None):
    self.hooks_called["_read"] = True

  def _write(self, data, timeout=None):
    self.hooks_called["_write"] = True


# Public method -> tuple of (corresponding private method, test args)
_TEST_DATA = {
    "open": ("_open", ()),
    "close": ("_close", ()),
    "read": ("_read", ()),
    "write": ("_write", ("bogusdata",))
}


class TransportBaseTests(unit_test_case.UnitTestCase):

  def test_001_transport_base_cannot_be_instantiated(self):
    """Test if it's possible to instantiate TransportBase."""
    with self.assertRaisesRegexp(TypeError,
                                 r"Can't instantiate abstract class"):
      transport_base.TransportBase(False, False)

  def test_010_transport_base_good_subclass_instantiation(self):
    """Tests concrete subclass instantiation."""
    prop_value = "top_kek"
    tb = FakeGoodTransport(prop_value, True)
    self.assertEqual(prop_value, tb.get_property("somekey"))
    self.assertEqual(True, tb.get_property(transport_properties.AUTO_REOPEN))
    self.assertEqual(True, tb.get_property(transport_properties.OPEN_ON_START))
    self.assertIs(None, tb.get_property("bogus_property"))

  def test_011_transport_base_bad_subclass_instantiation(self):
    """Tests abstract subclass instantiation."""
    with self.assertRaisesRegexp(TypeError,
                                 r"Can't instantiate abstract class"):
      FakeBadTransport(False, False)

  def test_020_is_open_called_for_each_method(self):
    """is_open() should be called for each method."""
    for method in _TEST_DATA:
      tb = FakeGoodTransport()
      getattr(tb, method)(*_TEST_DATA[method][1])
      self.assertTrue(tb.hooks_called["is_open"])

  def test_021_closed_transport_hooks_should_not_be_called(self):
    """Test calling close, read, write on a closed transport."""
    for method in ["close", "read", "write"]:
      tb = FakeGoodTransport()
      getattr(tb, method)(*_TEST_DATA[method][1])
      self.assertFalse(tb.hooks_called[_TEST_DATA[method][0]])

  def test_022_closed_transport_open_works(self):
    """Calling open() on an empty transport should call _open() hook."""
    tb = FakeGoodTransport()
    tb.open()
    self.assertTrue(tb.hooks_called["_open"])
    self.assertTrue(tb.is_open())

  def test_023_open_transport_open_does_nothing(self):
    """Calling open() on an open transport should not call _open() hook."""
    tb = FakeGoodTransport()
    tb.open()
    self.assertTrue(tb.is_open())

    tb.hooks_called["_open"] = False
    tb.open()
    self.assertFalse(tb.hooks_called["_open"])

  def test_024_open_transport_hooks_work(self):
    """Test calling close, read, write on an open transport."""
    for method in ["close", "read", "write"]:
      tb = FakeGoodTransport()
      tb.open()
      self.assertTrue(tb.is_open())

      getattr(tb, method)(*_TEST_DATA[method][1])
      self.assertTrue(tb.hooks_called[_TEST_DATA[method][0]])

  def test_025_open_transport_and_close(self):
    """Test opening and closing a transport."""
    tb = FakeGoodTransport()
    self.assertFalse(tb.is_open())

    tb.open()
    self.assertTrue(tb.hooks_called["is_open"])
    self.assertTrue(tb.hooks_called["_open"])
    self.assertTrue(tb.is_open())
    self.assertFalse(tb.hooks_called["_close"])

    tb.close()
    self.assertTrue(tb.hooks_called["_close"])
    self.assertFalse(tb.is_open())


if __name__ == "__main__":
  unit_test_case.main()
