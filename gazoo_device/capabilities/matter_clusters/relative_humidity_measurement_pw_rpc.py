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

"""Pigweed RPC implementation of Matter Relative Humidity Measurement cluster capability.
"""
from gazoo_device.capabilities import matter_enums
from gazoo_device.capabilities.matter_clusters.interfaces import measurement_base
from gazoo_device.protos import attributes_service_pb2


class RelativeHumidityMeasurementClusterPwRpc(
    measurement_base.MeasurementClusterBase):
  """Matter Pressure Measurement cluster capability."""

  CLUSTER_ID = matter_enums.RelativeHumidityMeasurementCluster.ID
  MATTER_CLUSTER = matter_enums.RelativeHumidityMeasurementCluster
  ATTRIBUTE_TYPE = (
      attributes_service_pb2.AttributeType.ZCL_INT16U_ATTRIBUTE_TYPE)
