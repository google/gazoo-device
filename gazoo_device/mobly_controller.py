"""Methods for mobly controller.

Imported into init.

To use:
import gazoo_device
from mobly import base_test

class Test(base_test.TestCase):
  def set_up_class(self):
    self.devices = self.register_controller(gazoo_device)


  def setup_test(self):
    for device in self.devices:
      device.start_new_log(log_name_prefix=self.current_test_info.name)

  def teardown_test(self):
    for device in self.devices:
      device.make_device_ready()
"""
import logging
import os
from typing import Any, Dict, List, Sequence

from gazoo_device import custom_types
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device import manager

# Device properties for gazoo device analytics.
_DEVICE_PROPS = ("name", "device_type", "model", "platform", "serial_number",
                 "wifi_mac_address", "firmware_version", "firmware_branch",
                 "firmware_type", "alias", "communication_address",
                 "secondary_communication_address", "build_date",
                 "initial_code_name")
_LOGGER = gdm_logger.get_logger()
_MANAGER_INSTANCE = None


def _set_auxiliary_props(properties: Dict[str, Any], device_name: str):
  """Sets props on device instance to the values in the config.

  Label is translated to Alias and dimensions are left out.

  Args:
    properties: Dictionary of device properties and their values.
    device_name: Id of the device instance.
  """
  for prop_name, value in properties.items():
    if prop_name in ["id", "dimensions"]:
      continue
    elif prop_name == "label":
      _MANAGER_INSTANCE.set_prop(device_name, "alias", value)
    else:
      try:
        _MANAGER_INSTANCE.set_prop(device_name, prop_name, value)
      except errors.DeviceError:
        _LOGGER.warning("%s unsettable for %s", prop_name, device_name)


def create(configs: List[Dict[str, Any]]) -> List[custom_types.Device]:
  """Creates gazoo device instances and returns them."""
  # log_path is set by mobly on logging in base_test
  log_path_directory = getattr(logging, "log_path", "/tmp/logs")
  gdm_log_file = os.path.join(log_path_directory, "gdm.txt")
  global _MANAGER_INSTANCE
  _MANAGER_INSTANCE = manager.Manager(
      log_directory=log_path_directory,
      gdm_log_file=gdm_log_file,
      stdout_logging=False)
  devices = []
  for entry in configs:
    name = entry["id"]
    _set_auxiliary_props(entry, name)
    device = _MANAGER_INSTANCE.create_device(name)
    devices.append(device)
  return devices


def get_info(devices: Sequence[custom_types.Device]) -> List[Dict[str, Any]]:
  """Returns persistent info and firmware version for each device."""
  info = []
  for device in devices:
    props = {}
    for device_prop in _DEVICE_PROPS:
      try:
        props[device_prop] = device.get_property(device_prop, raise_error=True)
      except AttributeError:
        props[device_prop] = "Undefined"
    info.append(props)
  return info


def destroy(devices: List[custom_types.Device]) -> None:
  """Closes all created devices and manager."""
  for device in devices:
    device.close()
  global _MANAGER_INSTANCE
  _MANAGER_INSTANCE.close()
  _MANAGER_INSTANCE = None
