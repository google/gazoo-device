# GDM device setup: Matter(CHIP) lighting sample app on NRF dev board

Manufacturer: https://www.nordicsemi.com/

Supported models: NRF52840 DK

## Setup

1.  Clone the source from the Matter repository
    (https://github.com/project-chip/connectedhomeip) and build the Matter
    lighting sample app image with Pigweed RPC debug interface for NRF DK:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/nrfconnect#building-with-pigweed-rpcs

2.  Flash the image to the NRF52840 DK:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/nrfconnect#flashing-and-debugging

3.  (Optional) Try if the Lighting endpoints work in the interactive console:
    follow the instructions to launch an interactive console and send RPCs to
    the lighting app:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/efr32#running-pigweed-rpc-console

4.  Detect the NRF lighting app: `gdm detect`

```shell
    Device                     Alias           Type                 Model                Connected
    -------------------------- --------------- -------------------- -------------------- ----------

    Other Devices              Alias           Type                 Model                Available
    -------------------------- --------------- -------------------- -------------------- ----------
    nrfpigweedlighting-6125    <undefined>     nrfpigweedlighting   PROTO                available
```

## Usage

```shell
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
