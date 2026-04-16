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

import immutabledict

PACKAGE_PATH = "gazoo_device/"

INSTALL_DIRECTORY = os.path.join(os.path.expanduser("~"), "gazoo", "gdm")
LAUNCHER_PATH = os.path.join(os.path.expanduser("~"), "gazoo", "bin", "gdm")

ADB_BIN_PATH_CONFIG = "adb_path"
SEARCHWINDOWSIZE = 2000  # Default size of search window for switchboard methods

DEFAULT_LOG_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "log")
CONFIG_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "conf")
DATA_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "data")
BACKUP_PARENT_DIRECTORY = os.path.join(CONFIG_DIRECTORY, "backup")
BIN_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "bin")
KEYS_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "keys")
VIRTUAL_ENV_DIRECTORY = os.path.join(INSTALL_DIRECTORY, "virtual_env")

REQUIRED_FOLDERS = [
    INSTALL_DIRECTORY, CONFIG_DIRECTORY, DATA_DIRECTORY, DEFAULT_LOG_DIRECTORY,
    BACKUP_PARENT_DIRECTORY, KEYS_DIRECTORY
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

LOGGER_NAME = "gazoo_device_manager"
CLASS_PROPERTY_TYPES = (
    str, int, float, dict, immutabledict.immutabledict, type(None), type)

# TODO(gdm-authors): Revert to 30s once all tests are migrated off monolithic
# GDM dependency.
SWITCHBOARD_PROCESS_START_TIMEOUT_S = 90
SWITCHBOARD_PROCESS_COMMAND_CONSUMPTION_TIMEOUT_S = 6
SWITCHBOARD_PROCESS_POLLING_INTERVAL_S = 0.1

KEY_PACKAGE_NAME = "gazoo_device_controllers"
