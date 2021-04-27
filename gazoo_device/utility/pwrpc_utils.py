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

"""Utility module for interaction with PwRPC (Pigweed RPC)."""
from gazoo_device import gdm_logger


PROTO_PACKAGE = "gazoo_device.protos"
NON_PIGWEED_TYPE = "nonpigweed"
PIGWEED_LIGHTING_TYPE = "lighting"
PWRPC_LIGHTING_PROTO = "pigweed_lighting.proto"

logger = gdm_logger.get_logger()


# pylint: disable=unused-argument
def application_type(address: str) -> str:
  """Returns Pigweed application type of the device.

  Args:
    address: Device serial address.

  Returns:
    Pigweed application type.
  """
  # TODO(b/183467331) Add device application type detection logic.
  return PIGWEED_LIGHTING_TYPE
