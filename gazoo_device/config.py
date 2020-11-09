# Copyright 2020 Google LLC
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
from __future__ import absolute_import
import os

SEARCHWINDOWSIZE = 2000  # Used as default size of searchwindow used in switchboard functions
CUR_DIRECTORY = "/gazoo/gdm"
TEMP_DIRECTORY = os.path.join(os.environ["HOME"], "gdm")
if os.path.exists(CUR_DIRECTORY):
    GAZOO_DEVICE_DIRECTORY = CUR_DIRECTORY
else:
    GAZOO_DEVICE_DIRECTORY = TEMP_DIRECTORY
ADB_BIN_PATH_CONFIG = "adb_path"

PACKAGE_PATH = os.path.dirname(os.path.abspath(__file__))
BIN_PATH = os.path.join(PACKAGE_PATH, "bin")
DEFAULT_LOG_DIRECTORY = os.path.join(GAZOO_DEVICE_DIRECTORY, "log")
CONFIG_DIRECTORY = os.path.join(GAZOO_DEVICE_DIRECTORY, "conf")
FILTER_DIRECTORY = os.path.join(PACKAGE_PATH, "filters")
TTY_DIRECTORY = os.path.join(GAZOO_DEVICE_DIRECTORY, "tty")
DETOK_DIRECTORY = os.path.join(GAZOO_DEVICE_DIRECTORY, "detok")
BACKUP_PARENT_DIRECTORY = os.path.join(CONFIG_DIRECTORY, "backup")
BOTO_DIRECTORY = os.path.join(GAZOO_DEVICE_DIRECTORY, "botos")
KEYS_DIRECTORY = os.path.join(GAZOO_DEVICE_DIRECTORY, "keys")
BUILD_DEFAULTS_DIRECTORY = os.path.join(PACKAGE_PATH, "build_defaults")

DEFAULT_DEVICE_FILE = os.path.join(CONFIG_DIRECTORY, "devices.json")
DEFAULT_OPTIONS_FILE = os.path.join(CONFIG_DIRECTORY, "device_options.json")
DEFAULT_TESTBEDS_FILE = os.path.join(CONFIG_DIRECTORY, "testbeds.json")
DEFAULT_GDM_CONFIG_FILE = os.path.join(CONFIG_DIRECTORY, "gdm.json")

DEFAULT_LOG_FILE = os.path.join(DEFAULT_LOG_DIRECTORY, "gdm.txt")

DEFAULT_BUILD_INFO_FILE = os.path.join(BUILD_DEFAULTS_DIRECTORY, "info.json")
DEVICE_SCRIPTS_FOLDER = os.path.join(PACKAGE_PATH, "device_scripts")

REQUIRED_FOLDERS = [
    GAZOO_DEVICE_DIRECTORY,
    CONFIG_DIRECTORY,
    TTY_DIRECTORY,
    DEFAULT_LOG_DIRECTORY,
    DETOK_DIRECTORY,
    BACKUP_PARENT_DIRECTORY,
    BOTO_DIRECTORY,
    KEYS_DIRECTORY
]

KEY_FLAVOR_SSH = "ssh"
KEY_FLAVOR_API = "api"
# Keys used by GDM, such as private SSH keys. Format of entries:
# "key_name": {"remote_filename": "foo_key",
#              "flavor": KEY_FLAVOR_API or KEY_FLAVOR_SSH,
#              "local_path": os.path.join(KEYS_DIRECTORY, "foo_key")}
KEYS = {
    "raspbian":
        {"remote_filename": "raspberrypi3_ssh_key",
         "local_path": os.path.join(KEYS_DIRECTORY, "raspberrypi3_ssh_key"),
         "flavor": KEY_FLAVOR_SSH},
    "raspbian_public":
        {"remote_filename": "raspberrypi3_ssh_key.pub",
         "local_path": os.path.join(KEYS_DIRECTORY, "raspberrypi3_ssh_key.pub"),
         "flavor": KEY_FLAVOR_SSH},
    "unifi_switch":
        {"remote_filename": "unifi_switch_ssh_key",
         "local_path": os.path.join(KEYS_DIRECTORY, "unifi_switch_ssh_key"),
         "flavor": KEY_FLAVOR_SSH},
    "unifi_switch_public":
        {"remote_filename": "unifi_switch_ssh_key.pub",
         "local_path": os.path.join(KEYS_DIRECTORY, "unifi_switch_ssh_key.pub"),
         "flavor": KEY_FLAVOR_SSH}
}


REQUIRED_FILES = [
    DEFAULT_DEVICE_FILE,
    DEFAULT_OPTIONS_FILE,
    DEFAULT_TESTBEDS_FILE,
    DEFAULT_GDM_CONFIG_FILE,
    DEFAULT_LOG_FILE,
    DEFAULT_BUILD_INFO_FILE
]

REQUIRED_HUB_ENTRY_ATTRIBUTES = [
    "device_type", "model", "serial_number"
]

HUB_OPTION_ATTRIBUTES = [
    "alias"
]

REQUIRED_DEVICE_ENTRY_ATTRIBUTES = [
    "device_type", "model", "serial_number"
]

DEVICE_OPTION_ATTRIBUTES = [
    "alias", "power_switch", "power_port", "usb_hub", "location", "usb_port"
]

DEVICES_KEYS = ["devices", "other_devices"]
OPTIONS_KEYS = ["device_options", "other_device_options"]
TESTBED_KEYS = ["testbeds"]

DEFAULT_BOTO = os.path.join(os.environ["HOME"], ".boto")

CLASS_PROPERTY_TYPES = (str, int, dict, type(None))
