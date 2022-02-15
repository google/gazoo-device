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

    You may also use GDM python interpreter for flashing:

    ```
    >>> from gazoo_device import Manager
    >>> m = Manager()
    >>> esp = m.create_device('esp32matterallclusters-fa26')
    >>> esp.flash_build.upgrade(build_file='/path/to/application.bin',
                                partition_file='/path/to/partition_table.bin',
                                bootloader_file='/path/to/bootloader.bin')
    ```

    Or using GDM CLI:

    ```
    gdm issue esp32matterallclusters-fa26 - flash_build - upgrade \
      --build_file=/path/to/application.bin \
      --partition_file=/path/to/partition_table.bin \
      --bootloader_file=/path/to/bootloader.bin
    ```

3.  (Optional) Try if the endpoints work in the interactive console: follow the
    instructions to launch an interactive console and send RPCs to the
    all-clusters app:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/all-clusters-app/esp32#using-the-rpc-console

4.  Detect the ESP32 all-clusters app: `gdm detect`

```shell
    Device                         Alias           Type                     Model                Connected
    ------------------------------ --------------- ------------------------ -------------------- ----------
    esp32matterallclusters-fa26   <undefined>     esp32matterallclusters  PROTO                connected
    Other Devices                  Alias          Type                    Model                Available
    ------------------------------ --------------- ------------------------ -------------------- ----------
```

## Example Usage

```shell
gdm issue esp32matterallclusters-fa26 - on_off_light - on_off - on  # Turn the light on
gdm issue esp32matterallclusters-fa26 - on_off_light - on_off - onoff  # Check the light state
gdm issue esp32matterallclusters-fa26 - on_off_light - on_off - off  # Turn the light off
gdm issue esp32matterallclusters-fa26 - factory_reset
gdm issue esp32matterallclusters-fa26 - pw_rpc_common - vendor_id
gdm issue esp32matterallclusters-fa26 - pw_rpc_common - product_id
gdm issue esp32matterallclusters-fa26 - pw_rpc_common - software_version
gdm issue esp32matterallclusters-fa26 - pw_rpc_wifi - ipv4_address
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
>>> esp.on_off_light.on_off.on()
>>> esp.on_off_light.on_off.onoff
>>> esp.pw_rpc_wifi.ipv4_address
>>> esp.close()
```

## Supported endpoints

The latest supported endpoints in GDM based on the Matter
[lighting proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/lighting_service.proto),
[device proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/device_service.proto),
[button proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/button_service.proto),
[wifi_proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/ipv6only-app/common/wifi_service/wifi_service.proto).

**1. Turn on/off the light and get light state**

```
>>> esp.on_off_light.on_off.on()
>>> esp.on_off_light.on_off.off()
>>> esp.on_off_light.on_off.onoff
```

**2. Set and get brightness level**

```
>>> esp.on_off_light.on_off.move_to_level(level=108)
>>> esp.on_off_light.on_off.current_level
```

**3. Set and get lighting color**

```
>>> esp.color_temperature_light.color.move_to_hue(108)
>>> esp.color_temperature_light.color.current_hue
>>> esp.color_temperature_light.color.move_to_saturation(50)
>>> esp.color_temperature_light.color.current_saturation
```

**4. Factory reset**

```
>>> esp.factory_reset()
```

**5. Push button**

```
>>> esp.pw_rpc_button.push(button_id=0)
```

**6. WiFi connection manipulation and properties**

```
>>> esp.pw_rpc_wifi.mac_address
>>> esp.pw_rpc_wifi.connect("ssid_wpa2_psk_name", "WIFI_AUTH_WPA2_PSK", "wifi_password")
>>> esp.pw_rpc_wifi.ipv4_address
>>> esp.pw_rpc_wifi.disconnect()
```
