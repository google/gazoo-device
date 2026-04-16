# OpenThread sample app on Nordic dev board

Manufacturer: [Nordic Semiconductor](https://www.nordicsemi.com)

Supported models: NRF52840 DK

## Setup

**1. Get Build**

**2. Flash**

Flash the image to the NRF52840 DK by using the
[nRF command line tools](https://www.nordicsemi.com/Products/Development-tools/nrf-command-line-tools/download)
(download the binary and make sure `nrfjprog` exists in your `$PATH`), follow
the instructions on
[OpenThread codelab](https://openthread.io/codelabs/openthread-hardware#4) or
the below commands:

```
nrfjprog -f nrf52 --program ${image_file}.hex --sectorerase -s ${serial-number}
nrfjprog -f nrf52 --reset -s ${serial-number}
```

You may also use GDM python interpreter for flashing:

The device needs to be detected first (depending on the present image, as a
plain `nrf52840` or as `nrfopenthread`):

```
gdm detect
```

Create the device class and flash the build:

```
>>> nrf = m.create_device('nrf52840-3453')
>>> nrf.flash_build.flash_device(['/path/to/nrf52840_sample_app.hex'])
```

(We can also use GDM CLI for flashing: `gdm issue nrf52840-3453 - flash_build -
upgrade --build_file=/path/to/nrf52840_sample_app.hex`)

After flashing it'll need to be redetected (if going from `nrf52840` to
`nrfopenthread`).

```
gdm delete nrf52840-3453
gdm detect
```

**3. Device detection**

Detect the NRF Matter sample app: `gdm detect`

```
Other Devices                  Alias           Type                     Model                Available
------------------------------ --------------- ------------------------ -------------------- ----------
nrfopenthread-3453             <undefined>     nrfopenthread            PROTO                available
```

**4. (Recommended) Remove on-board CR2032 coin cell battery**

The coin cell [battery](images/nrf52840_battery.png) on the back of the board is
an alternate power source for the board. When used in a testbed setup, the
battery is not needed. If the board is connected to a Cambrionix, removing the
battery. Removing the battery enables the board to be power cycled
programmatically using

```
device.device_power.off()
device.device_power.on()
```

Which is useful to recover the device from unresponsiveness.

## Usage

Using the CLI

```
gdm issue nrfopenthread-5732 - wpan - factory_reset
gdm issue nrfopenthread-5732 - wpan - csl_period
gdm issue nrfopenthread-5732 - flash_build - upgrade --build_file=/path/to/nrf52840_sample_app.hex
gdm man nrfopenthread-5732  # To see all supported functionality
```

Or inside the python console

Activate GDM virtual env and open the console:

```
source ~/gazoo/gdm/virtual_env/bin/activate
python3
```

Inside python console:

```
>>> from gazoo_device import Manager
>>> m = Manager()
>>> nrf = m.create_device('nrfopenthread-5732')
>>> nrf.wpan.factory_reset()
>>> nrf.wpan.csl_period
>>> nrf.flash_build.upgrade('/path/to/nrf52840_sample_app.hex')
>>> nrf.close()
```
