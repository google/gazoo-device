# Matter sample app on EFR32 dev board

Manufacturer: [Silicon Labs](https://www.silabs.com/)

Supported models: EFR32MG

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

Build the Matter sample app image with Pigweed RPC debug interface for EFR32
with `gn` command line tool, make sure it's in your path:
[clone gn](https://gn.googlesource.com/gn/). Select the
[Matter application](https://github.com/project-chip/connectedhomeip/tree/master/examples)
you'd like to build (lighting, locking ... etc).

Follow the instructions on the corresponding
[README](https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/efr32#building)
or the below detailed commands:

Inside `${project}` directory:

```
export EFR32_BOARD=BRD4161A
cd examples/lighting-app/efr32
source third_party/connectedhomeip/scripts/activate.sh
gn gen out/debug --args="efr32_board=\"${EFR32_BOARD}\""
gn gen out/debug --args="efr32_board=\"${EFR32_BOARD}\" import(\"//with_pw_rpc.gni\")"
ninja -C out/debug
```

**3. Flash**

Flash the image to the EFR32 by using
[Simplicity Commander](https://community.silabs.com/s/article/simplicity-commander?language=en_US).
Follow the instructions on
[README](https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/efr32#flashing-the-application)
or the below commands:

```
export PATH=$PATH:$HOME/SimplicityCommander-Linux/commander
commander flash ${image_file}.s37
```

You may also use GDM for flashing. You'll need to download the `.hex` image from
the above build bot, or manually convert the image from `.s37` to `.hex`
following the
[commander instruction](https://www.silabs.com/documents/public/user-guides/ug162-simplicity-commander-reference-guide.pdf).
Then use GDM python interpreter to flash:

The device needs to be detected first (depending on the present image, as a
plain `efr32` or as `efr32matter`),

```
>>> from gazoo_device import Manager
>>> m = Manager()
>>> m.detect()
```

Create the device class and flash the build:

```
>>> efr = m.create_device('efr32-3453')
>>> efr.flash_build.flash_device(['/path/to/efr32_sample_app.hex'])
```

(We can also use GDM CLI for flashing: `gdm issue efr32-3453 - flash_build -
upgrade --build_file=/path/to/efr32_sample_app.hex`)

After flashing it'll need to be redetected (if going from `efr32` to
`efr32matter`).

```
>>> m.redetect('efr32-3453')
```

**4. (Optional) Try Descriptor RPC**

Try if the Matter Descriptor endpoints work in the CHIP console.

Build the CHIP console by following the instructions on the above `Build`
section. Activate GDM virtual env and enable the CHIP console:
`${device-address}` should be something like `/dev/tty/ACM0`.

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

Detect the EFR32 Matter sample app: `gdm detect`

```
    Device                     Alias           Type                 Model                Connected
    -------------------------- --------------- -------------------- -------------------- ----------
    efr32matter-3453           <undefined>     efr32matter          PROTO                connected

    Other Devices              Alias           Type                 Model                Available
    -------------------------- --------------- -------------------- -------------------- ----------
```

**6. (Recommended) Remove on-board coin cell battery**

The coin cell [battery](images/efr32_battery.jpg)
besides the USB port is an alternate power source for the board. When used in a
testbed setup, the battery is not needed. Removing the battery enables the board
to be power cycled programmatically using

```
device.device_power.off()
device.device_power.on()
```

Which is useful to recover the device from unresponsiveness.

## Usage

Using the CLI

```
gdm issue efr32matter-6125 - factory_reset
gdm issue efr32matter-6125 - reboot
gdm issue efr32matter-6125 - qr_code
gdm issue efr32matter-6125 - matter_endpoints - list
gdm issue efr32matter-6125 - flash_build - upgrade --build_file=/path/to/efr32_sample_app.hex
gdm man efr32matter  # To see all supported functionality
```

Or inside the python console:

Activate GDM virtual env and open the console:

```
source ~/gazoo/gdm/virtual_env/bin/activate
python
```

Inside python console:

```
>>> from gazoo_device import Manager
>>> m = Manager()
>>> efr = m.create_device('efr32matter-6125')
>>> efr.factory_reset()
>>> efr.reboot()
>>> efr.qr_code
>>> efr.matter_endpoints.list()
>>> efr.flash_build.flash_device(['/path/to/efr32_sample_app.hex'])
>>> efr.close()
```

### Pigweed RPCs

The sample app on the dev board supports various Pigweed RPC calls:

**1. Reboot and factory reset**

```
>>> efr.reboot()
>>> efr.factory_reset()
```

**2. Getting pairing QR code and QR code URL**

```
>>> efr.qr_code
>>> efr.qr_code_url
```

**3. Push buttons on the board**

```
// Push button 0
>>> efr.pw_rpc_button.push(button_id=0)
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
>>> efr.matter_endpoints.list()
{1: <class 'gazoo_device.capabilities.matter_endpoints.dimmable_light.DimmableLightEndpoint'>}
```

The keys in the mapping are Matter endpoint IDs on the device.

**2. Access the endpoint by `get`**

```
>>> efr.matter_endpoints.get(1).on_off.onoff
True
```

**3. Access the endpoint by alias**

```
>>> efr.dimmable_light.on_off.onoff
True
```

**4. Access an invalid endpoint**

Assume `efr` does not have a `DoorLock` endpoint.

```
>>> efr.door_lock
efrmatter-4585 starting MatterEndpointsAccessor.get_endpoint_instance_by_class(endpoint_class=<class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'>)
efrmatter-4585 starting MatterEndpointsAccessor.get_endpoint_id(endpoint_class=<class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'>)
Traceback (most recent call last):
  ....
    raise errors.DeviceError(
gazoo_device.errors.DeviceError: Class <class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'> is not supported on efrmatter-4585.
```
