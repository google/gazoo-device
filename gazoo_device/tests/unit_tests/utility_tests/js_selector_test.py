# Copyright 2023 Google LLC
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

"""Unit tests for js_selector module."""
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import js_selector


class JsSelectorTest(unit_test_case.UnitTestCase):
  """Unit tests for js_selector module."""

  def testSelectorInit_Defaults(self):
    selector = js_selector.JsSelector()
    self.assertEqual(selector.ToJavascript(), '[document]')

  def testSelectorInit_Window(self):
    selector = js_selector.JsSelector(javascript='[window]')
    self.assertEqual(selector.ToJavascript(), '[window]')

  def testSelectorQuerySelector(self):
    selector = js_selector.JsSelector(
        javascript='[root]').QuerySelector('[id="a"]')
    self._AssertMapping(selector, '.map(e=>e.querySelector(\'[id="a"]\'))')

  def testSelectorNullGuard(self):
    selector = js_selector.JsSelector(javascript='[root]').NullGuard()
    self._AssertMapping(selector, '.flatMap(e=>e==null?[]:[e])')

  def testSelectorShadowRoot(self):
    selector = js_selector.JsSelector(javascript='[root]').ShadowRoot()
    self._AssertMapping(selector, '.map(e=>e.shadowRoot)')

  def testSelectorProperty(self):
    selector = js_selector.JsSelector(javascript='[root]').Property('some_prop')
    self._AssertMapping(selector, '.map(e=>e.some_prop)')

  def testSelectorMap(self):
    selector = js_selector.JsSelector(javascript='[root]').Map('e=>e.f()')
    self._AssertMapping(selector, '.map(e=>e.f())')

  def testSelectorChain(self):
    selector = js_selector.JsSelector(
        javascript='[root]').Property('a').Property('b')
    self._AssertMapping(selector, '.map(e=>e.a).map(e=>e.b)')

  def _AssertMapping(self, selector, javascript):
    expected = '[root]%s' % javascript
    self.assertEqual(selector.ToJavascript(), expected)

  def testSelectorGetOrDefault_Default(self):
    unwrapped = js_selector.JsSelector(javascript='[root]').GetOrDefault()
    expected = '[[root]].flatMap(a=>a.length==0?[(null)]:a)[0]'
    self.assertEqual(unwrapped, expected)

  def testSelectorGetOrDefault_SomeValue(self):
    unwrapped = js_selector.JsSelector(javascript='[root]').GetOrDefault('abc')
    expected = '[[root]].flatMap(a=>a.length==0?[(abc)]:a)[0]'
    self.assertEqual(unwrapped, expected)

  def testSelectorStr(self):
    selector = js_selector.JsSelector(javascript='[window]')
    self.assertEqual(selector.ToJavascript(), str(selector))


if __name__ == '__main__':
  unit_test_case.main()
