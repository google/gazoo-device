"""Allows for triggering GPIO lines on FTDI based boards."""
import time

import pylibftdi


class FtdiButtons:
  """Allows for triggering GPIO lines on FTDI based boards."""

  def __init__(self, ftdi_serial_number, button_map, polarity=False):
    """Initializes the FtdiButtons with the properties provided.

    The ftdi_serial_number is needed to unique identify the FTDI device
    to control as there may be more than one FTDI device available. The
    button map defines the interfaces and pin (bit) to set for each button
    and should look like this:
    some_button_map = {"a_button": {"interface": 1, "pin": 3},
                       "b_button": {"interface": 2, "pin": 5}}

    Args:
        ftdi_serial_number (str): FTDI serial number to use
        button_map (dict): button to pin (bit) mapping.
        polarity (bool): GPIO pin polarity to use (True to push button).
    """
    self._button_map = button_map
    self._button_down = {}
    self._ftdi_serial_number = ftdi_serial_number
    self._polarity = polarity
    self._sub_process = None
    self._bb_map = {}
    self._bitbang_device_init = False
    self.bitbang_device_init()

  def __del__(self):
    self.close()

  def close(self):
    """Release any held buttons on close."""
    for button in list(self._button_down):
      self.release(button)

    for interface in self._bb_map:
      ftdi_device = self._bb_map[interface]
      ftdi_device.close()

    self._bb_map.clear()
    self._bitbang_device_init = False

  def is_valid(self, button):
    """Return True if button specified is in the list of valid buttons.

    Args:
        button (str): button identifier.

    Returns:
        bool: True if button specified is in button map provided
    """

    return button in list(self._button_map.keys())

  def bitbang_device_init(self):
    """Creates BitBangDevices for each button and initializes to 'off'."""
    for button in list(self._button_map.keys()):
      interface = self._button_map[button]["interface"]
      pin = self._button_map[button]["pin"]

      if interface not in self._bb_map:
        ftdi_device = pylibftdi.BitBangDevice(
            device_id=self._ftdi_serial_number,
            interface_select=interface,
            direction=(1 << pin))
        ftdi_device.port = 0 if self._polarity else 255
        self._bb_map[interface] = ftdi_device
      else:
        self._bb_map[interface].direction |= (1 << pin)
      self._button_down[button] = False

    self._bitbang_device_init = True

  def press(self, button, wait=0.0):
    """Presses button and waits for the time specified.

    Note: You must call release or close to release the button later.

    Args:
        button (str): identify which button to press
        wait (float): seconds to wait before returning

    Raises:
        ValueError: invalid button or wait given.
    """
    if not self._bitbang_device_init:
      self.bitbang_device_init()
    if button not in self._button_map:
      raise ValueError("Invalid button {} specified".format(button))
    elif wait < 0.0:
      raise ValueError("Invalid wait {} specified".format(wait))
    elif not self._button_down[button]:
      self._gpio(button, -1, active_high=self._polarity)
      time.sleep(wait)

  def click(self, button, duration=.5):
    """Presses the button specified and holds it for the specified duration.

    Args:
        button (str): button to click.
        duration (float): seconds to wait before releasing the button.

    Raises:
        ValueError: invalid button or duration given.
    """
    if not self._bitbang_device_init:
      self.bitbang_device_init()
    if button not in self._button_map:
      raise ValueError("Invalid button {} specified".format(button))
    elif duration <= 0.0:
      raise ValueError("Invalid duration {} specified".format(duration))
    else:
      self._gpio(button, duration, active_high=self._polarity)

  def release(self, button):
    """Releases the button specified if it was previously pressed.

    Args:
        button (str): button to click.

    Raises:
        ValueError: invalid button given.
    """
    if not self._bitbang_device_init:
      self.bitbang_device_init()
    if button not in self._button_map:
      raise ValueError("Invalid button {} specified".format(button))
    elif self._button_down[button]:
      self._gpio(button, -1, active_high=self._polarity)

  def read_pin(self, interface, pin):
    """Returns True if the bit is high for the given pin, False otherwise.

    Args:
        interface (int): the port on the FTDI chip containing the GPIO
        pin (int): the bit representing the GPIO to read
    Return:
       bool: True if pin is high, False if low.
    """
    if not self._bitbang_device_init:
      self.bitbang_device_init()
    return (self._bb_map[interface].port & (1 << pin)) != 0

  def valid_buttons(self):
    """Returns a list of valid button names.

    Returns:
        list: A list of valid button name strings
    """
    return list(self._button_map.keys())

  def _gpio(self, button, duration, active_high):
    """Drive the GPIO of the button specified for the duration provided.

    Args:
        button (str): button to be toggled
        duration (float): seconds to wait between the two toggles. If
          negative, only one toggle will be performed (either a press or
          release).
        active_high (bool): drive the pin high if True otherwise drive
          active_low.
    """
    if not self._bitbang_device_init:
      self.bitbang_device_init()
    interface = self._button_map[button]["interface"]
    bb = self._bb_map[interface]
    self.__toggle(button, bb, active_high)
    if duration >= 0.0:
      time.sleep(duration)
      self.__toggle(button, bb, active_high)

  def __toggle(self, button, bb, active_high):
    """Toggles the button specified based on its previous state.

    Args:
        button (str): button to be toggled
        bb (BitBangDevice): performs the toggle.
        active_high (bool): drive the pin high if True, otherwise drive
          active_low.
    """
    if not self._bitbang_device_init:
      self.bitbang_device_init()
    pin = self._button_map[button]["pin"]
    if self._button_down[button]:
      # Release button
      if active_high:
        self.__clear_pin(bb, pin)
      else:
        self.__set_pin(bb, pin)
      self._button_down[button] = False
    else:
      # Set button
      if active_high:
        self.__set_pin(bb, pin)
      else:
        self.__clear_pin(bb, pin)
      self._button_down[button] = True

  @staticmethod
  def __clear_pin(bb, pin):
    """Clear the bit of the given pin.

    Args:
        bb (BitBangDevice): performs the work
        pin (int): the bit representing the GPIO to clear
    """
    bb.port &= 255 ^ (1 << pin)

  @staticmethod
  def __set_pin(bb, pin):
    """Sets the bit for the given pin.

    Args:
        bb (BitBangDevice): performs the work
        pin (int): the bit representing the GPIO to clear
    """
    bb.port |= (1 << pin)
