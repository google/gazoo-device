# GDM device setup: Matter(CHIP) lighting sample app on EFR32 dev board

Manufacturer: https://www.silabs.com/

Supported models: EFR32MG

## Setup

1.  Clone the source from the Matter repository
    (https://github.com/project-chip/connectedhomeip) and build the Matter
    lighting sample app image with Pigweed RPC debug interface for EFR32:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/efr32#building

2.  Flash the image to the EFR32:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/efr32#flashing-the-application

3.  (Optional) Try if the Lighting endpoints work in the interactive console:
    follow the instructions to launch an interactive console and send RPCs to
    the lighting app:
    https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/efr32#running-pigweed-rpc-console

4.  Detect the EFR32 lighting app: `gdm detect`

```shell
    Device                     Alias           Type                 Model                Connected
    -------------------------- --------------- -------------------- -------------------- ----------

    Other Devices              Alias           Type                 Model                Available
    -------------------------- --------------- -------------------- -------------------- ----------
    efr32pigweedlighting-3453  <undefined>     efr32pigweedlighting PROTO                available
```

## Usage

```shell
gdm issue efr32pigweedlighting-3453 - pw_rpc_light - on  # Turn the light on
gdm issue efr32pigweedlighting-3453 - pw_rpc_light - state  # Check the light state
gdm issue efr32pigweedlighting-3453 - pw_rpc_light - off  # Turn the light off
gdm issue efr32pigweedlighting-3453 - factory_reset
gdm issue efr32pigweedlighting-3453 - reboot
gdm issue efr32pigweedlighting-3453 - pw_rpc_common - vendor_id
gdm issue efr32pigweedlighting-3453 - pw_rpc_common - product_id
gdm issue efr32pigweedlighting-3453 - pw_rpc_common - software_version
gdm man efr32pigweedlighting  # To see all supported functionality
```
