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

"""Interface for a Matter endpoint base capability."""
from typing import Any, Type
from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.capabilities.interfaces import capability_base
from gazoo_device.capabilities.matter_clusters.interfaces import cluster_base

logger = gdm_logger.get_logger()


class EndpointBase(capability_base.CapabilityBase):
  """Matter endpoint base interface."""

  # TODO(b/209366650) Add discovery cluster support.

  @decorators.CapabilityLogDecorator(logger, level=decorators.DEBUG)
  def cluster_lazy_init(
      self,
      cluster_class: Type[cluster_base.ClusterBase],
      *args: Any,
      **kwargs: Any) -> cluster_base.ClusterBase:
    """Provides a lazy instantiation mechanism for Matter cluster.

    Args:
      cluster_class: cluster class to instantiate.
      *args: positional args to the cluster's __init__. Prefer
        using keyword arguments over positional arguments.
      **kwargs: keyword arguments to the cluster's __init__.

    Returns:
      Initialized Matter cluster instance.
    """
    cluster_name = cluster_class.__name__
    if not hasattr(self, cluster_name):
      cluster_inst = cluster_class(*args, **kwargs)
      setattr(self, cluster_name, cluster_inst)
    return getattr(self, cluster_name)
