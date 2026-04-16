# GDM device setup: Cambrionix USB hub

Manufacturer: https://www.cambrionix.com/.

Supported models: PP8S, PP15S, PS15-USB3, SuperSync15, SuperSync15b, U16S,
ThunderSync3-16.

Port numbers: ![Cambrionix PP8 Port Numbers](images/cambrionix_pp8.jpg)
![Cambrionix PP15 Port Numbers](images/cambrionix_pp15.jpg)
![Cambrionix SuperSync15 Port Numbers](images/cambrionix_supersync15.jpg)

## Setup

There are no special setup steps. \
To detect the Cambrionix, run `gdm detect`.

## Usage

```shell
gdm issue cambrionix-1234 - switch_power - power_off 2
gdm issue cambrionix-1234 - switch_power - get_mode 2
gdm issue cambrionix-1234 - switch_power - power_on 2
gdm issue cambrionix-1234 - switch_power - get_mode 2
# To see all supported functionality:
gdm man cambrionix
gdm man cambrionix switch_power
```
