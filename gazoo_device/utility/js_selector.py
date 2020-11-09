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

"""Provides classes to ease writing snippets of javascript code in python.

The JsSelector class allows generating selector code easily.

Copy-pasted from eurtest.tools.chrome.js_code.py.
"""


class JsSelector(object):
    """Create javascript code for selecting DOM elements.

    This class generates javascript code that can chain calls on a root element
    ('document' by default) while catering to common use cases such as
    querySelector, and shadowRoot.  Uses a javascript array type as an optional
    type so that you can create a document element selector arbitrarily deep,
    across shadowroots, and with null guards.

    Typical usage.
        RECIPE = (JsSelector()
                .QuerySelector('[data-window-id="ui.RECIPE_OVERVIEW"]').NullGuard()
                .ShadowRoot().NullGuard()
                .QuerySelector('[id="overview-native-container"]').NullGuard()
            )
        RECIPE_SCROLL_TOP = RECIPE.Property('scrollTop')

        def test():
            <device>.devtools.connect().evaluate_javascript(RECIPE_SCROLL_TOP.GetOrDefault('0'))
            <device>.devtools.connect().evaluate_javascript(
                '(%s) != null' %s RECIPE.GetOrDefault())
    """

    def __init__(self, javascript='[document]'):
        self._javascript = '%s' % javascript

    def __str__(self):
        """Returns the javascript representation as a description."""
        return self._javascript

    def QuerySelector(self, selector):
        """Returns this selector followed by a call to querySelector."""
        return JsSelector('%s.map(e=>e.querySelector(\'%s\'))' %
                          (self._javascript, selector))

    def NullGuard(self):
        """Returns this selector followed by a null check.

        Generates code that ensures that subsequent javascript methods will not
        be called if the value is null.

        Returns:
            JsSelector: A selector that represents this selector followed by a null check.
        """
        return JsSelector('%s.flatMap(e=>e==null?[]:[e])' % (self._javascript))

    def ShadowRoot(self):
        """Returns this selector followed by getting the shadowRoot property."""
        return self.Property('shadowRoot')

    def Property(self, property_name):
        """Returns this selector followed by a call to the given property."""
        return JsSelector('%s.map(e=>e.%s)' % (self._javascript, property_name))

    def Map(self, function):
        """Returns this selector followed by a call to the given function."""
        return JsSelector('%s.map(%s)' % (self._javascript, function))

    def GetOrDefault(self, default='null'):
        """Returns code for this selector's value or the given default.

        The expression will yield either null or the value.

        Args:
            default (str): A javascript expression of the default value. Must not be None,
                           but the javascript expression may evaluate to 'null'.

        Returns:
            str: a string with the javascript expression.
        """
        return '[%s].flatMap(a=>a.length==0?[(%s)]:a)[0]' % (self._javascript, default)

    def ToJavascript(self):
        """Returns the javascript code for this selector.

        The statement will have a type of array, and the array will be empty
        or contain a single value.

        Returns:
            str: a string with the javascript expression.
        """
        return self._javascript
