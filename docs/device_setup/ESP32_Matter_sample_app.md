# Matter sample app on ESP32 M5Stack dev board

Manufacturer: [Espressif](https://www.espressif.com/en/products/socs/esp32)

Supported models: ESP32 M5Stack

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

Also need to clone the `Espressif ESP-IDF` tool for environment setup and image
compilation.

```
mkdir ${HOME}/tools
cd ${HOME}/tools
git clone https://github.com/espressif/esp-idf.git
cd esp-idf
git checkout v4.3
git submodule update --init
./install.sh
. ./export.sh
```

**2. Build**

Build the Matter sample app image with Pigweed RPC debug interface for ESP32
M5stck. Select the
[Matter application](https://github.com/project-chip/connectedhomeip/tree/master/examples)
you like to build (lighting, locking ... etc) and follow the instructions on
[README](https://github.com/project-chip/connectedhomeip/tree/master/examples/lock-app/esp32#building-the-example-application)
or the below detailed commands:

Inside `${project}` directory:

```
source ./scripts/bootstrap.sh
source ./scripts/activate.sh
cd examples/lock-app/esp32
```

Enable the Pigweed RPC build flag from menuconfig:

```
idf.py menuconfig
```

Inside menu console:

```
Component config -> CHIP Core -> General options -> Enable pigweed RPC library
```

Build the image:

```
idf.py build
```

**3. Flash**

Flash the image to the ESP32 M5Stack, follow the instructions on
[README](https://github.com/project-chip/connectedhomeip/tree/master/examples/lock-app/esp32#building-the-example-application)
or the below commands:

Inside the same build folder, `${device-address}` should be something like
`/dev/tty/ACM0`

```
idf.py -p ${device-address} flash monitor
```

You may also use GDM python interpreter for flashing:

The device needs to be detected first (depending on the present image, as a
plain `esp32` or as `esp32matter`),

```
>>> from gazoo_device import Manager
>>> m = Manager()
>>> m.detect()
```

Create the device class and flash the build:

```
>>> esp = m.create_device('esp32-b69b')
>>> esp.flash_build.upgrade(build_file='/path/to/application.bin',
                            partition_file='/path/to/partition_table.bin',
                            bootloader_file='/path/to/bootloader.bin')
```

(We can also use GDM CLI for flashing: `gdm issue esp32-b69b - flash_build -
upgrade --build_file=/path/to/application.bin
--partition_file=/path/to/partition_table.bin
--bootloader_file=/path/to/bootloader.bin`)

Note: For flashing a chef build, you'll also need to pass a
`flash_settings_file` argument for `chip-shell.flash.py`. Also sometimes the
`application.bin` might be renamed as `chip-shell.bin` in the build artifacts.

```
>>> esp.flash_build.upgrade(build_file='/path/to/chip-shell.bin',
                            partition_file='/path/to/partition_table.bin',
                            bootloader_file='/path/to/bootloader.bin',
                            flash_settings_file=/path/to/chip-shell.flash.py)
```

After flashing it'll need to be redetected (if going from `esp32` to
`esp32matter`).

```
>>> m.redetect('esp32-b69b')
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

Detect the ESP32 Matter sample app: `gdm detect`

```
    Device                     Alias           Type                 Model                Connected
    -------------------------- --------------- -------------------- -------------------- ----------
    esp32matter-6125           <undefined>     esp32matter          PROTO                connected

    Other Devices              Alias           Type                 Model                Available
    -------------------------- --------------- -------------------- -------------------- ----------
```

**6. (Recommended) Remove on-board coin cell battery**

The [battery](images/esp32_battery.jpg) on the
bottom of the board is an alternate power source for the board. When used in a
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
gdm issue esp32matter-6125 - factory_reset
gdm issue esp32matter-6125 - reboot
gdm issue esp32matter-6125 - qr_code
gdm issue esp32matter-6125 - matter_endpoints - list
gdm issue esp32matter-6125 - flash_build - upgrade --build_file=/path/to/application.bin --partition_file=/path/to/partition_table.bin --bootloader_file=/path/to/bootloader.bin
gdm man esp32matter  # To see all supported functionality
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
>>> esp = m.create_device('esp32matter-6125')
>>> esp.factory_reset()
>>> esp.reboot()
>>> esp.qr_code
>>> esp.matter_endpoints.list()
>>> esp.flash_build.upgrade(build_file='/path/to/application.bin',
                            partition_file='/path/to/partition_table.bin',
                            bootloader_file='/path/to/bootloader.bin')
>>> esp.close()
```

### Pigweed RPCs

The sample app on the dev board supports various Pigweed RPC calls:

**1. Reboot and factory reset**

```
>>> esp.reboot()
>>> esp.factory_reset()
```

**2. Getting pairing QR code and QR code URL**

```
>>> esp.qr_code
>>> esp.qr_code_url
```

**3. Push buttons on the board**

```
// Push button 0
>>> esp.pw_rpc_button.push(button_id=0)
```

**4. WiFi connection manipulation and properties**

```
>>> esp.pw_rpc_wifi.mac_address
>>> esp.pw_rpc_wifi.connect("ssid_wpa2_psk_name", "WIFI_AUTH_WPA2_PSK", "wifi_password")
>>> esp.pw_rpc_wifi.ipv4_address
>>> esp.pw_rpc_wifi.disconnect()
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
>>> esp.matter_endpoints.list()
{1: <class 'gazoo_device.capabilities.matter_endpoints.dimmable_light.DimmableLightEndpoint'>}
```

The keys in the mapping are Matter endpoint IDs on the device.

**2. Access the endpoint by `get`**

```
>>> esp.matter_endpoints.get(1).on_off.onoff
True
```

**3. Access the endpoint by alias**

```
>>> esp.dimmable_light.on_off.onoff
True
```

**4. Access an invalid endpoint**

Assume `esp` does not have a `DoorLock` endpoint.

```
>>> esp.door_lock
esp32matter-4585 starting MatterEndpointsAccessorPwRpc.get_endpoint_instance_by_class(endpoint_class=<class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'>)
esp32matter-4585 starting MatterEndpointsAccessorPwRpc.get_endpoint_id(endpoint_class=<class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'>)
Traceback (most recent call last):
  ....
    raise errors.DeviceError(
gazoo_device.errors.DeviceError: Class <class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'> is not supported on esp32matter-4585.
```
