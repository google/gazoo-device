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

"""CONFIG FILE."""
import os.path
from gazoo_device import data_types
import immutabledict

PACKAGE_PATH = os.path.dirname(os.path.abspath(__file__))

INSTALL_DIRECTORY = os.path.join(os.path.expanduser("~"), "gazoo", "gdm")
LAUNCHER_PATH = os.path.join(os.path.expanduser("~"), "gazoo", "bin", "gdm")

ADB_BIN_PATH_CONFIG = "adb_path"
SEARCHWINDOWSIZE = 2000  # Default size of search window for switchboard methods

DEFAULT_LOG_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "log")
CONFIG_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "conf")
DATA_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "data")
BACKUP_PARENT_DIRECTORY = os.path.join(CONFIG_DIRECTORY, "backup")
BOTO_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "botos")
BIN_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "bin")
KEYS_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "keys")
PTY_PROCESS_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "pty_proc")
DETOK_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "detok")
VIRTUAL_ENV_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "virtual_env")

REQUIRED_FOLDERS = [
    INSTALL_DIRECTORY, CONFIG_DIRECTORY, DATA_DIRECTORY, DEFAULT_LOG_DIRECTORY,
    BACKUP_PARENT_DIRECTORY, BOTO_DIRECTORY, KEYS_DIRECTORY, DETOK_DIRECTORY
]

DEFAULT_DEVICE_FILE = os.path.join(CONFIG_DIRECTORY, "devices.json")
DEFAULT_OPTIONS_FILE = os.path.join(CONFIG_DIRECTORY, "device_options.json")
DEFAULT_TESTBEDS_FILE = os.path.join(CONFIG_DIRECTORY, "testbeds.json")
DEFAULT_GDM_CONFIG_FILE = os.path.join(CONFIG_DIRECTORY, "gdm.json")
DEFAULT_LOG_FILE = os.path.join(DEFAULT_LOG_DIRECTORY, "gdm.txt")

DEVICES_KEYS = ["devices", "other_devices"]
OPTIONS_KEYS = ["device_options", "other_device_options"]
TESTBED_KEYS = ["testbeds"]

HUB_OPTION_ATTRIBUTES = ["alias"]
DEVICE_OPTION_ATTRIBUTES = [
    "alias", "power_switch", "power_port", "usb_hub", "location", "usb_port"
]

CLASS_PROPERTY_TYPES = (str, int, dict, type(None))

_BUILT_IN_EXTENSION_PACKAGE_NAME = "gazoo_device_controllers"
KEYS = immutabledict.immutabledict({
    "raspberrypi3_ssh_key": data_types.KeyInfo(
        file_name="raspberrypi3_ssh_key",
        type=data_types.KeyType.SSH,
        package=_BUILT_IN_EXTENSION_PACKAGE_NAME),
    "raspberrypi3_ssh_key_public": data_types.KeyInfo(
        file_name="raspberrypi3_ssh_key.pub",
        type=data_types.KeyType.SSH,
        package=_BUILT_IN_EXTENSION_PACKAGE_NAME),
    "unifi_switch_ssh_key": data_types.KeyInfo(
        file_name="unifi_switch_ssh_key",
        type=data_types.KeyType.SSH,
        package=_BUILT_IN_EXTENSION_PACKAGE_NAME),
    "unifi_switch_ssh_key_public": data_types.KeyInfo(
        file_name="unifi_switch_ssh_key.pub",
        type=data_types.KeyType.SSH,
        package=_BUILT_IN_EXTENSION_PACKAGE_NAME),
})
