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

"""Device logs for RPi Matter devices."""
from gazoo_device.tests.unit_tests.utils import raspbian_device_logs
from gazoo_device.tests.unit_tests.utils import ssh_device_logs
from immutabledict import immutabledict

make_device_responses = ssh_device_logs.make_device_responses

_RESPONSES = ({
    "cmd": "test -f /home/ubuntu/matter-linux-app",
    "resp": "",
    "code": 0,
}, {
    "cmd": "test -f /etc/systemd/system/matter-linux-app.service",
    "resp": "",
    "code": 0,
}, {
    "cmd": "sudo systemctl is-enabled matter-linux-app.service",
    "resp": "enabled",
    "code": 0,
}, {
    "cmd": "pgrep -f matter-linux-app",
    "resp": "12345",
    "code": 0,
}, {
    "cmd": "sudo kill -9 12345",
    "resp": "",
    "code": 0,
}, {
    "cmd": "sudo systemctl enable matter-linux-app.service",
    "resp": "",
    "code": 0,
}, {
    "cmd": "sudo reboot",
    "resp": "",
    "code": 0,
}, {
    "cmd": "sudo rm -rf /tmp/chip*",
    "resp": "",
    "code": 0,
}, {
    "cmd": 'sudo sh -c \'echo "--- GDM Log Marker ---" >> /var/log/syslog\'',
    "resp": "",
    "code": 0
})

DEFAULT_BEHAVIOR = immutabledict({
    **raspbian_device_logs.DEFAULT_BEHAVIOR,
    **make_device_responses(_RESPONSES)
})
