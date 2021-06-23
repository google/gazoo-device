# Copyright 2021 Google LLC
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


def generate_command(cmd):
  return "{};echo Return Code: $?\n".format(cmd)


def generate_response(resp, code):
  return "{}\nReturn Code: {}\n\n".format(
      resp, code)  # Note the extra newline at the end


def make_device_responses(raw_response_dict):
  return {
      generate_command(entry["cmd"]): generate_response(entry["resp"],
                                                        entry["code"])
      for entry in raw_response_dict
  }


_RESPONSES = [{
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
}]

RESPONSES = make_device_responses(_RESPONSES)
