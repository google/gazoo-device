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
"""Capability unit test for matter_endpoints_accessor module."""
from unittest import mock

from absl.testing import parameterized
from gazoo_device import errors
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities import matter_endpoints_and_clusters
from gazoo_device.capabilities.matter_endpoints import on_off_light
from gazoo_device.capabilities.matter_endpoints import unsupported_endpoint
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base
from gazoo_device.protos import attributes_service_pb2
from gazoo_device.protos import descriptor_service_pb2
from gazoo_device.switchboard import switchboard
from gazoo_device.tests.unit_tests.utils import fake_device_test_case

_FAKE_ENDPOINT_ID = 0
_FAKE_DEVICE_TYPE_ID = 10
_FAKE_CLUSTER_ID = 0
_FAKE_RPC_TIMEOUT_S = 10
_FAKE_DEVICE_NAME = "fake-device-name"
_FAKE_ENDPOINT_NAME = "fake_endpoint_name"
_FAKE_CLUSTER_NAME = "fake_cluster_name"
_FAKE_ENDPOINT_IDS = [_FAKE_ENDPOINT_ID]
_FAKE_ENDPOINT_CLS = mock.Mock(DEVICE_TYPE_ID=_FAKE_DEVICE_TYPE_ID)
_FAKE_ENDPOINT_INST = mock.Mock(spec=endpoint_base.EndpointBase)
_FAKE_CLUSTER_CLS = mock.Mock(CLUSTER_ID=_FAKE_CLUSTER_ID)
_FAKE_ENDPOINT_ID_TO_CLS = {_FAKE_ENDPOINT_ID: _FAKE_ENDPOINT_CLS}
_FAKE_ENDPOINT_CLS_TO_ID = {_FAKE_ENDPOINT_CLS: _FAKE_ENDPOINT_ID}
_FAKE_ENDPOINT_ID_TO_CLUSTERS = {_FAKE_ENDPOINT_ID: [_FAKE_CLUSTER_CLS]}
_FAKE_ENDPOINT_ID_TO_DEVICE_TYPE_ID = {_FAKE_ENDPOINT_ID: _FAKE_DEVICE_TYPE_ID}
_FAKE_NOT_IMPLEMENTED_CLUSTER_ID = 1
_FAKE_ATTRIBUTE_ID = 0
_FAKE_ATTRIBUTE_TYPE = attributes_service_pb2.AttributeType.ZCL_BOOLEAN_ATTRIBUTE_TYPE


