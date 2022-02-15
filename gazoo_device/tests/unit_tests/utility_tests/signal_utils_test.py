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

"""Unit tests for gazoo_device.utility.signal_utils.py."""
import signal
import sys
from unittest import mock

from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import signal_utils


class SignalUtilsTests(unit_test_case.UnitTestCase):
  """Unit tests for gazoo_device.utility.signal_utils.py."""

  def test_handle_sigterm(self):
    """Tests that handle_sigterm raises a SystemExit exception."""
    with self.assertRaises(SystemExit) as cm:
      signal_utils.handle_sigterm(signal.SIGTERM.value, None)
    self.assertEqual(cm.exception.code, signal_utils._BASH_SIGTERM_EXIT_CODE)

  def test_signalreceiver_handle_signal(self):
    """Tests _SignalReceiver.handle_signal."""
    signal_receiver = signal_utils._SignalReceiver()
    self.assertFalse(signal_receiver.received)
    signal_receiver.handle_signal(signal.SIGTERM.value, None)
    self.assertTrue(signal_receiver.received)

  @mock.patch.object(signal_utils, "_SignalReceiver", autospec=True)
  @mock.patch.object(signal, "signal")
  @mock.patch.object(signal, "getsignal")
  @mock.patch.object(sys, "exit")
  def test_postpone_sigterm_until_completion_no_signal(
      self, mock_sys_exit, mock_signal_getsignal, mock_signal_signal,
      mock_signalreceiver_class):
    """Tests postpone_sigterm_until_completion when it doesn't get a signal."""
    previous_handler = lambda: None
    mock_signal_getsignal.return_value = previous_handler
    signal_receiver = mock_signalreceiver_class.return_value
    signal_receiver.received = False

    with signal_utils.postpone_sigterm_until_completion():
      mock_signal_signal.assert_called_once_with(
          signal.SIGTERM, signal_receiver.handle_signal)

    mock_signal_signal.assert_called_with(signal.SIGTERM, previous_handler)
    mock_sys_exit.assert_not_called()

  @mock.patch.object(signal_utils, "_SignalReceiver", autospec=True)
  @mock.patch.object(signal, "signal")
  @mock.patch.object(signal, "getsignal")
  @mock.patch.object(sys, "exit")
  def test_postpone_sigterm_until_completion_with_signal(
      self, mock_sys_exit, mock_signal_getsignal, mock_signal_signal,
      mock_signalreceiver_class):
    """Tests postpone_sigterm_until_completion when it receives a signal."""
    previous_handler = lambda: None
    mock_signal_getsignal.return_value = previous_handler
    signal_receiver = mock_signalreceiver_class.return_value
    signal_receiver.received = False

    with signal_utils.postpone_sigterm_until_completion():
      mock_signal_signal.assert_called_once_with(
          signal.SIGTERM, signal_receiver.handle_signal)
      signal_receiver.received = True

    mock_signal_signal.assert_called_with(signal.SIGTERM, previous_handler)
    mock_sys_exit.assert_called_once_with(signal_utils._BASH_SIGTERM_EXIT_CODE)


if __name__ == "__main__":
  unit_test_case.main()
