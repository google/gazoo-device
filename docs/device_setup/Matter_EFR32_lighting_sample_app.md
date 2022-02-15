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

You may also use GDM for flashing. You'll need to download the `.hex` image from
the above build bot, or manually convert the image from `.s37` to `.hex`
following the
[commander instruction](https://www.silabs.com/documents/public/user-guides/ug162-simplicity-commander-reference-guide.pdf).
Then use GDM python interpreter to flash:

```
>>> from gazoo_device import Manager
>>> m = Manager()
>>> efr = m.create_device('efr32-3453')
>>> efr.flash_build.flash_device(['/path/to/efr32_light.hex'])
```

Or using GDM CLI:

```
gdm issue efr32-3453 - flash_build - upgrade --build_file=/path/to/efr32_light.hex
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
    efr32matterlighting-3453  <undefined>     efr32matterlighting   PROTO                connected

    Other Devices              Alias           Type                 Model                Available
    -------------------------- --------------- -------------------- -------------------- ----------
```

## Usage

Using GDM CLI

```
gdm issue efr32matterlighting-3453 - on_off_light - on_off - on  # Turn the light on
gdm issue efr32matterlighting-3453 - on_off_light - on_off - onoff  # Check the light state
gdm issue efr32matterlighting-3453 - on_off_light - on_off - off  # Turn the light off
gdm issue efr32matterlighting-3453 - pw_rpc_button - push 0  # Push button 0
gdm issue efr32matterlighting-3453 - factory_reset
gdm issue efr32matterlighting-3453 - reboot
gdm issue efr32matterlighting-3453 - pw_rpc_common - vendor_id
gdm issue efr32matterlighting-3453 - pw_rpc_common - product_id
gdm issue efr32matterlighting-3453 - pw_rpc_common - software_version
gdm man efr32matterlighting  # To see all supported functionality
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
>>> efr = m.create_device('efr32matterlighting-3453')
>>> efr.on_off_light.on_off.on()
>>> efr.on_off_light.on_off.onoff
>>> efr.close()
```

## Supported endpoints

The latest supported lighting endpoints in GDM based on the Matter
[lighting proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/lighting_service.proto)
and
[device proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/device_service.proto).

**1. Turn on/off the light and get light state**

```
>>> efr.on_off_light.on_off.on()
>>> efr.on_off_light.on_off.off()
>>> efr.on_off_light.on_off.onoff
```

**2. Set and get brightness level**

```
>>> efr.on_off_light.on_off.move_to_level(level=108)
>>> efr.on_off_light.on_off.current_level
```

**3. Set and get lighting color**

```
>>> efr.color_temperature_light.color.move_to_hue(108)
>>> efr.color_temperature_light.color.current_hue
>>> efr.color_temperature_light.color.move_to_saturation(50)
>>> efr.color_temperature_light.color.current_saturation
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
