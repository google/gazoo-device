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

"""Unit tests for the queries sent to devices during detection."""
import logging
import os
import subprocess
from unittest import mock

from gazoo_device import detect_criteria
from gazoo_device.tests.unit_tests.utils import fake_detect_playback
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import adb_utils
from gazoo_device.utility import host_utils
from gazoo_device.utility import http_utils
from gazoo_device.utility import pwrpc_utils
from gazoo_device.utility import usb_config
from gazoo_device.utility import usb_utils
import immutabledict
import usb

_ADB_ADDRESS = "01a12345"
_IP_ADDRESS = "192.168.2.65"
_JLINK_ADDRESS = "/dev/serial/by-id/usb-SEGGER_J-Link_000050130117-if00"
_SERIAL_ADDRESS = (
    "/dev/serial/by-id/usb-Manufacturer-ProductName-SerialNumber-if00")
_MOCK_USB_DEVICE = mock.create_autospec(
    idProduct=0x0001,
    idVendor=0x1000,
    langids=(1033,),
    serial_number="12345678",
    product="Product name",
    spec=usb.core.Device)
_MOCK_USB_DEVICE_INFO = usb_config.UsbInfo(
    address=_SERIAL_ADDRESS,
    manufacturer="Manufacturer",
    product_id=1212,
    product_name="ProductName",
    serial_number="12345678",
    vendor_id=3434)

DEVICE_TYPE_TO_COMMS_ADDRESS = immutabledict.immutabledict({
    **{adb_device_type: _ADB_ADDRESS
       for adb_device_type in fake_detect_playback.ADB_DEVICE_BEHAVIORS},
    **{jlink_device_type: _JLINK_ADDRESS
       for jlink_device_type in fake_detect_playback.JLINK_DEVICE_BEHAVIORS},
    **{serial_device_type: _SERIAL_ADDRESS
       for serial_device_type in fake_detect_playback.SERIAL_DEVICE_BEHAVIORS},
    **{singleton_device_type: _SERIAL_ADDRESS
       for singleton_device_type in fake_detect_playback.SINGLETON_DEVICES},
    **{snmp_device_type: _IP_ADDRESS
       for snmp_device_type in fake_detect_playback.SNMP_DEVICE_BEHAVIORS},
    **{ssh_device_type: _IP_ADDRESS
       for ssh_device_type in fake_detect_playback.SSH_DEVICE_BEHAVIORS},
    # UsbComms devices use their communication addresses in detection criteria,
    # so their addresses may need to be different.
    **{usb_device_type: usb_behavior["address"]
       for usb_device_type, usb_behavior in
       fake_detect_playback.USB_DEVICE_BEHAVIORS.items()},
})


