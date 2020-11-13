"""Example of a primary device controller.

This example targets a generic Linux device accessible over SSH.
Assumptions for this device controller to work:
- The target device is running Linux.
- The device responds to ping and can be SSHed into.
- SSH does not require a password. You may need to set up passwordless
  SSH access via ssh-copy-id.
- The SSH username is "root". If not, change the value of SSH_USERNAME.

To try it out:
- Check out the gazoo-device repository:
  `git clone https://github.com/google/gazoo-device.git; cd gazoo-device`
- Connect a Linux device to your host and ensure that all of the
  assumptions above are satisfied.
- Comment out the 2 detection criteria in DETECT_MATCH_CRITERIA
  (see the instructions there) and save the file.
- Create a virtual environment:
  `python3 -m virtualenv gdm_venv`
- Install the gazoo-device from the checked out source code:
  `gdm_venv/bin/pip install -e ./`
- Try detecting your device:
  `gdm_venv/bin/python gdm detect --static_ips=<IP_of_device>`
- Try the GDM CLI with your device:
  ```
  gdm_venv/bin/python gdm man linuxexample
  gdm_venv/bin/python gdm devices
  # Use your device name (from output of "gdm devices") instead of "linuxexample-1234" below
  gdm_venv/bin/python gdm issue linuxexample-1234 --help
  gdm_venv/bin/python gdm issue linuxexample-1234 - shell "echo 'foo'"
  gdm_venv/bin/python gdm get-prop linuxexample-1234
  ```
"""
from gazoo_device import decorators
from gazoo_device import detect_criteria
from gazoo_device import errors
from gazoo_device import gdm_logger
from gazoo_device.base_classes import ssh_device

logger = gdm_logger.get_gdm_logger()

COMMANDS = {
    "FIRMWARE_VERSION": "uname -r",
    # Commands prefixed with "INFO_" will run during detection.
    # Their return values will be stored in the persistent config file.
    # The values will be available in
    # self.props["persistent_identifiers"][<property>].
    # In this case, the property name will be "hardware_architecture".
    "INFO_HARDWARE_ARCHITECTURE": "uname -m",
    # This only works on Raspberry Pi.
    "INFO_MODEL": "cat /sys/firmware/devicetree/base/model 2>/dev/null",
    # This only works on Raspberry Pi.
    "INFO_SERIAL_NUMBER": 'cat /proc/cpuinfo | grep "Serial" '
                          '| cut -d" " -f 2',
    "REBOOT": "reboot"
}
REGEXES = {}
TIMEOUTS = {}
SSH_USERNAME = "root"  # You may need to change this.


# Note: the device controller class name must not end in "Base" or
# "Device" to be automatically detected by GDM. Class names ending in
# "Base" or "Device" are interpreted as base classes.
class LinuxExample(ssh_device.SshDevice):
    """Example primary device controller for a generic Linux device."""
    _COMMUNICATION_KWARGS = {
        **ssh_device.SshDevice._COMMUNICATION_KWARGS,
        "username": SSH_USERNAME
    }
    # Device controllers must correspond to a single device type.
    # Therefore, detect criteria must uniquely identify a single device
    # type. I'm cheating in this example as it is generic.
    # To avoid interference with more specific Linux device controllers
    # (such as Raspberry Pi), this match is always set to False.
    # Comment out the 2 criteria below to enable detection of generic
    # Linux devices.
    DETECT_MATCH_CRITERIA = {
        # Comment these 2 lines out
        detect_criteria.SSH_QUERY.is_rpi: True,
        detect_criteria.SSH_QUERY.is_unifi: True
    }
    DEVICE_TYPE = "linuxexample"

    def __init__(self,
                 manager,
                 device_config,
                 log_file_name=None,
                 log_directory=None):
        super().__init__(manager,
                         device_config,
                         log_file_name=log_file_name,
                         log_directory=log_directory)
        self._commands.update(COMMANDS)
        self._regexes.update(REGEXES)
        self._timeouts.update(TIMEOUTS)

    @decorators.LogDecorator(logger)
    def factory_reset(self):
        """Resets the device to its factory default settings.

        Raises:
            NotImplementedError: there's no command to factory reset a
                                 generic Linux device.
        """
        raise NotImplementedError("Not really possible for a generic "
                                  "Linux device.")

    @decorators.DynamicProperty
    def firmware_version(self) -> str:
        """Returns the firmware version of the device."""
        return self.shell(self.commands["FIRMWARE_VERSION"])

    @decorators.LogDecorator(logger)
    def get_detection_info(self):
        """Gets the persistent and optional attributes of a device.

        Returns:
            tuple: (persistent properties dict, optional properties dict)
        """
        persistent_props, optional_props = super().get_detection_info()
        # Note that setting the "serial_number" persistent property is
        # required to generate the GDM name for the device.
        # If the device doesn't expose the serial number, set
        # self.props["persistent_identifiers"]["serial_number"] to any
        # unique identifier such as a MAC address of an interface.
        if not persistent_props.get("serial_number"):
            persistent_props["serial_number"] = "12345678"
        # Setting the "model" persistent property is also required.
        # Typical values are "Production", "Development", "Prototype".
        if not persistent_props.get("model"):
            persistent_props["model"] = "Production"

        return persistent_props, optional_props

    @decorators.PersistentProperty
    def hardware_architecture(self) -> str:
        """Returns the hardware architecture (such as "x86_64").

        This property is not required by GDM. It's an example of a
        persistent property which is populated during detection.
        """
        return self.props["persistent_identifiers"][
            "hardware_architecture"]

    @decorators.PersistentProperty
    def platform(self) -> str:
        """Returns the platform of the device."""
        return "new_top_secret_platform"

    @decorators.LogDecorator(logger)
    def reboot(self, no_wait=False, method="shell"):
        """Issues a soft reboot command.

        Args:
            no_wait (bool): flag indicating whether reboot verification
                            should be skipped. If False, blocks until
                            reboot completion.
            method (str): reboot technique to use.

        Raises:
            GazooDeviceError: if the provided reboot method is not supported.
        """
        if method not in ["shell"]:
            raise errors.GazooDeviceError(
                "{} reboot failed. Unsupported reboot method {!r} requested."
                .format(self.name, method))
        self.shell(self.commands["REBOOT"])
        if not no_wait:
            self._verify_reboot()
