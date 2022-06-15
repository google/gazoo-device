# Matter Endpoints capability in GDM

## What is Matter

Matter is an industrial smart home protocol which simplifies development for
manufacturers and increases compatibility for consumers. The protocol is built
around a shared belief that smart home devices should be secure, reliable, and
seamless to use. By building upon Internet Protocol (IP), the project aims to
enable communication across smart home devices, mobile apps, and cloud services
and to define a specific set of IP-based networking technologies for device
certification. For more information, please visit
[Matter open source repository](https://github.com/project-chip/connectedhomeip).

## Matter Endpoint

A Matter endpoint is a logical instance of a device type within the physical,
addressable Matter device. For example, for a device which has 3 dimmable lights
on it and each endpoint houses an instance of the `DimmableLight` device type,
with `OnOff` and `Level` cluster on each endpoint.

A physical device can have multiple endpoints. Each endpoint also houses
different required or optional clusters. Each cluster possesses their
corresponding attributes and commands defined in the Matter spec. Note that the
endpoint ID 0 is the root node endpoint defined by the Matter spec. This
endpoint is akin to a "read me first" endpoint that describes itself and the
other endpoints that make up the node. In addition to the root node endpoint,
other endpoints must correspond to one of the "Matter device types" defined by
the Matter spec.

Below is a basic diagram of how Matter endpoints, clusters, and cluster
attributes/commands are organized:

![Matter_Structure_Example](device_setup/images/matter_structure_example.png)

For a lighting device which has 1 `OnOffLight` endpoint and 1
`ColorTemperatureLight` endpoint, the structure will look like:

![Matter_Structure_Light](device_setup/images/matter_structure_light.png)

## Matter Endpoint Capability in GDM

All the supported Matter endpoints in GDM are listed in the
[matter_endpoints directory](https://github.com/google/gazoo-device/tree/master/gazoo_device/capabilities/matter_endpoints).
Each endpoint definition includes its supported cluster aliases. These aliases
are used in the format of: `dut.door_lock`, `dut.dimmable_light`,
`dut.on_off_light` and so on.

The cluster implementations can be found in the
[matter_clusters directory](https://github.com/google/gazoo-device/tree/master/gazoo_device/capabilities/matter_clusters).

A Matter endpoint capability wrapper `matter_endpoints` is defined in the
[matter_base_device](https://github.com/google/gazoo-device/tree/master/gazoo_device/base_classes/matter_device_base.py)
module, which is for interacting with Matter endpoints. Also, all the supported
Matter endpoint aliases are defined in the same base class module. These aliases
represent all capabilities a generic Matter device class (ex:
[nrf_matter](https://github.com/google/gazoo-device/tree/master/gazoo_device/primary_devices/nrf_matter.py))
could support, while an individual device may not implement all of them. This is
a fundamental design descision to support the generic Matter device classes
([NRF](https://github.com/google/gazoo-device/blob/master/docs/device_setup/NRF_Matter_sample_app.md),
[EFR32](https://github.com/google/gazoo-device/blob/master/docs/device_setup/EFR32_Matter_sample_app.md),
[ESP32](https://github.com/google/gazoo-device/blob/master/docs/device_setup/ESP32_Matter_sample_app.md))
which is contrast to other GDM capabilities where defining a capability in a
device class means that it's implemented by the device.

For example, a `NrfMatter` device instance with a `DimmableLight` endpoint does
not have a `DoorLock` endpoint, so trying to access the `door_lock` endpoint on
the device will raise a `DeviceError`:

```
>>> nrf.door_lock
nrfmatter-4585 starting MatterEndpointsAccessorPwRpc.get_endpoint_instance_by_class(endpoint_class=<class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'>)
nrfmatter-4585 starting MatterEndpointsAccessorPwRpc.get_endpoint_id(endpoint_class=<class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'>)
Traceback (most recent call last):
  ....
    raise errors.DeviceError(
gazoo_device.errors.DeviceError: Class <class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'> is not supported on nrfmatter-4585.
```

On the other hand, accessing the `dimmable_light` endpoint should work:

```
>>> nrf.dimmable_light.on_off.onoff
True
```

See the below API usages for checking the supported endpoints on the device.

## Matter Endpoint API usages

The generic Matter device classes uses Descriptor cluster to list the supported
endpoints on the device. Users can use `matter_endpoints.get` or alias to access
the supported endpoint instance.

### Aliases

#### `color_temperature_light`

Alias for accessing `ColorTemperatureLight` endpoint and its supported clusters.

```
# Check the OnOff state on the OnOff cluster on the ColorTemperatureLight endpoint.
>>> dut.color_temperature_light.on_off.onoff
```

The supported clusters can be found in the
[GDM ColorTemperatureLight implementation](https://github.com/google/gazoo-device/blob/master/gazoo_device/capabilities/matter_endpoints/color_temperature_light.py).

#### `dimmable_light`

Alias for accessing `DimmableLight` endpoint and its supported clusters.

```
# Check the OnOff state on the OnOff cluster on the DimmableLight endpoint.
>>> dut.dimmable_light.on_off.onoff
```

The supported clusters can be found in the
[GDM DimmableLight implementation](https://github.com/google/gazoo-device/blob/master/gazoo_device/capabilities/matter_endpoints/dimmable_light.py).

#### `door_lock`

Alias for accessing `DoorLock` endpoint and its supported clusters.

```
# Check the LockState attribute on the DoorLock cluster on the DoorLock endpoint.
>>> dut.door_lock.door_lock.lock_state
```

The supported clusters can be found in the
[GDM DoorLock implementation](https://github.com/google/gazoo-device/blob/master/gazoo_device/capabilities/matter_endpoints/door_lock.py).

#### `on_off_light`

Alias for accessing `OnOffLight` endpoint and its supported clusters.

```
# Check the OnOff state on the OnOff cluster on the OnOffLight endpoint.
>>> dut.on_off_light.on_off.onoff
```

The supported clusters can be found in the
[GDM OnOffLight implementation](https://github.com/google/gazoo-device/blob/master/gazoo_device/capabilities/matter_endpoints/on_off_light.py).

#### `pressure_sensor`

Alias for accessing `PressureSensor` endpoint and its supported clusters.

```
# Check the MeasuredValue attribute on the PressureMeasurement cluster on the PressureSensor endpoint.
>>> dut.pressure_sensor.pressure_measurement.measured_value
```

The supported clusters can be found in the
[GDM PressureSensor implementation](https://github.com/google/gazoo-device/blob/master/gazoo_device/capabilities/matter_endpoints/pressure_sensor.py).

#### `temperature_sensor`

Alias for accessing `TemperatureSensor` endpoint and its supported clusters.

```
# Check the MeasuredValue attribute on the TemperatureMeasurement cluster on the TemperatureSensor endpoint.
>>> dut.temperature_sensor.temperature_measurement.measured_value
```

The supported clusters can be found in the
[GDM TemperatureSensor implementation](https://github.com/google/gazoo-device/blob/master/gazoo_device/capabilities/matter_endpoints/temperature_sensor.py).

### APIs of the Matter Endpoints capability

#### `list()`

List the supported endpoint ID to endpoint class mapping on the device.

```
>>> dut.matter_endpoints.list()
{1: <class 'gazoo_device.capabilities.matter_endpoints.dimmable_light.DimmableLightEndpoint'>}
```

The keys in the mapping are Matter endpoint IDs on the device.

#### `get(endpoint_id)`

Get the endpoint instance by the given endpoint ID.

```
>>> dut.matter_endpoints.get(1)
<gazoo_device.capabilities.matter_endpoints.on_off_light.OnOffLightEndpoint object at 0x7fca9d346eb0>
>>> dut.matter_endpoints.get(1).on_off.onoff
True
```

#### `reset()`

Reset the endpoint ID to endpoint class mapping on the device. This method will
be automatically called after a new build is flashed to the dev board via the
GDM `flash_build` capability. Users don't need to call this method explicitly.

```
>>> dut.matter_endpoints.reset()
```

#### `has_endpoints(endpoint_names)`

Return if the device supports all of the given endpoint names.

```
>>> dut.matter_endpoints.has_endpoints(["dimmable_light"])
True
>>> dut.matter_endpoints.has_endpoints(["door_lock"])
False
```

#### `get_supported_endpoints()`

Return a list of the supported endpoint names on the device.

```
>>> dut.matter_endpoints.get_supported_endpoints()
["dimmable_light", "on_off_light"]
```

#### `get_supported_endpoint_flavors()`

Return a list of the supported endpoint flavors on the device.

```
>>> dut.matter_endpoints.get_supported_endpoint_flavors()
[<class 'gazoo_device.capabilities.matter_endpoints.dimmable_light.DimmableLightEndpoint'>,
<class 'gazoo_device.capabilities.matter_endpoints.on_off_light.OnOffLightEndpoint'>]
```

#### `get_supported_endpoints_and_clusters()`

Return a mapping of the supported endpoint ID to the set of cluster names.

```
>>> dut.matter_endpoints.get_supported_endpoints_and_clusters()
{1: ['color_control_cluster', 'door_lock_cluster', 'level_control_cluster', 'on_off_cluster'], 2: ['on_off_cluster']}
```

#### `get_supported_endpoint_instances_and_cluster_flavors()`

Return a mapping of the supported endpoint instance to the set of cluster
flavors.

```
>>> dut.matter_endpoints.get_supported_endpoint_instances_and_cluster_flavors()
{<gazoo_device.capabilities.matter_endpoints.on_off_light.OnOffLightEndpoint object at 0x7f70b1501580>:
frozenset({<class 'gazoo_device.capabilities.matter_clusters.level_control_pw_rpc.LevelControlClusterPwRpc'>,
<class 'gazoo_device.capabilities.matter_clusters.on_off_pw_rpc.OnOffClusterPwRpc'>,
<class 'gazoo_device.capabilities.matter_clusters.color_control_pw_rpc.ColorControlClusterPwRpc'>,
<class 'gazoo_device.capabilities.matter_clusters.door_lock_pw_rpc.DoorLockClusterPwRpc'>}),
<gazoo_device.capabilities.matter_endpoints.on_off_light.OnOffLightEndpoint object at 0x7f70b1501f40>:
frozenset({<class 'gazoo_device.capabilities.matter_clusters.on_off_pw_rpc.OnOffClusterPwRpc'>})})
```

#### `read(endpoint_id, cluster_id, attribute_id, attribute_type)`

Ember API read method to read the data from a specific endpoint with given
cluster ID, attribute ID and attribute type. The Ember API can be used to
interact with any Matter endpoint, including ones that don't have GDM support
yet. It's mostly called by the cluster instance and generally doesn't need to be
called by the users.

```
>>> dut.matter_endpoints.read(endpoint_id=1. cluster_id=6, attribute_id=0, attribute_type=16)
data_bool: false
```

#### `write(endpoint_id, cluster_id, attribute_id, attribute_type, **data_kwargs)`

Ember API write method to write the data to a specific endpoint with given
cluster ID, attribute ID and attribute type. The Ember API can be used to
interact with any Matter endpoint, including ones that don't have GDM support
yet. It's mostly called by the cluster instance and generally doesn't need to be
called by the users.

```
>>> dut.matter_endpoints.write(endpoint_id=1. cluster_id=6, attribute_id=0, attribute_type=16, data_bool=True)
```

### APIs / properties of endpoint instances

The APIs and properties that exist on all endpoint instances. The below code
snippets use `on_off_light` as examples.

#### `id`

Return the endpoint ID of the instance.

```
>>> dut.on_off_light.id
1
```

#### `name`

Return the endpoint name of the instance.

```
>>> dut.on_off_light.name
'on_off_light'
```

#### `has_clusters(cluster_names)`

Return if the device supports all of the given cluster names.

```
>>> dut.on_off_light.has_clusters(['level_control', 'on_off'])
True
>>> dut.on_off_light.has_clusters(['door_lock'])
False
```

#### `get_supported_clusters()`

Return a list of the supported cluster names on the endpoint.

```
>>> dut.on_off_light.get_supported_clusters()
['level_control_cluster', 'occupancy_cluster', 'on_off_cluster']
```

#### `get_supported_cluster_flavors()`

Return a list of the supported cluster flavors on the endpoint.

```
>>> dut.on_off_light.get_supported_cluster_flavors()
frozenset({<class 'gazoo_device.capabilities.matter_clusters.occupancy_pw_rpc.OccupancyClusterPwRpc'>,
<class 'gazoo_device.capabilities.matter_clusters.level_control_pw_rpc.LevelControlClusterPwRpc'>,
<class 'gazoo_device.capabilities.matter_clusters.on_off_pw_rpc.OnOffClusterPwRpc'>})
```
