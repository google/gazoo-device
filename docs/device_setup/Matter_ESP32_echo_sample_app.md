# GDM device setup: Matter(CHIP) echo sample app on ESP32 dev board

Manufacturer: https://www.espressif.com/en/products/socs/esp32

Supported models: ESP32 M5Stack

## Setup

1.  Clone the source from the Matter repository
    (https://github.com/project-chip/connectedhomeip) and build the Matter echo
    sample app image with Pigweed RPC debug interface for ESP32 M5Stack:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/pigweed-app/esp32#building-the-example-application

2.  Flash the image to the ESP32 M5Stack:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/pigweed-app/esp32#building-the-example-application

3.  (Optional) Try if the Echo endpoints work in the interactive console: follow
    the instructions to launch an interactive console and send RPCs to the echo
    app:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/pigweed-app/esp32#testing-the-example-application

4.  Detect the ESP32 echo app: `gdm detect`

```shell
    Device                     Alias           Type                 Model                Connected
    -------------------------- --------------- -------------------- -------------------- ----------

    Other Devices              Alias           Type                 Model                Available
    -------------------------- --------------- -------------------- -------------------- ----------
    esp32pigweedecho-b69b      <undefined>     esp32pigweedecho     PROTO                available
```

## Usage

```shell
gdm issue esp32pigweedecho-b69b - pw_rpc_echo - echo "Hello World"  # Trigger the Echo app
gdm man esp32pigweedecho  # To see all supported functionality
```
