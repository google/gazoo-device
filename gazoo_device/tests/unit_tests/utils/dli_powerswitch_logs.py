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

"""Device logs for DLI powerswitch devices."""

RETURN_CODE = "200\n"
ERROR_RETURN_CODE = "409\n"

DEFAULT_BEHAVIOR = {
    "http://123.45.67.89/restapi/config/=version/": {
        "text": '["1.7.15.0"]',
        "status_code": "207"
    },
    "http://123.45.67.89/restapi/config/=serial/": {
        "text": '["ABCD1234"]',
        "status_code": "207"
    },
    "http://123.45.67.89/restapi/config/=brand_company_name/": {
        "text": '["Digital Loggers, Inc."]',
        "status_code": "207"
    },
    "http://123.45.67.89/restapi/config/=brand_name/": {
        "text": '["Web Power Switch"]',
        "status_code": "207"
    },
    "http://123.45.67.89/restapi/relay/outlets/=1/state/": {
        "text": '["true"]',
        "status_code": "207"
    },
}
