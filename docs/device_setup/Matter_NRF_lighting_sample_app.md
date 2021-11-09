# GDM device setup: Matter(CHIP) lighting sample app on NRF dev board

Manufacturer: https://www.nordicsemi.com/

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

Build the Matter lighting sample app image with Pigweed RPC debug interface for
NRF DK. Recommend using Docker container for setup.

Follow the instructions on
[README](https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/nrfconnect#building-with-pigweed-rpcs)
or the below detailed commands:

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
nrfjprog --program ${image_file}.hex -f NRF52 --snr ${DK serial-number} --sectoranduicrerase
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

Detect the NRF lighting app: `gdm detect`

```
    Device                     Alias           Type                 Model                Connected
    -------------------------- --------------- -------------------- -------------------- ----------

    Other Devices              Alias           Type                 Model                Available
    -------------------------- --------------- -------------------- -------------------- ----------
    nrfpigweedlighting-6125    <undefined>     nrfpigweedlighting   PROTO                available
```

## Usage

Using GDM CLI

```
gdm issue nrfpigweedlighting-6125 - pw_rpc_light - on  # Turn the light on
gdm issue nrfpigweedlighting-6125 - pw_rpc_light - state  # Check the light state
gdm issue nrfpigweedlighting-6125 - pw_rpc_light - off  # Turn the light off
gdm issue nrfpigweedlighting-6125 - pw_rpc_button - push 0  # Push button 0
gdm issue nrfpigweedlighting-6125 - factory_reset
gdm issue nrfpigweedlighting-6125 - reboot
gdm issue nrfpigweedlighting-6125 - pw_rpc_common - vendor_id
gdm issue nrfpigweedlighting-6125 - pw_rpc_common - product_id
gdm issue nrfpigweedlighting-6125 - pw_rpc_common - software_version
gdm man nrfpigweedlighting  # To see all supported functionality
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
>>> nrf = m.create_device('nrfpigweedlighting-6125')
>>> nrf.pw_rpc_light.on()
>>> nrf.pw_rpc_light.state
>>> nrf.close()
```

## Supported endpoints

The latest supported lighting endpoints in GDM based on the Matter
[lighting proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/lighting_service.proto)
and
[device proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/device_service.proto).

**1. Turn on/off the light and get light state**

```
>>> nrf.pw_rpc_light.on()
>>> nrf.pw_rpc_light.off()
>>> nrf.pw_rpc_light.state
```

**2. Set and get brightness level**

```
>>> nrf.pw_rpc_light.on(level=100)
>>> nrf.pw_rpc_light.brightness
```

**3. Set and get lighting color**

```
>>> nrf.pw_rpc_light.on(hue=50, saturation=30)
>>> nrf.pw_rpc_light.color.hue
>>> nrf.pw_rpc_light.color.saturation
```

**4. Push buttons on the board**

```
// Push button 0
>>> nrf.pw_rpc_button.push(button_id=0)
```

**5. Reboot and factory reset**

```
>>> nrf.reboot()
>>> nrf.factory_reset()
```
