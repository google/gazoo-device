# GDM device setup: Matter(CHIP) locking sample app on ESP32 dev board

Manufacturer: https://www.espressif.com/en/products/socs/esp32

Supported models: ESP32 M5Stack

## Setup

**1. Clone Matter Repo**

Clone the source (master) from the Matter repository
https://github.com/project-chip/connectedhomeip and do submodule update.

Inside your own `${project}` directory:

```
git clone https://github.com/project-chip/connectedhomeip.git
cd connectedhomeip
git submodule update --init
```

**2. Clone Espressif ESP-IDF tool**

We'll need ESP-IDF for environment setup and image compilation.

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

**3. Build**

Build the Matter locking sample app image with Pigweed RPC debug interface for
ESP32 M5Stack with ESP-IDF tool. Follow the instructions on
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

**4. Flash**

Flash the image to the ESP32 M5Stack, follow the instructions on
[README](https://github.com/project-chip/connectedhomeip/tree/master/examples/lock-app/esp32#building-the-example-application)
or the below commands:

Inside the same build folder, `${device-address}` should be something like
`/dev/tty/ACM0`

```
idf.py -p ${device-address} flash monitor
```

**5. (Optional) Try RPC**

Try if the Locking endpoints work in the interactive console.

Launch an interactive console and send RPCs to the locking app, follow the
instructions on
[README](https://github.com/project-chip/connectedhomeip/tree/master/examples/lock-app/esp32#using-the-rpc-console)
or the below commands:

Build and install the
[CHIP RPC console](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/rpc_console/README.md).
Device address should be something like /dev/tty/ACM0

```
python -m chip_rpc.console --device ${device-address}
```

Inside interactive console:

```
// Lock the device
In [1]: rpcs.chip.rpc.Locking.Set(locked=True)
// Unlock the device
In [2]: rpcs.chip.rpc.Locking.Set(locked=False)
// Get locked state
In [3]: rpcs.chip.rpc.Locking.Get()
```

**6. Device detection**

Detect the ESP32 locking app: `gdm detect`

```
    Device                     Alias           Type                 Model                Connected
    -------------------------- --------------- -------------------- -------------------- ----------
    esp32matterlocking-b69b   <undefined>      esp32matterlocking   PROTO                connected

    Other Devices              Alias           Type                 Model                Available
    -------------------------- --------------- -------------------- -------------------- ----------
```

## Usage

Using GDM CLI

```
gdm issue esp32matterlocking-b69b - pw_rpc_lock - lock  # Lock the device
gdm issue esp32matterlocking-b69b - pw_rpc_lock - unlock  # Unlock the device
gdm issue esp32matterlocking-b69b - pw_rpc_lock - state  # Get locked state
gdm man esp32matterlocking  # To see all supported functionality
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
>>> esp = m.create_device('esp32matterlocking-b69b')
>>> esp.pw_rpc_lock.lock()
>>> esp.pw_rpc_lock.state
>>> esp.close()
```

## Supported endpoints

The latest supported locking endpoints in GDM based on the Matter
[locking proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/locking_service.proto)
and
[device proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/device_service.proto).

**1. Lock/unlock and get locked state**

```
>>> esp.pw_rpc_lock.lock()
>>> esp.pw_rpc_lock.unlock()
>>> esp.pw_rpc_lock.state
```

**2. Reboot and factory reset**

```
>>> esp.reboot()
>>> esp.factory_reset()
```
