"""DC2200 LED driver from Thorlabs.

SCPI programming manual:
https://www.thorlabs.com/_sd.cfm?fileName=MTN005097-D03.pdf&partNumber=DC2200

Product:
https://www.thorlabs.com/thorproduct.cfm?partnumber=DC2200
"""
from typing import Any

from gazoo_device import custom_types
from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device import mobly_controller
from gazoo_device import version
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.capabilities import led_driver_default
from gazoo_device.detect_criteria import usb_detect_criteria
from gazoo_device.switchboard.communication_types import usb_comms
from gazoo_device.utility import usb_utils
import immutabledict


logger = gdm_logger.get_logger()


class DC2200(auxiliary_device.AuxiliaryDevice):
  """DC2200 LED driver controller."""

  COMMUNICATION_TYPE = usb_comms.UsbComms
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict({
      usb_detect_criteria.UsbQuery.VENDOR_PRODUCT_ID: "1313:80c8",
      usb_detect_criteria.UsbQuery.PRODUCT_NAME: "DC2200",
  })
  DEVICE_TYPE = "dc2200"
  _MODEL = "dc2200"

  @decorators.LogDecorator(logger)
  def get_console_configuration(self) -> None:
    """Returns None. Console is not supported because there's no Switchboard."""
    del self  # Unused because console is not supported.
    return None

  def get_detection_info(
      self
  ) -> tuple[custom_types.PersistentConfigsDict,
             custom_types.OptionalConfigsDict]:
    """Gets the persistent and optional attributes of a device during setup.

    Returns:
      Dictionaries of persistent attributes, and optional attributes.
    """
    persistent_dict = self.props["persistent_identifiers"]
    persistent_dict["serial_number"] = persistent_dict["console_port_name"]
    persistent_dict["model"] = self._MODEL
    optional_dict = {}
    return persistent_dict, optional_dict

  @classmethod
  def is_connected(
      cls, device_config: custom_types.ManagerDeviceConfigDict) -> bool:
    """Determines if the device is connected (reachable).

    Args:
      device_config: Dictionary containing "persistent" properties.

    Returns:
      True if the device is connected, False otherwise.
    """
    device = usb_utils.get_usb_device_from_serial_number(
        device_config["persistent"]["console_port_name"])
    return device is not None

  @decorators.CapabilityDecorator(led_driver_default.LedDriverDefault)
  def led_driver(self) -> led_driver_default.LedDriverDefault:
    """LED driver capability for DC2200."""
    return self.lazy_init(
        led_driver_default.LedDriverDefault,
        device_name=self.name,
        serial_number=self.serial_number)


_DeviceClass = DC2200
_COMMUNICATION_TYPE = _DeviceClass.COMMUNICATION_TYPE.__name__
# For Mobly controller integration.
MOBLY_CONTROLLER_CONFIG_NAME = (
    mobly_controller.get_mobly_controller_config_name(_DeviceClass.DEVICE_TYPE))
create = mobly_controller.create
destroy = mobly_controller.destroy
get_info = mobly_controller.get_info
get_manager = mobly_controller.get_manager


def export_extensions() -> dict[str, Any]:
  """Exports device class and capabilities to act as a GDM extension package."""
  return {
      "auxiliary_devices": [_DeviceClass],
      "detect_criteria": immutabledict.immutabledict({
          _COMMUNICATION_TYPE: usb_detect_criteria.USB_QUERY_DICT,
      }),
  }

__version__ = version.VERSION