class MatterEndpointsAccessorPwPpcTest(
    fake_device_test_case.FakeDeviceTestCase):
  """Unit test for MatterEndpointsAccessorPwRpc."""

  def setUp(self):
    super().setUp()
    self.fake_switchboard_call = mock.Mock(
        spec=switchboard.SwitchboardDefault.call)
    self.uut = matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc(
        device_name=_FAKE_DEVICE_NAME,
        switchboard_call=self.fake_switchboard_call,
        rpc_timeout_s=_FAKE_RPC_TIMEOUT_S)
    _FAKE_ENDPOINT_CLS.return_value = _FAKE_ENDPOINT_INST

  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "get_supported_clusters",
      return_value={
          _FAKE_CLUSTER_CLS,
      })
  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "get_endpoint_class_and_device_type_id",
      side_effect=[(_FAKE_ENDPOINT_CLS, _FAKE_DEVICE_TYPE_ID)])
  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "get_supported_endpoint_ids",
      return_value=_FAKE_ENDPOINT_IDS)
  def test_fetch_endpoints_and_clusters_on_success(
      self, mock_get_suppored_endpoint_ids, mock_get_endpoint_cls,
      mock_get_supported_clusters):
    """Verifies descriptor RPC service is triggered successfully."""
    self.uut.reset()

    self.uut._fetch_endpoints_and_clusters()

    self.assertEqual(
        _FAKE_DEVICE_TYPE_ID,
        self.uut.endpoint_id_to_class[_FAKE_ENDPOINT_ID].DEVICE_TYPE_ID)
    self.assertIn(_FAKE_ENDPOINT_ID, self.uut.endpoint_class_to_id.values())
    self.assertEqual(
        _FAKE_CLUSTER_ID,
        self.uut.endpoint_id_to_clusters[_FAKE_ENDPOINT_ID].pop().CLUSTER_ID)
    mock_get_suppored_endpoint_ids.assert_called_once()
    mock_get_endpoint_cls.assert_called_once()
    mock_get_supported_clusters.assert_called_once()

  def test_get_supported_endpoint_ids(self):
    """Verifies get_supported_endpoint_ids method on success."""
    fake_endpoint = descriptor_service_pb2.Endpoint(endpoint=_FAKE_ENDPOINT_ID)
    fake_supported_endpoints = [fake_endpoint.SerializeToString()]
    self.fake_switchboard_call.return_value = fake_supported_endpoints

    self.assertEqual([_FAKE_ENDPOINT_ID], self.uut.get_supported_endpoint_ids())

  @mock.patch.object(
      matter_endpoints_and_clusters.MATTER_DEVICE_TYPE_ID_TO_CLASS,
      "get",
      return_value=_FAKE_ENDPOINT_CLS)
  def test_get_endpoint_class_and_device_type_id(self, mock_mapping):
    """Verifies get_endpoint_class_and_device_type_id on success."""
    fake_device_type = descriptor_service_pb2.DeviceType(
        device_type=_FAKE_DEVICE_TYPE_ID)
    fake_device_types = [fake_device_type.SerializeToString()]
    self.fake_switchboard_call.return_value = fake_device_types

    self.assertEqual(
        (_FAKE_ENDPOINT_CLS, _FAKE_DEVICE_TYPE_ID),
        self.uut.get_endpoint_class_and_device_type_id(_FAKE_ENDPOINT_ID))

  def test_reset_method_on_success(self):
    """Verifies reset method on success."""
    self.uut.reset()

    self.assertEqual({}, self.uut._endpoint_id_to_class)
    self.assertEqual({}, self.uut._endpoint_class_to_id)
    self.assertEqual({}, self.uut._endpoint_id_to_clusters)

  @parameterized.parameters(
      dict(cluster_id=_FAKE_CLUSTER_ID, cluster_class=_FAKE_CLUSTER_CLS),
      dict(cluster_id=_FAKE_NOT_IMPLEMENTED_CLUSTER_ID, cluster_class=None))
  @mock.patch.object(matter_endpoints_and_clusters.CLUSTER_ID_TO_CLASS_PW_RPC,
                     "get")
  def test_get_supported_clusters_on_success(self, mock_get, cluster_id,
                                             cluster_class):
    """Verifies get_supported_clusters method on success."""
    mock_get.return_value = cluster_class
    fake_cluster = descriptor_service_pb2.Cluster(cluster_id=cluster_id)
    fake_clusters = [fake_cluster.SerializeToString()]
    self.fake_switchboard_call.return_value = fake_clusters

    expected_cluster_classes = (
        set() if cluster_class is None else {
            cluster_class,
        })
    self.assertEqual(
        expected_cluster_classes,
        self.uut.get_supported_clusters(endpoint_id=_FAKE_ENDPOINT_ID))

  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "_fetch_endpoints_and_clusters")
  def test_get_method_on_success_with_supported_endpoint(self, mock_fetch):
    """Verifies the get endpoint method on success with supported endpoint."""
    self.uut._endpoint_id_to_class = _FAKE_ENDPOINT_ID_TO_CLS
    self.uut._endpoint_id_to_clusters = _FAKE_ENDPOINT_ID_TO_CLUSTERS
    self.uut._endpoint_id_to_device_type_id = _FAKE_ENDPOINT_ID_TO_DEVICE_TYPE_ID
    self.uut._endpoints.clear()

    _FAKE_ENDPOINT_CLS.return_value = _FAKE_ENDPOINT_INST
    self.assertEqual(_FAKE_ENDPOINT_INST, self.uut.get(_FAKE_ENDPOINT_ID))

  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "_fetch_endpoints_and_clusters")
  def test_get_method_on_success_with_unsupported_endpoint(self, mock_fetch):
    """Verifies the get endpoint method on success with unsupported endpoint."""
    self.uut._endpoint_id_to_class = {
        _FAKE_ENDPOINT_ID: unsupported_endpoint.UnsupportedEndpoint
    }
    self.uut._endpoint_id_to_clusters = _FAKE_ENDPOINT_ID_TO_CLUSTERS
    self.uut._endpoint_id_to_device_type_id = _FAKE_ENDPOINT_ID_TO_DEVICE_TYPE_ID
    self.uut._endpoints.clear()

    self.assertIsInstance(
        self.uut.get(_FAKE_ENDPOINT_ID),
        unsupported_endpoint.UnsupportedEndpoint)

  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "_fetch_endpoints_and_clusters")
  def test_get_method_on_failure_invalid_id(self, mock_fetch):
    """Verifies get endpoint method on failure for invalid endpoint ID."""
    self.uut._endpoint_id_to_class = {}

    with self.assertRaisesRegex(
        errors.DeviceError, f"Endpoint ID {_FAKE_ENDPOINT_ID} on "
        f"{_FAKE_DEVICE_NAME} does not exist"):
      self.uut.get(_FAKE_ENDPOINT_ID)

  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "_fetch_endpoints_and_clusters")
  def test_list_endpoints(self, mock_fetch):
    """Verifies the list endpoints method on success."""
    self.uut._endpoint_id_to_class = _FAKE_ENDPOINT_ID_TO_CLS
    self.assertEqual(_FAKE_ENDPOINT_ID_TO_CLS, self.uut.list())

  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "get",
      return_value=_FAKE_ENDPOINT_INST)
  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "_fetch_endpoints_and_clusters")
  def test_get_endpoint_instance_by_class_on_success(self, mock_fetch,
                                                     mock_get):
    """Verifies get_endpoint_instance_by_class method on success."""
    self.uut._endpoint_class_to_id = _FAKE_ENDPOINT_CLS_TO_ID

    self.assertEqual(
        _FAKE_ENDPOINT_INST,
        self.uut.get_endpoint_instance_by_class(_FAKE_ENDPOINT_CLS))
    mock_get.assert_called_once()

  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "_fetch_endpoints_and_clusters")
  def test_get_endpoint_instance_by_class_on_failure(self, mock_fetch):
    """Verifies get_endpoint_instance_by_class with unsupported endpoint."""
    self.uut._endpoint_class_to_id = {}

    with self.assertRaisesRegex(errors.DeviceError, "is not supported on"):
      self.uut.get_endpoint_instance_by_class(_FAKE_ENDPOINT_CLS)

  @parameterized.parameters(
      dict(supported_endpoint=on_off_light.OnOffLightEndpoint, expected=True),
      dict(supported_endpoint=None, expected=False))
  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc, "list")
  def test_has_endpoints_on_success(self, mock_list, supported_endpoint,
                                    expected):
    """Verifies has_endpoints method on success."""
    mock_list.return_value = {_FAKE_ENDPOINT_ID: supported_endpoint}
    endpoint_name = on_off_light.OnOffLightEndpoint.get_capability_name()

    self.assertEqual(expected, self.uut.has_endpoints([endpoint_name]))

  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "_fetch_endpoints_and_clusters")
  def test_has_endpoints_on_failure_invalid_endpoint(self, mock_fetch):
    """Verifies has_endpoints method on failure with invalid endpoint."""
    self.assertFalse(self.uut.has_endpoints([_FAKE_ENDPOINT_NAME]))

  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
      "get_supported_endpoint_flavors")
  def test_get_supported_endpoints_on_success(
      self, mock_get_supported_endpoint_flavors):
    """Verifies get_supported_endpoints method on success."""
    fake_endpoint = mock.Mock(spec=endpoint_base.EndpointBase)
    fake_endpoint.get_capability_name.return_value = _FAKE_ENDPOINT_NAME
    mock_get_supported_endpoint_flavors.return_value = [fake_endpoint]

    self.assertEqual([_FAKE_ENDPOINT_NAME], self.uut.get_supported_endpoints())

  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc, "list")
  def test_get_supported_endpoint_flavors_on_success(self, mock_list):
    """Verifies get_supported_endpoint_flavors method on success."""
    fake_endpoint = mock.Mock(spec=endpoint_base.EndpointBase)
    mock_list.return_value = {_FAKE_ENDPOINT_ID: fake_endpoint}

    self.assertEqual([fake_endpoint], self.uut.get_supported_endpoint_flavors())

  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc, "get")
  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc, "list")
  def test_get_supported_endpoints_and_clusters(self, mock_list, mock_get):
    """Verifies get_supported_endpoints_and_clusters method on success."""
    mock_list.return_value = [_FAKE_ENDPOINT_ID]
    mock_get.return_value.get_supported_clusters.return_value = [
        _FAKE_CLUSTER_NAME
    ]

    self.assertEqual({_FAKE_ENDPOINT_ID: [_FAKE_CLUSTER_NAME]},
                     self.uut.get_supported_endpoints_and_clusters())

  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc, "get")
  @mock.patch.object(
      matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc, "list")
  def test_get_supported_endpoint_instances_and_cluster_flavors(
      self, mock_list, mock_get):
    """Verifies get_supported_endpoint_instances_and_cluster_flavors method."""
    mock_list.return_value = [_FAKE_ENDPOINT_ID]
    mock_get.return_value = _FAKE_ENDPOINT_INST
    _FAKE_ENDPOINT_INST.get_supported_cluster_flavors.return_value = [
        _FAKE_CLUSTER_CLS
    ]
    expected_mapping = {_FAKE_ENDPOINT_INST: [_FAKE_CLUSTER_CLS]}

    self.assertEqual(
        expected_mapping,
        self.uut.get_supported_endpoint_instances_and_cluster_flavors())

  def test_ember_api_read(self):
    """Verifies Ember API read method on success."""
    data = attributes_service_pb2.AttributeData(data_bool=True)
    self.fake_switchboard_call.return_value = data.SerializeToString()

    self.assertEqual(
        data,
        self.uut.read(
            endpoint_id=_FAKE_ENDPOINT_ID,
            cluster_id=_FAKE_CLUSTER_ID,
            attribute_id=_FAKE_ATTRIBUTE_ID,
            attribute_type=_FAKE_ATTRIBUTE_TYPE))

  def test_ember_api_write(self):
    """Verifies Ember API write method on success."""
    self.uut.write(
        endpoint_id=_FAKE_ENDPOINT_ID,
        cluster_id=_FAKE_CLUSTER_ID,
        attribute_id=_FAKE_ATTRIBUTE_ID,
        attribute_type=_FAKE_ATTRIBUTE_TYPE,
        data_bool=True)

    self.fake_switchboard_call.assert_called_once()


if __name__ == "__main__":
  fake_device_test_case.main()
