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

"""Base class for device and capability unit tests.

Sets up the common components of unit testing device classes and capabilities
with fake device responses. Uses fake_responder for mocking device responses.
Closes self.uut upon test tearDown.

To use, call setup_fake_device_requirements() in test setUp.
"""
import json
import logging
import os
import re
from typing import Any, Mapping, Optional
from unittest import mock

from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.base_classes import gazoo_device_base
from gazoo_device.capabilities import event_parser_default
from gazoo_device.tests.unit_tests.utils import fake_devices
from gazoo_device.tests.unit_tests.utils import fake_responder
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import usb_utils
import immutabledict

main = unit_test_case.main
MockSubprocess = unit_test_case.MockSubprocess
MockFile = unit_test_case.MockFile

MOCK_DEVICE_USB_HUB_INFO = {
    "device_usb_port": 2,
    "device_usb_hub_name": "cambrionix-1234",
}


def _mock_get_last_event(device_event_file_name, event_label, timeout=1.0):
  """Mock of event_parser._get_last_event (to avoid host dependencies)."""
  del timeout  # Unused by the mock implementation.
  if not os.path.exists(device_event_file_name):
    return None, True

  with open(device_event_file_name) as device_event_file:
    file_contents = device_event_file.readlines()

  if event_label is None:
    event_line = file_contents[-1]
  else:
    word_regex = rf"\b{event_label}\b"
    for line in file_contents[::-1]:
      if re.search(word_regex, line):
        event_line = line
        break
    else:
      event_line = ""

  event_labels = None if event_label is None else [event_label]
  # pylint: disable=protected-access
  events = event_parser_default._get_events_from_json_output([event_line],
                                                             event_labels)
  # pylint: enable=protected-access
  result = events[0] if events else None
  return result, False


