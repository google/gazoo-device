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

"""Device logs for debian devices."""
from gazoo_device.tests.unit_tests.utils import ssh_device_logs

generate_command = ssh_device_logs.generate_command
generate_response = ssh_device_logs.generate_response
make_device_responses = ssh_device_logs.make_device_responses

_RESPONSES = (
    {
        "cmd": "cat /etc/os-release",
        "resp": """
        PRETTY_NAME="Debian GNU/Linux rodete"
        NAME="Debian GNU/Linux"
        VERSION_ID="rodete"
        VERSION="12 (rodete)"
        VERSION_CODENAME=rodete
        ID=debian
        HOME_URL="https://www.debian.org/"
        SUPPORT_URL="https://www.debian.org/"
        BUG_REPORT_URL="https://www.debian.org/""",
        "code": 0,
    },
    {
        "cmd": "cat /proc/cpuinfo",
        "resp": """
        processor       : 0
        vendor_id       : GenuineIntel""",
        "code": 0,
    },
    {
        "cmd": "uname -r",
        "resp": "6.1.20",
        "code": 0,
    },
    {
        "cmd": (
            "sudo bash -c 'echo \"--- GDM Log Marker ---\" >> /var/log/syslog'"
        ),
        "resp": "",
        "code": 0,
    },
    {
        "cmd": "sudo systemctl --wait is-system-running",
        "resp": "running",
        "code": 0,
    },
    {
        "cmd": "Hello",
        "resp": "bash: Hello: command not found",
        "code": 0,
    },
    {
        "cmd": "echo 'GDM-HELLO'",
        "resp": "GDM-HELLO",
        "code": 0,
    },
    {
        "cmd": "echo 'wlan0'",
        "resp": "wlan0",
        "code": 0,
    },
    {
        "cmd": "ip address show wlan0",
        "resp": 'Device "wlan0" does not exist.',
        "code": 0,
    },
    {
        "cmd": "sleep 10 &",
        "resp": "",
        "code": 0,
    },
    {
        "cmd": "echo 'gdm hello'",
        "resp": "gdm hello",
        "code": 0,
    },
)

DEFAULT_BEHAVIOR = ssh_device_logs.make_device_responses(_RESPONSES)
