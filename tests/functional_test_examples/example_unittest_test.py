"""Example device test with unittest + Mobly."""
import logging
import unittest
from gazoo_device import manager


class ExampleTest(unittest.TestCase):
    """Example device test with unittest + Mobly."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logging.getLogger().setLevel(logging.INFO)
        cls.manager = manager.Manager()

    @classmethod
    def tearDownClass(cls):
        cls.manager.close()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.device = self.manager.create_device("raspberrypi-1234")
        logging.info("Created device for test: %s", self.device.name)

    def tearDown(self):
        self.device.close()
        super().tearDown()

    def test_example(self):
        self.device.reboot()
        self.assertTrue(self.device.is_connected(),
                        "Device {} did not come back up after reboot"
                        .format(self.device.name))
