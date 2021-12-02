# GDM device setup: Matter(CHIP) all-clusters sample app on ESP32 dev board

Manufacturer: https://www.espressif.com/en/products/socs/esp32

Supported models: ESP32 M5Stack

## Setup

1.  Clone the source from the Matter repository
    (https://github.com/project-chip/connectedhomeip) and build the Matter
    all-clusters sample app image with Pigweed RPC debug interface for ESP32
    M5Stack:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/all-clusters-app/esp32#building-the-example-application

2.  Flash the image to the ESP32 M5Stack:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/all-clusters-app/esp32#flashing-app-using-script

3.  (Optional) Try if the endpoints work in the interactive console: follow
    the instructions to launch an interactive console and send RPCs to the
    all-clusters app:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/all-clusters-app/esp32#using-the-rpc-console

4.  Detect the ESP32 all-clusters app: `gdm detect`

```shell
    Device                         Alias           Type                     Model                Connected
    ------------------------------ --------------- ------------------------ -------------------- ----------
    esp32matterallclusters-fa26   <undefined>     esp32matterallclusters  PROTO                connected
    Other Devices                  Alias           Type                     Model                Available
    ------------------------------ --------------- ------------------------ -------------------- ----------
```

## Usage

```shell
gdm issue esp32matterallclusters-fa26 - pw_rpc_light - on  # Turn the light on
gdm issue esp32matterallclusters-fa26 - pw_rpc_light - state  # Check the light state
gdm issue esp32matterallclusters-fa26 - pw_rpc_light - off  # Turn the light off
gdm issue esp32matterallclusters-fa26 - factory_reset
gdm issue esp32matterallclusters-fa26 - pw_rpc_common - vendor_id
gdm issue esp32matterallclusters-fa26 - pw_rpc_common - product_id
gdm issue esp32matterallclusters-fa26 - pw_rpc_common - software_version
gdm man esp32matterallclusters  # To see all supported functionality
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
>>> esp = m.create_device('esp32matterallclusters-fa26')
>>> esp.pw_rpc_light.on()
>>> esp.pw_rpc_light.state
>>> esp.close()
```

## Supported endpoints

The latest supported locking endpoints in GDM based on the Matter
[lighting proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/lighting_service.proto),
[device proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/device_service.proto),
[button proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/button_service.proto).

**1. Turn on/off the light and get light state**

```
>>> esp.pw_rpc_light.on()
>>> esp.pw_rpc_light.off()
>>> esp.pw_rpc_light.state
```

**2. Set and get brightness level**

```
>>> esp.pw_rpc_light.on(level=100)
>>> esp.pw_rpc_light.brightness
```

**3. Set and get lighting color**

```
>>> esp.pw_rpc_light.on(hue=50, saturation=30)
>>> esp.pw_rpc_light.color.hue
>>> esp.pw_rpc_light.color.saturation
```

**4. Factory reset**

```
>>> esp.factory_reset()
```

**5. Push button**

```
>>> esp.pw_rpc_button.push(button_id=0)
```
