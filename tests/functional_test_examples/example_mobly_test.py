"""Example device test with GDM + Mobly."""
import logging
import os
from mobly import asserts
from mobly import base_test
from gazoo_device import manager

GAZOO_DEVICE_CONTROLLER = "GazooDevice"


class ExampleTest(base_test.BaseTestClass):
    """Example device test with GDM + Mobly."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = None
        self.device = None
        self.devices = []

    def setup_class(self):
        super().setup_class()
        logging.getLogger().setLevel(logging.INFO)
        self.manager = manager.Manager(
            log_directory=self.log_path,
            gdm_log_file=os.path.join(self.log_path, "gdm.log"),
            stdout_logging=False)  # Avoid log duplication with Mobly's stdout log handler

    def teardown_class(self):
        self.manager.close()
        super().teardown_class()

    def setup_test(self):
        """Instantiates a device controller to be used by tests."""
        super().setup_test()
        gazoo_device_names = self.get_gazoo_device_configs()
        self.devices = [self.manager.create_device(device_name)
                        for device_name in gazoo_device_names]
        logging.info("Created devices for test: %s",
                     [device.name for device in self.devices])
        self.device = self.devices[0]

    def teardown_test(self):
        """Closes each device."""
        for device in getattr(self, "devices", []):
            device.close()
        super().teardown_test()

    def get_gazoo_device_configs(self):
        """Extracts Gazoo devices from the testbed.

        Raises:
            RuntimeError: the testbed config does not contain any "GazooDevice" controller entries.

        Returns:
            list[str]: names of all GazooDevices in the testbed.
        """
        gazoo_device_configs = []
        for controller, device_name_list in self.controller_configs.items():
            if controller == GAZOO_DEVICE_CONTROLLER:
                for device_name in device_name_list:
                    gazoo_device_configs.append(device_name)
        if not gazoo_device_configs:
            raise RuntimeError("The testbed config does not have any {} controller entries"
                               .format(GAZOO_DEVICE_CONTROLLER))
        return gazoo_device_configs

    def test_example(self):
        for device in self.devices:
            device.reboot()
            asserts.assert_true(device.is_connected(),
                                "Device {} did not come back up after reboot".format(device.name))
