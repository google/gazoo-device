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

"""Device logs for raspbian devices."""
from gazoo_device.tests.unit_tests.utils import ssh_device_logs

generate_command = ssh_device_logs.generate_command
generate_response = ssh_device_logs.generate_response
make_device_responses = ssh_device_logs.make_device_responses

_RESPONSES = [{
    "cmd": "cat /proc/device-tree/model",
    "resp": "Raspberry Pi 3 Model B Rev 1.1",
    "code": 0,
}, {
    "cmd": "cat /etc/os-release",
    "resp": """
        PRETTY_NAME="Raspbian GNU/Linux 10 (buster)"
        NAME="Raspbian GNU/Linux"
        VERSION_ID="10"
        VERSION="10 (buster)"
        VERSION_CODENAME=buster
        ID=raspbian
        ID_LIKE=debian
        HOME_URL="http://www.raspbian.org/"
        SUPPORT_URL="http://www.raspbian.org/RaspbianForums"
        BUG_REPORT_URL="http://www.raspbian.org/RaspbianBugs""",
    "code": 0,
}, {
    "cmd": "cat /proc/cpuinfo",
    "resp": """
        processor	: 0
        model name	: ARMv7 Processor rev 4 (v7l)
        BogoMIPS	: 38.40
        Features	: half thumb fastmult vfp edsp neon vfpv3 tls vfpv4 idiva idivt vfpd32 lpae evtstrm crc32
        CPU implementer	: 0x41
        CPU architecture: 7
        CPU variant	: 0x0
        CPU part	: 0xd03
        CPU revision	: 4

        processor	: 1
        model name	: ARMv7 Processor rev 4 (v7l)
        BogoMIPS	: 38.40
        Features	: half thumb fastmult vfp edsp neon vfpv3 tls vfpv4 idiva idivt vfpd32 lpae evtstrm crc32
        CPU implementer	: 0x41
        CPU architecture: 7
        CPU variant	: 0x0
        CPU part	: 0xd03
        CPU revision	: 4

        processor	: 2
        model name	: ARMv7 Processor rev 4 (v7l)
        BogoMIPS	: 38.40
        Features	: half thumb fastmult vfp edsp neon vfpv3 tls vfpv4 idiva idivt vfpd32 lpae evtstrm crc32
        CPU implementer	: 0x41
        CPU architecture: 7
        CPU variant	: 0x0
        CPU part	: 0xd03
        CPU revision	: 4

        processor	: 3
        model name	: ARMv7 Processor rev 4 (v7l)
        BogoMIPS	: 38.40
        Features	: half thumb fastmult vfp edsp neon vfpv3 tls vfpv4 idiva idivt vfpd32 lpae evtstrm crc32
        CPU implementer	: 0x41
        CPU architecture: 7
        CPU variant	: 0x0
        CPU part	: 0xd03
        CPU revision	: 4

        Hardware	: BCM2835
        Revision	: a020d3
        Serial		: 000000005ee230c2
        Model		: Raspberry Pi 3 Model B Plus Rev 1.3""",
    "code": 0,
}, {
    "cmd": "uname -r",
    "resp": "4.19.75-v7+",
    "code": 0,
}, {
    "cmd": "sudo bash -c 'echo \"--- GDM Log Marker ---\" >> /var/log/syslog'",
    "resp": "",
    "code": 0,
}, {
    "cmd": "sudo systemctl --wait is-system-running",
    "resp": "running",
    "code": 0,
}, {
    "cmd": "Hello",
    "resp": "bash: Hello: command not found",
    "code": 0,
}, {
    "cmd": "echo 'GDM-HELLO'",
    "resp": "GDM-HELLO",
    "code": 0,
}, {
    "cmd": "echo 'wlan0'",
    "resp": "wlan0",
    "code": 0,
}, {
    "cmd": "ip address show wlan0",
    "resp": """
        3: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast
           state UP group default qlen 1000
           link/ether b8:27:eb:ae:7c:57 brd ff:ff:ff:ff:ff:ff
           inet 192.168.50.199/24 brd 192.168.50.255 scope global wlan0
           valid_lft forever preferred_lft forever
           inet6 fe80::319b:325e:d0f2:4d78/64 scope link
           valid_lft forever preferred_lft forever""",
    "code": 0,
}, {
    "cmd": "sleep 10 &",
    "resp": "",
    "code": 0,
}, {
    "cmd": "echo 'gdm hello'",
    "resp": "gdm hello",
    "code": 0,
}]

DEFAULT_BEHAVIOR = ssh_device_logs.make_device_responses(_RESPONSES)
