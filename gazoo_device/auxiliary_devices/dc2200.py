"""DC2200 LED driver from Thorlabs.

SCPI programming manual:
https://www.thorlabs.com/_sd.cfm?fileName=MTN005097-D03.pdf&partNumber=DC2200

Product:
https://www.thorlabs.com/thorproduct.cfm?partnumber=DC2200
"""
from typing import Tuple

from gazoo_device import custom_types
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.capabilities import led_driver_default
from gazoo_device.utility import usb_utils
import immutabledict


logger = gdm_logger.get_logger()


class DC2200(auxiliary_device.AuxiliaryDevice):
  """DC2200 LED driver controller."""

  COMMUNICATION_TYPE = "UsbComms"
  DETECT_MATCH_CRITERIA = immutabledict.immutabledict({
      detect_criteria.UsbQuery.VENDOR_PRODUCT_ID: "1313:80c8",
      detect_criteria.UsbQuery.PRODUCT_NAME: "DC2200",
  })
  DEVICE_TYPE = "dc2200"
  _OWNER_EMAIL = "gdm-authors@google.com"
  _MODEL = "dc2200"

  @decorators.LogDecorator(logger)
  def get_console_configuration(self) -> None:
    """Returns None. Console is not supported because there's no Switchboard."""
    del self  # Unused because console is not supported.
    return None

  def get_detection_info(
      self
  ) -> Tuple[custom_types.PersistentConfigsDict,
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
