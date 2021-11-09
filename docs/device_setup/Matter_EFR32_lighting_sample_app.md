# GDM device setup: Matter(CHIP) lighting sample app on EFR32 dev board

Manufacturer: https://www.silabs.com/

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

Build the Matter lighting sample app image with Pigweed RPC debug interface for
EFR32 with `gn` command line tool, make sure it's in your path:
[clone gn](https://gn.googlesource.com/gn/)

Follow the instructions on
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

**4. (Optional) Try RPC**

Try if the Lighting endpoints work in the interactive console.

Launch an interactive console and send RPCs to the lighting app, follow the
instructions on
[README](https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/efr32#running-pigweed-rpc-console)
or the below commands:

Activate GDM virtual env and enable RPC console: `${device-address}` should be
something like `/dev/tty/ACM0`

```
source ~/gazoo/gdm/virtual_env/bin/activate
python -m lighting_app.rpc_console -d ${device-address} -b 115200 -o /tmp/pw.log
```

Inside interactive console:

```
// Turn on the light
In [1]: rpcs.chip.rpc.Lighting.Set(on=True)
// Turn off the light
In [2]: rpcs.chip.rpc.Lighting.Set(on=False)
// Get light state
In [3]: rpcs.chip.rpc.Lighting.Get()
```

**5. Device detection**

Detect the EFR32 lighting app: `gdm detect`

```
    Device                     Alias           Type                 Model                Connected
    -------------------------- --------------- -------------------- -------------------- ----------

    Other Devices              Alias           Type                 Model                Available
    -------------------------- --------------- -------------------- -------------------- ----------
    efr32pigweedlighting-3453  <undefined>     efr32pigweedlighting PROTO                available
```

## Usage

Using GDM CLI

```
gdm issue efr32pigweedlighting-3453 - pw_rpc_light - on  # Turn the light on
gdm issue efr32pigweedlighting-3453 - pw_rpc_light - state  # Check the light state
gdm issue efr32pigweedlighting-3453 - pw_rpc_light - off  # Turn the light off
gdm issue efr32pigweedlighting-3453 - pw_rpc_button - push 0  # Push button 0
gdm issue efr32pigweedlighting-3453 - factory_reset
gdm issue efr32pigweedlighting-3453 - reboot
gdm issue efr32pigweedlighting-3453 - pw_rpc_common - vendor_id
gdm issue efr32pigweedlighting-3453 - pw_rpc_common - product_id
gdm issue efr32pigweedlighting-3453 - pw_rpc_common - software_version
gdm man efr32pigweedlighting  # To see all supported functionality
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
>>> efr = m.create_device('efr32pigweedlighting-3453')
>>> efr.pw_rpc_light.on()
>>> efr.pw_rpc_light.state
>>> efr.close()
```

## Supported endpoints

The latest supported lighting endpoints in GDM based on the Matter
[lighting proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/lighting_service.proto)
and
[device proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/device_service.proto).

**1. Turn on/off the light and get light state**

```
>> efr.pw_rpc_light.on()
>> efr.pw_rpc_light.off()
>> efr.pw_rpc_light.state
```

**2. Set and get brightness level**

```
>> efr.pw_rpc_light.on(level=100)
>> efr.pw_rpc_light.brightness
```

**3. Set and get lighting color**

```
>>> efr.pw_rpc_light.on(hue=50, saturation=30)
>>> efr.pw_rpc_light.color.hue
>>> efr.pw_rpc_light.color.saturation
```

**4. Push buttons on the board**

```
// Push button 0
>>> efr.pw_rpc_button.push(button_id=0)
```

**5. Reboot and factory reset**

```
>>> efr.reboot()
>>> efr.factory_reset()
```
