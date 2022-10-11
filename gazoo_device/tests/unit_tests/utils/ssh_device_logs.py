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

"""Generic SSH (Linux) device logs."""
from immutabledict import immutabledict


def generate_command(cmd):
  return ("echo '{}';".format(cmd.replace("'", r"'\''")) +
          cmd + ";" +
          "echo Return Code: $?\n")


def generate_response(cmd, resp, code, add_response_newline=True):
  response_newline = "" if not add_response_newline else "\n"
  return (f"{cmd}\n"
          f"{resp}{response_newline}"
          f"Return Code: {code}\n")


def make_device_responses(raw_response_dict):
  device_responses = {}
  for entry in raw_response_dict:
    device_responses.update({
        generate_command(entry["cmd"]): generate_response(
            entry["cmd"], entry["resp"], entry["code"],
            entry.get("response_newline", True))
    })
  return immutabledict(device_responses)


_RESPONSES = ({
    "cmd": "echo 'gdm hello'",
    "resp": "gdm hello",
    "code": 0,
}, {
    "cmd": "which ls",
    "resp": "/bin/ls",
    "code": 0,
}, {
    "cmd": "which foo_bar",
    "resp": "",
    "code": 1,
})

RESPONSES = make_device_responses(_RESPONSES)
