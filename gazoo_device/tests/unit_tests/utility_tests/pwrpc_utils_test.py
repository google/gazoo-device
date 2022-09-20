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

"""Unit tests for module gazoo_device.utility.pwrpc_utils."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device import errors
from gazoo_device import switchboard
from gazoo_device.tests.unit_tests.utils import fake_device_test_case
from gazoo_device.utility import pwrpc_utils

_FAKE_ADDRESS = "fake-address"
_FAKE_LOG_PATH = "fake-log-path"
_FAKE_DECODER_PATH = "fake_module.fake_class"
_FAKE_BYTES = b"fake-bytes"
_FAKE_ERROR_MESSAGE = "fake-message"


class PwRpcUtilsTests(fake_device_test_case.FakeDeviceTestCase):
  """Unit tests for module gazoo_device.utility.pwrpc_utils."""

  def setUp(self):
    super().setUp()
    fake_inst = mock.Mock()
    fake_inst.SerializeToString.return_value = _FAKE_BYTES
    self.proto_state = pwrpc_utils.PigweedProtoState(
        proto_inst=fake_inst,
        decoder_path=_FAKE_DECODER_PATH)

  @mock.patch.object(pwrpc_utils.importlib, "import_module")
  def test_get_decoder(self, mock_import_module):
    """Verifies _get_decoder method on success."""
    decoder = self.proto_state._get_decoder()
    self.assertIsNotNone(decoder)
    mock_import_module.assert_called_once()

  @mock.patch.object(pwrpc_utils.PigweedProtoState, "_get_decoder")
  def test_decode(self, mock_get_decoder):
    """Verifies decode method on success."""
    fake_decoder = mock.Mock()
    mock_get_decoder.return_value = fake_decoder

    proto_inst = self.proto_state.decode()

    self.assertIsNotNone(proto_inst)
    fake_decoder.assert_called_once_with(_FAKE_BYTES)

  @parameterized.parameters(dict(is_matter=True), dict(is_matter=False))
  def test_is_matter_device(self, is_matter):
    """Verifies is_matter_device method."""
    fake_switchboard_func = mock.Mock(
        spec=switchboard.switchboard.SwitchboardDefault)
    if not is_matter:
      fake_switchboard_func.return_value.call.side_effect = (
          errors.DeviceError(_FAKE_ERROR_MESSAGE))
    else:
      fake_switchboard_func.return_value.call.return_value = None

    self.assertEqual(is_matter,
                     pwrpc_utils.is_matter_device(
                         address=_FAKE_ADDRESS,
                         log_path=_FAKE_LOG_PATH,
                         create_switchboard_func=fake_switchboard_func,
                         detect_logger=mock.Mock()))

    fake_switchboard_func.return_value.close.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
