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

"""Unit tests for gazoo_device.utility.pwrpc_utils.py."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device import errors
from gazoo_device.utility import pwrpc_utils


_FAKE_ADDRESS = "fake-address"
_FAKE_LOG_PATH = "fake-log-path"
_FAKE_CALL_GOOD_RESPONSE = (True, None)
_FAKE_DECODER_PATH = "fake_module.fake_class"
_FAKE_BYTES = b"fake-bytes"


def _fake_matter_app_response(matter_device_type, call_args):
  """Fake Matter application responses."""
  for method_args, _, app_type in pwrpc_utils._PIGWEED_APP_ENDPOINTS:
    if matter_device_type == app_type and call_args == method_args:
      return _FAKE_CALL_GOOD_RESPONSE
  raise errors.DeviceError("error")


def _create_fake_app_response(matter_device_type):
  """Creates fake Matter application responses function."""
  def _fake_response(method, method_args, method_kwargs):
    del method  # unused
    del method_kwargs  # unused
    return _fake_matter_app_response(matter_device_type, method_args)
  return _fake_response


class PwRPCUtilsTests(parameterized.TestCase):
  """Unit tests for gazoo_device.utility.pwrpc_utils.py."""

  def setUp(self):
    super().setUp()
    fake_inst = mock.Mock()
    fake_inst.SerializeToString.return_value = _FAKE_BYTES
    self.proto_state = pwrpc_utils.PigweedProtoState(
        proto_inst=fake_inst,
        decoder_path=_FAKE_DECODER_PATH)

  @parameterized.named_parameters(
      ("lighting_app", pwrpc_utils.PigweedAppType.LIGHTING),
      ("locking_app", pwrpc_utils.PigweedAppType.LOCKING),
      ("non-matter-app", pwrpc_utils.PigweedAppType.NON_PIGWEED))
  def test_get_application_type_for_various_apps(self, app):
    """Verifies get_application_type for various apps."""
    mock_create_switchboard = mock.Mock()
    fake_app_response = _create_fake_app_response(app)
    mock_create_switchboard.return_value.call = (
        mock.MagicMock(side_effect=fake_app_response))

    app_type = pwrpc_utils.get_application_type(
        address=_FAKE_ADDRESS,
        log_path=_FAKE_LOG_PATH,
        create_switchboard_func=mock_create_switchboard)

    self.assertEqual(app.value, app_type)

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
