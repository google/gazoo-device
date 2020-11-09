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

"""Dynamically generated maps of all classes supported by GDM.

These are populated by reflection_utils.py at import time (in gazoo_device/__init__.py).
These values are intended for internal GDM usage only.
See Manager.get_all_supported_<...> methods for the user-facing APIs returning the same data.
"""
mappings_generated = False
SUPPORTED_AUXILIARY_DEVICE_CLASSES = None
SUPPORTED_CAPABILITIES = None
SUPPORTED_CAPABILITY_INTERFACES = None
SUPPORTED_CAPABILITY_FLAVORS = None
SUPPORTED_PRIMARY_DEVICE_CLASSES = None
SUPPORTED_VIRTUAL_DEVICE_CLASSES = None
