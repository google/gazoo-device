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

"""Mixin for Matter Door Lock cluster test suite."""
from gazoo_device.capabilities import matter_enums
from mobly import asserts

_LOCK_VALUE = matter_enums.LockState.LOCKED
_UNLOCK_VALUE = matter_enums.LockState.UNLOCKED


class DoorLockClusterTestSuite:
  """Mixin for Matter Door Lock cluster test suite.

  The mixin assumes self.endpoint is set.
  """

  def test_lock_unlock_command_and_lock_state_attribute(self):
    """Tests the Lock / Unlock command and LockState attribute."""
    if self.endpoint.door_lock.lock_state == _LOCK_VALUE:
      self._unlock_and_verify()
      self._lock_and_verify()
    else:
      self._lock_and_verify()
      self._unlock_and_verify()

  def _unlock_and_verify(self):
    """Unlocks the device and verifies the state."""
    self.endpoint.door_lock.unlock_door()
    asserts.assert_equal(_UNLOCK_VALUE, self.endpoint.door_lock.lock_state)

  def _lock_and_verify(self):
    """Locks the device and verifies the state."""
    self.endpoint.door_lock.lock_door()
    asserts.assert_equal(_LOCK_VALUE, self.endpoint.door_lock.lock_state)
