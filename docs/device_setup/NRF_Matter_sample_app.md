# Matter sample app on Nordic dev board

Manufacturer: [Nordic Semiconductor](https://www.nordicsemi.com)

Supported models: NRF52840 DK

## Setup

**1. Clone**

Clone the source (master) from the Matter repository
https://github.com/project-chip/connectedhomeip and do submodule update.

Inside your own `${project}` directory:

```
git clone https://github.com/project-chip/connectedhomeip.git
cd connectedhomeip
git submodule update --init
```

**2. Build**

Build the Matter sample app image with Pigweed RPC debug interface for NRF DK.
Select the
[Matter application](https://github.com/project-chip/connectedhomeip/tree/master/examples)
you like to build (lighting, locking ... etc) and follow the instructions on
[README](https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/nrfconnect#building-with-pigweed-rpcs)
or the below detailed commands by using Docker container:

Inside `${project}` directory:

```
mkdir -p nrfconnect
docker pull nordicsemi/nrfconnect-chip
docker run --rm -it -e RUNAS=$(id -u) -v nrfconnect:/var/ncs -v connectedhomeip:/var/chip \
     -v /dev/bus/usb:/dev/bus/usb --device-cgroup-rule "c 189:* rmw" nordicsemi/nrfconnect-chip
```

Inside container (If there's an error during setup, exit the container and run
`rm -rf nrfconnect && mkdir -p nrfconnect`)

```
setup --ncs v1.6.1
cd /var/chip
python3 scripts/setup/nrfconnect/update_ncs.py --update
source ./scripts/activate.sh
cd examples/lighting-app/nrfconnect
rm -rf build/ && west build -b nrf52840dk_nrf52840 -- -DOVERLAY_CONFIG=rpc.overlay
```

**3. Flash**

Flash the image to the NRF52840 DK by using the
[nRF command line tools](https://www.nordicsemi.com/Products/Development-tools/nrf-command-line-tools/download)
(download the binary and make sure `nrfjprog` exists in your `$PATH`), follow
the instructions on
[README](https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/nrfconnect#flashing-and-debugging)
or the below commands:

```
nrfjprog -f nrf52 --program ${image_file}.hex --sectorerase -s ${serial-number}
nrfjprog -f nrf52 --reset -s ${serial-number}
```

You may also use GDM python interpreter for flashing:

The device needs to be detected first (depending on the present image, as a
plain `nrf52840` or as `nrfmatter`):

```
>>> from gazoo_device import Manager
>>> m = Manager()
>>> m.detect()
```

Create the device class and flash the build:

```
>>> nrf = m.create_device('nrf52840-3453')
>>> nrf.flash_build.flash_device(['/path/to/nrf52840_sample_app.hex'])
```

(We can also use GDM CLI for flashing: `gdm issue nrf52840-3453 - flash_build -
upgrade --build_file=/path/to/nrf52840_sample_app.hex`)

After flashing it'll need to be redetected (if going from `nrf52840` to
`nrfmatter`).

```
>>> m.redetect('nrf52840-3453')
```

**4. (Optional) Try Descriptor RPC**

Try if the Matter Descriptor endpoints work in the CHIP console.

Build the CHIP console by following the instructions on the above `Build`
section. Activate GDM virtual env and enable the CHIP console:
`${device-address}` should be something like `/dev/tty/ACM0`

```
source ~/gazoo/gdm/virtual_env/bin/activate
python -m chip_rpc.console --device ${device-address} -b 115200 -o /tmp/pw.log
```

Inside interactive console:

```
# Get supported endpoints on the device
In [1]: rpcs.chip.rpc.Descriptor.PartsList(endpoint=0)
>>> (Status.OK, [chip.rpc.Endpoint(endpoint=1)])

# Check device type of the endpoint
In [2]:  rpcs.chip.rpc.Descriptor.DeviceTypeList(endpoint=1)
>>> (Status.OK, [chip.rpc.DeviceType(device_type=10)])
```

**5. Device detection**

Detect the NRF Matter sample app: `gdm detect`

```
    Device                     Alias           Type                 Model                Connected
    -------------------------- --------------- -------------------- -------------------- ----------
    nrfmatter-6125             <undefined>     nrfmatter            PROTO                connected

    Other Devices              Alias           Type                 Model                Available
    -------------------------- --------------- -------------------- -------------------- ----------
```

**6. (Recommended) Remove on-board CR2032 coin cell battery**

The coin cell [battery](images/nrf52840_battery.jpg)
on the back of the board is an alternate power source for the board. When used
in a testbed setup, the battery is not needed. Removing the battery enables the
board to be power cycled programmatically using

```
device.device_power.off()
device.device_power.on()
```

Which is useful to recover the device from unresponsiveness.

## Usage

Using the CLI

```
gdm issue nrfmatter-6125 - factory_reset
gdm issue nrfmatter-6125 - reboot
gdm issue nrfmatter-6125 - qr_code
gdm issue nrfmatter-6125 - matter_endpoints - list
gdm issue nrfmatter-6125 - flash_build - upgrade --build_file=/path/to/nrf52840_sample_app.hex
gdm man nrfmatter  # To see all supported functionality
```

Or inside the python console

Activate GDM virtual env and open the console:

```
source ~/gazoo/gdm/virtual_env/bin/activate
python
```

Inside python console:

```
>>> from gazoo_device import Manager
>>> m = Manager()
>>> nrf = m.create_device('nrfmatter-6125')
>>> nrf.factory_reset()
>>> nrf.reboot()
>>> nrf.qr_code
>>> nrf.matter_endpoints.list()
>>> nrf.flash_build.flash_device(['/path/to/nrf52840_sample_app.hex'])
>>> nrf.close()
```

### Pigweed RPCs

The sample app on the dev board supports various Pigweed RPC calls:

**1. Reboot and factory reset**

```
>>> nrf.reboot()
>>> nrf.factory_reset()
```

**2. Getting pairing QR code and QR code URL**

```
>>> nrf.qr_code
>>> nrf.qr_code_url
```

**3. Push buttons on the board**

```
// Push button 0
>>> nrf.pw_rpc_button.push(button_id=0)
```

### Matter endpoints

The Matter sample app uses Descriptor cluster to list the supported endpoints on
the device, users can use `matter_endpoints.get` or alias to access the
supported endpoint. Accessing an invalid endpoint will raise a `DeviceError`.
(Invalid endpoint means either: the given endpoint id is not available on the
device, or the endpoint alias is not supported on the device.)

Please visit [Matter Endpoint Doc](../Matter_endpoints.md) for more information.

**1. List supported endpoints**

```
>>> nrf.matter_endpoints.list()
{1: <class 'gazoo_device.capabilities.matter_endpoints.dimmable_light.DimmableLightEndpoint'>}
```

The keys in the mapping are Matter endpoint IDs on the device.

**2. Access the endpoint by `get`**

```
>>> nrf.matter_endpoints.get(1).on_off.onoff
True
```

**3. Access the endpoint by alias**

```
>>> nrf.dimmable_light.on_off.onoff
True
```

**4. Access an invalid endpoint**

Assume `nrf` does not have a `DoorLock` endpoint.

```
>>> nrf.door_lock
nrfmatter-4585 starting MatterEndpointsAccessorPwRpc.get_endpoint_instance_by_class(endpoint_class=<class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'>)
nrfmatter-4585 starting MatterEndpointsAccessorPwRpc.get_endpoint_id(endpoint_class=<class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'>)
Traceback (most recent call last):
  ....
    raise errors.DeviceError(
gazoo_device.errors.DeviceError: Class <class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'> is not supported on nrfmatter-4585.
```
