# GDM device setup: Matter(CHIP) locking sample app on ESP32 dev board

Manufacturer: https://www.espressif.com/en/products/socs/esp32

Supported models: ESP32 M5Stack

## Setup

1.  Clone the source from the Matter repository
    (https://github.com/project-chip/connectedhomeip) and build the Matter
    locking sample app image with Pigweed RPC debug interface for ESP32 M5Stack:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/lock-app/esp32#building-the-example-application

2.  To enable the Pigweed config option, follow the steps: `idf.py menuconfig`
    -> Component config -> CHIP Core -> General options -> Enable pigweed RPC
    library

3.  Flash the image to the ESP32 M5Stack:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/lock-app/esp32#building-the-example-application

4.  (Optional) Try if the Locking endpoints work in the interactive console:
    follow the instructions to launch an interactive console and send RPCs to
    the locking app, please refer to the lighting app example:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/efr32#running-pigweed-rpc-console.
    The locking service proto is at:
    https://github.com/project-chip/connectedhomeip/blob/master/examples/lock-app/esp32/main/locking_service.proto

5.  Detect the ESP32 locking app: `gdm detect`

```shell
    Device                     Alias           Type                 Model                Connected
    -------------------------- --------------- -------------------- -------------------- ----------

    Other Devices              Alias           Type                 Model                Available
    -------------------------- --------------- -------------------- -------------------- ----------
    esp32pigweedlocking-b69b   <undefined>     esp32pigweedlocking  PROTO                available
```

## Usage

```shell
gdm issue esp32pigweedlocking-b69b - pw_rpc_lock - lock  # Lock the device
gdm issue esp32pigweedlocking-b69b - pw_rpc_lock - unlock  # Unlock the device
gdm issue esp32pigweedlocking-b69b - pw_rpc_lock - state  # Get locked state
gdm man nrfpigweedlighting  # To see all supported functionality
```