class FakeDeviceTestCase(unit_test_case.UnitTestCase):
  """Base class for unit tests with mock device communication."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.fake_responder = None
    self.mock_manager = None
    self.mock_switchboard = None
    self.uut = None
    self.device_config = None

  @classmethod
  def tearDownClass(cls):
    super().tearDownClass()
    mock.patch.stopall()

  def setup_fake_device_requirements(self,
                                     uut_name: str = "fakedevice-1234",
                                     debug: bool = False):
    """Sets up communication mocks commonly used by device unit tests.

    Creates:
    * self.device_config (dict): Persistent and optional device configuration.
    * self.mock_switchboard (MagicMock): A mock of device communication.
    * self.fake_responder (FakeResponder): Fake device IO. Sets "behavior_dict"
      and "response".
    * self.uut (GazooDeviceBase or AuxiliaryDevice): Not initiated.
    * self.mock_manager(MagicMock): A mock of gazoo_device.manager.

    Args:
      uut_name: Name of fake device under test. Format:
        "<device_type>-<device-id>".
      debug: If True, enables debug logging for FakeResponder.

    Raises:
      RuntimeError: If uut_name is not in <device_type>-<device-id> format.
    """
    self.uut_name = uut_name
    self.device_config = fake_devices.create_default_device_config(uut_name)

    self.mock_manager = fake_devices.create_mock_manager(
        self.artifacts_directory)

    self._log_to_artifacts_directory()
    self.fake_responder = fake_responder.FakeResponder(debug=debug)
    self.mock_switchboard = fake_devices.create_mock_switchboard(
        uut_name, self.mock_manager, self.fake_responder)
    self.mock_out_usb_utils_methods()
    self.add_time_mocks()
    self.check_device_connected_patch_primary = mock.patch.object(
        gazoo_device_base.GazooDeviceBase,
        "check_device_connected",
        autospec=True)
    self.check_device_connected_patch_primary.start()
    self.addCleanup(self.check_device_connected_patch_primary.stop)
    self.check_device_connected_patch_auxiliary = mock.patch.object(
        auxiliary_device.AuxiliaryDevice,
        "check_device_connected",
        autospec=True)
    self.check_device_connected_patch_auxiliary.start()
    self.addCleanup(self.check_device_connected_patch_auxiliary.stop)

  def validate_dynamic_properties(self,
                                  expected_dynamic_properties,
                                  error_msg=None):
    """Verifies dynamic device properties."""
    # Setup returns a mock method instead of a property for these properties.
    exception_property_regexes = (
        r"^usb_hub\.supported_modes:Exception_DeviceError$",
        r"^comm_power\.port_mode:Exception_DeviceError$",
        r"^device_power\.port_mode:Exception_DeviceError$",
    )
    error_msg = error_msg or "All dynamic properties should be retrievable"
    self.validate_properties(
        self.uut.get_dynamic_properties(),
        expected_dynamic_properties,
        error_msg,
        exception_property_regexes=exception_property_regexes)

  def validate_optional_properties(
      self,
      expected_optional_properties: Mapping[str, Any],
      error_msg: Optional[str] = None) -> None:
    """Verifies optional device properties.

    Args:
      expected_optional_properties: Dictionary containing optional properties
        and their expected values.
      error_msg: Optional message to output for bad validatation
    """
    error_msg = error_msg or "All optional properties should be retrievable"
    self.validate_properties(
        self.uut.get_optional_properties(),
        expected_optional_properties,
        error_msg)

  def _log_to_artifacts_directory(self):
    """Sets up logging to test artifact directory."""
    gdm_log_file = os.path.join(self.artifacts_directory,
                                self._testMethodName + "-gdm.txt")
    gdm_log_formatter = logging.Formatter(
        gdm_logger.FMT, datefmt=gdm_logger.DATEFMT)
    gdm_log_handler = logging.FileHandler(gdm_log_file)
    gdm_log_handler.setFormatter(gdm_log_formatter)
    gdm_logger.add_handler(gdm_log_handler)
    self.addCleanup(gdm_log_handler.close)
    self.addCleanup(gdm_logger.remove_handler, gdm_log_handler)

  def _test_get_detection_info(self, console_port_name, device_class,
                               persistent_properties):
    """Verifies persistent properties obtained during device detection."""
    name = device_class.__name__.lower()
    device_config = {
        "persistent": {
            "console_port_name": console_port_name,
            "adb_serial": console_port_name,
            "name": f"{name}_detect",
        },
        "options": {},
    }

    self.uut = device_class(
        self.mock_manager,
        device_config=device_config,
        log_directory=self.artifacts_directory,
        log_file_name=name + "_detect.txt")
    self.uut.make_device_ready()
    with mock.patch.object(
        usb_utils,
        "get_usb_hub_info",
        return_value=MOCK_DEVICE_USB_HUB_INFO.copy()):
      self.uut.get_detection_info()
    self.create_example_event_file()  # in case logs are needed
    self.validate_properties(
        self.uut.get_persistent_properties(), persistent_properties,
        "All persistent properties should be retrievable after detect")
    self.uut.close()

  def validate_properties(self,
                          prop_dict,
                          expected_properties,
                          error_msg,
                          exception_property_regexes=()):
    """Verifies that device properties match the expected properties."""
    bad_props = [
        f"{prop}:{value}" for prop, value in prop_dict.items()
        if (gazoo_device_base.ERROR_PREFIX in str(value)
            and "CapabilityNotReadyError" not in str(value))
    ]
    regexes = exception_property_regexes
    filtered_bad_props = [
        prop for prop in bad_props
        if not any(re.search(regex, prop) for regex in regexes)
    ]
    self.assertFalse(
        filtered_bad_props,
        f"{error_msg} but these are not {filtered_bad_props}")

    for prop in expected_properties:
      value = self.uut.get_property(prop)
      self.assertIsNotNone(value, f"Unable to retrieve property {prop}.")
      if isinstance(expected_properties, (dict, immutabledict.immutabledict)):
        self.assertEqual(
            value, expected_properties[prop],
            "Property {} for {} should be {} but is {}".format(
                prop, self.uut.device_type, expected_properties[prop], value))

  def add_parser_get_last_event_mock(self):
    """Mocks out _get_last_event to avoid host dependencies."""
    # pylint: disable=protected-access
    self.real_parser_get_last_event = event_parser_default._get_last_event
    # pylint: enable=protected-access
    parser_get_last_event_patcher = mock.patch.object(
        event_parser_default,
        "_get_last_event",
        side_effect=_mock_get_last_event)
    self.mock_parser_get_last_event = parser_get_last_event_patcher.start()
    self.addCleanup(parser_get_last_event_patcher.stop)

  def create_example_event_file(self):
    """Loads all the example loglines from each filter.

    Generates the events in the events file.
    """
    if not hasattr(self.uut, "event_parser"):
      return
    examples = self._get_filter_examples(
        self.uut._DEFAULT_FILTERS)  # pylint: disable=protected-access
    with open(self.uut.event_file_name, "w") as open_file:
      for example_log in examples:
        self.uut.event_parser.process_line(open_file, example_log)
    self.add_parser_get_last_event_mock()

  def _get_filter_examples(self, default_filters):
    """Loads the filter example loglines."""
    examples = []
    for filter_file in default_filters:

      with open(filter_file) as filter_file:
        a_dict = json.load(filter_file)

      for entry in a_dict["filters"]:
        examples += entry.get("examples", [])
    return examples

  def tearDown(self):
    """Ensures device instance under test is closed."""
    if hasattr(self, "uut") and self.uut:
      self.uut.close()
    super().tearDown()
