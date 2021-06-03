# GDM device setup: DLI web power switch

Supported model:
[DLI Web Power Switch Pro](https://dlidirect.com/products/new-pro-switch).

## Setup

1. Connect the switch to a network (Wi-Fi or via Ethernet).
2. Configure the power switch to enable REST API:
   1. Open the power switch web interface in a browser and log in. The default
      IP is 192.168.0.100. The user name is "admin". The default password is
      "1234".
   2. Navigate to "External APIs" and select "Allow REST-style API".
3. Detect the power switch:

   ```shell
   gdm detect --static_ips=<IP_ADDRESS_OF_POWER_SWITCH>
   ```

## Usage

Note: Powerswitch labels its ports 1 - 8, but ports are addressed 0 - 7 in GDM.

```shell
gdm issue powerswitch-3570 - switch_power - power_off --port 0
gdm issue powerswitch-3570 - switch_power - get_mode --port 0
gdm issue powerswitch-3570 - switch_power - power_on --port 0
gdm issue powerswitch-3570 - switch_power - get_mode --port 0
# To see all supported functionality:
gdm man powerswitch
gdm man powerswitch switch_power
```