class TestDetectCriteria(unit_test_case.UnitTestCase):
  """Tests for detect_criteria.py."""
  _MOCKS = (
      (adb_utils, "root_device", None),
      (adb_utils, "shell", "adb_shell"),
      (host_utils, "ssh_command", "ssh_command"),
      (http_utils, "is_valid_ip_address", None),
      (http_utils, "send_http_get", "send_http_get"),
      (subprocess, "check_output", "check_output"),
      (usb_utils, "get_product_name_from_path", "get_product_name"),
      (usb_utils, "get_serial_number_from_path", "get_serial_number"),
      (usb_utils, "get_usb_device_from_serial_number",
       "get_usb_device_from_serial_number"),
  )

  def setUp(self):
    super().setUp()
    self.add_time_mocks()
    self.fake_detect_playback = fake_detect_playback.FakeDetectPlayback()
    self.mock_switchboard = mock.Mock()
    self.mock_switchboard.send_and_expect.side_effect = (
        self.fake_detect_playback.responder.send_and_expect)
    self.mock_create_switchboard = mock.Mock(return_value=self.mock_switchboard)
    for module, function, method_name in self._MOCKS:
      if method_name:
        side_effect = getattr(self.fake_detect_playback, method_name)
      else:
        side_effect = None
      self.enter_context(mock.patch.object(
          module, function, side_effect=side_effect))

  def test_snmp_comms_devices(self):
    """Verifies detection criteria for the SnmpComms comms type."""
    self._test_comms_type(
        "SnmpComms", fake_detect_playback.SNMP_DEVICE_BEHAVIORS)

  def test_ssh_devices(self):
    """Verifies detection criteria for the SSH comms type."""
    self._test_comms_type(
        "SshComms", fake_detect_playback.SSH_DEVICE_BEHAVIORS)

  def test_serial_devices(self):
    """Verifies detection criteria for the serial comms type."""
    self._test_comms_type(
        "SerialComms", fake_detect_playback.SERIAL_DEVICE_BEHAVIORS)

  def test_singleton_devices(self):
    """Verifies dection criteria for the singleton comms type."""
    singleton_devices = fake_detect_playback.SINGLETON_DEVICES
    for device_type, comms_type in singleton_devices.items():
      with self.subTest(comms_type=comms_type):
        self._test_comms_type(comms_type, {device_type: {}})

  def test_adb_devices(self):
    """Verifies detection criteria for the appropriate ADB comms type."""
    self._test_comms_type(
        "AdbComms", fake_detect_playback.ADB_DEVICE_BEHAVIORS)

  def test_jlink_devices(self):
    """Verifies detection criteria for the J-Link comms type."""
    self._test_comms_type(
        "JlinkSerialComms", fake_detect_playback.JLINK_DEVICE_BEHAVIORS)

  def test_ssh_devices_alt_poe(self):
    """Verifies detection criteria for the SSH comms type with updated poe."""
    updated_behaviors = {}
    updated_behaviors.update(fake_detect_playback.SSH_DEVICE_BEHAVIORS)
    updated_behaviors.update(fake_detect_playback.ALT_POE_BEHAVIORS)
    self._test_comms_type("SshComms", updated_behaviors)

  def test_usb_comms_devices(self):
    """Verifies detection criteria for the UsbComms type."""
    self._test_comms_type(
        "UsbComms", fake_detect_playback.USB_DEVICE_BEHAVIORS)

  def test_pty_process_name_query(self):
    """Tests _pty_process_name_query."""
    pty_address = "/some/host/path"
    self.assertEqual(
        pty_address,
        detect_criteria._pty_process_name_query(
            address=pty_address,
            detect_logger=mock.MagicMock(spec=logging.Logger),
            create_switchboard_func=mock.MagicMock()))

  def test_usb_vendor_product_id_from_serial_port_path(self):
    """Tests _usb_vendor_product_id_from_serial_port_path()."""
    with mock.patch.object(
        usb_utils, "get_device_info", return_value=_MOCK_USB_DEVICE_INFO):
      self.assertEqual(
          "3434:1212",
          detect_criteria._usb_vendor_product_id_from_serial_port_path(
              _SERIAL_ADDRESS,
              detect_logger=mock.MagicMock(spec=logging.Logger),
              create_switchboard_func=mock.MagicMock()))

  def test_usb_product_name_from_serial_number(self):
    """Tests _usb_product_name_from_serial_number()."""
    with mock.patch.object(usb_utils, "get_usb_device_from_serial_number",
                           return_value=_MOCK_USB_DEVICE):
      self.assertEqual(
          "Product name",
          detect_criteria._usb_product_name_from_serial_number(
              "12345678",
              detect_logger=mock.MagicMock(spec=logging.Logger),
              create_switchboard_func=mock.MagicMock()))

  def test_usb_vendor_product_id_query_found_usb_device(self):
    """Tests _usb_vendor_product_id_query() when a USB device is found."""
    with mock.patch.object(usb_utils, "get_usb_device_from_serial_number",
                           return_value=_MOCK_USB_DEVICE):
      self.assertEqual(
          "1000:0001",
          detect_criteria._usb_vendor_product_id_query(
              "12345678",
              detect_logger=mock.MagicMock(spec=logging.Logger),
              create_switchboard_func=mock.MagicMock()))

  def test_usb_vendor_product_id_query_not_found_usb_device(self):
    """Tests _usb_vendor_product_id_query() when no USB device is found."""
    with mock.patch.object(usb_utils, "get_usb_device_from_serial_number",
                           return_value=None):
      self.assertEqual(
          "",
          detect_criteria._usb_vendor_product_id_query(
              "12345678",
              detect_logger=mock.MagicMock(spec=logging.Logger),
              create_switchboard_func=mock.MagicMock()))

  def test_usb_serial_number(self):
    """Tests _usb_serial_number()."""
    self.assertEqual(
        "12345678",
        detect_criteria._usb_serial_number(
            "12345678",
            detect_logger=mock.MagicMock(spec=logging.Logger),
            create_switchboard_func=mock.MagicMock()))

  def test_manufacturer_name_query(self):
    """Tests _manufacturer_name_query()."""
    with mock.patch.object(usb_utils, "get_device_info",
                           return_value=_MOCK_USB_DEVICE_INFO):
      self.assertEqual(
          "manufacturer",
          detect_criteria._manufacturer_name_query(
              _SERIAL_ADDRESS,
              detect_logger=mock.MagicMock(spec=logging.Logger),
              create_switchboard_func=mock.MagicMock()))

  def test_pigweed_application_query(self):
    """Tests _pigweed_application_query()."""
    detect_logger = mock.MagicMock(spec=logging.Logger)
    detect_logger.handlers = [
        logging.FileHandler(
            os.path.join(self.artifacts_directory, "pigweed_detection_log.txt"))
    ]
    with mock.patch.object(
        pwrpc_utils, "get_application_type",
        return_value=pwrpc_utils.PigweedAppType.NON_PIGWEED.value):
      self.assertEqual(
          "nonpigweed",
          detect_criteria._pigweed_application_query(
              _JLINK_ADDRESS,
              detect_logger=detect_logger,
              create_switchboard_func=mock.MagicMock()))

  def _test_comms_type(
      self, comms_type, behaviors_dict, switchboard_behaviors_dict=None):
    errors = []
    bdict_name = "{}_DEVICE_BEHAVIORS".format(
        comms_type.replace("Comms", "").upper())
    device_types = [
        cls.DEVICE_TYPE
        for cls in detect_criteria.get_communication_type_classes(comms_type)
    ]
    self.assertCountEqual(
        behaviors_dict.keys(), device_types,
        f"All {comms_type} devices should have an entry in {bdict_name}")
    for device_type, behavior in behaviors_dict.items():
      address = DEVICE_TYPE_TO_COMMS_ADDRESS[device_type]
      log_file = os.path.join(self.artifacts_directory,
                              "{}_detect.txt".format(device_type))

      self.fake_detect_playback.behavior = behavior
      if switchboard_behaviors_dict:
        self.fake_detect_playback.responder.behavior_dict = (
            switchboard_behaviors_dict.get(device_type, {}))
      classes = detect_criteria.determine_device_class(
          address, comms_type, log_file, self.mock_create_switchboard)
      if len(classes) != 1 or classes[0].DEVICE_TYPE != device_type:
        errors.append("{}'s behavior returned {!r}".format(
            device_type, classes))

    if errors:
      error_msg = "Not all {} devices correctly matched. Mismatches: {}".format(
          comms_type, "\n\t".join(errors))
      self.fail(error_msg)


if __name__ == "__main__":
  unit_test_case.main()
