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


class DoorLockClusterTestSuite:
  """Mixin for Matter Door Lock cluster test suite.

  The mixin assumes self.endpoint is set.
  """

  def test_lock_door(self):
    """Tests the Lock command and checks its LockState attibute."""
    self.endpoint.door_lock.lock_door()
    asserts.assert_equal(matter_enums.LockState.LOCKED,
                         self.endpoint.door_lock.lock_state)

  def test_unlock_door(self):
    """Tests the Unlock command and checks its LockState attibute."""
    self.endpoint.door_lock.unlock_door()
    asserts.assert_equal(matter_enums.LockState.UNLOCKED,
                         self.endpoint.door_lock.lock_state)

  def test_door_lock_is_jammed(self):
    """Tests the case where the door lock is jammed (not fully locked)."""
    jammed_state = matter_enums.LockState.NOT_FULLY_LOCKED
    self.endpoint.door_lock.lock_state = jammed_state
    asserts.assert_equal(jammed_state,
                         self.endpoint.door_lock.lock_state)
