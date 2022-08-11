# GDM Device Setup: D-Link Switch

Supported models:

*   [D-Link 8-Port EasySmart Gigabit Ethernet Switch (DGS-1100-08) ](https://www.amazon.com/gp/product/B008ABLU2I/ref=ppx_yo_dt_b_asin_title_o02_s00?ie=UTF8&psc=1)
*   [D-Link 5-Port EasySmart Gigabit Ethernet Switch (DGS-1100-05) ](https://www.amazon.com/gp/product/B00AKRTLXA/ref=ppx_yo_dt_b_asin_title_o02_s00?ie=UTF8&psc=1)

## Setup

### Connecting to the Switch

*   Power on the switch and connect it to the host machine:
    *   If it is not a brand new switch, a factory reset is recommended before
        proceeding further.
    *   Factory reset the switch by pressing and holding the reset button on the
        back for 10 seconds.
*   Disconnect all devices connected over Ethernet from host machine.

*   Connect a laptop to the switch.
    *   This laptop will be used one time to assign a static IP to the switch
        that the host machine can use to reach the switch.
    *   You should now have your host machine and laptop connected to the switch
        over Ethernet.

*   Turn off your laptop's WiFi.

**NOTE:** The following instructions will assume you are using a Macbook, but
any laptop with configurable network preferences should work.

*   Navigate to "System Preferences → Networks".
*   Select your ethernet connection to the switch and select to "Manually"
    assign an IP Address.

*   Assign an IP ADRESS like `192.168.0.95` and SUBNET MASK: '255.0.0.0'

*   Navigate to your browser and open an incognito window. Log in to the switch
    by navigating your browser to `192.168.0.90`.

*   For a factory reset device, the password should be `admin`.

*   On the switch page, navigate to "System → System Information Settings → IPV4
    Interface".

*   Select "Static" under "IP Settings" and manually assign an IP ADDRESS which
    will be used by the host machine to access the switch.

Assign configs like:

*   IP ADDRESS: `192.168.0.90`
*   MASK: `255.255.255.0`
*   GATEWAY: `192.168.0.1`
*   Hit the "Apply" button

*   On Mac laptop, navigate to "System Preferences → Networks" and change the
    Ethernet interface connection type from "Manually" to "Using DHCP".

*   The Mac laptop will register the same IP address you just set via the
    switch's GUI. Your laptop and host machine can now address the switch via
    the IP address you set.

### Enabling SNMPv2c

*   Log in to the switch by returning back to your incognito browser window and
    navigating to the static IP address you set in prior steps.

NOTE: HIT the *Apply* button after enabling each of the following settings.

*   Navigate to "Management --> SNMP --> SNMP Global Settings"

    *   Enable SNMP Global State.
    *   Disable Trap Global State
    *   Hit *Apply*.

*   Navigate to "Management --> SNMP --> SNMP Community Table Settings"

    *   Enable private Read-Write access.
    *   Enable public Read-Only access.
    *   Hit *Apply*

*   Navigate to "Management --> SNMP --> SNMP Host Settings"

    *   Set a Host IPv4 Address.
    *   Set User-based Security Model to SNMPv2c.
    *   Set community string to private.
    *   Hit *Apply*.

*   Save the configuration on the switch by clicking the save icon in the upper
    left corner.

    *   This will ensure these settings remain persistent after switch reboots.

### Detect the Switch With GDM

*   Detect the D-Link switch via GDM:

    ```shell
      $ gdm detect --static_ips=<IP_ADDRESS_OF_DLINK_SWITCH>
    ```

*   Run `$ gdm devices` and ensure that the D-Link switch is populated in the
    Other Devices section:

    ```shell
      $ gdm devices

      Device                         Alias           Type                     Model                Connected
      ------------------------------ --------------- ------------------------ -------------------- ----------

      Other Devices                  Alias           Type                     Model                Available
      ------------------------------ --------------- ------------------------ -------------------- ----------
      dlink_switch-3.90              <undefined>     dlink_switch             DGS-1100 Gigabit Ethernet Switch available

    ```

**~ THE DLINK SWITCH IS NOW READY TO USE! ~**

## Usage

### switch_power

Note: Ports are defined as 1-5 or 1-8 depending on the model.

*   GET mode of port 1: `$ gdm issue dlink_switch-3.90 - switch_power get_mode
    1`

*   POWER ON port 1: `$ gdm issue dlink_switch-3.90 - switch_power power_on 1`

*   POWER OFF port 1: `$ gdm issue dlink_switch-3.90 - switch_power power_off 1`


## Troubleshooting

### I cannot log into the switch after factory resetting the switch

*   If you are having trouble logging into the device after factory reset,
    ensure you are navigating to the IP address with http as opposed to https.

### GDM Cannot detect my switch

*   Ensure that `snmp` is installed on you host machine
    `sudo apt-get install snmp`. If it was not, re-detect the switch after
     installation.

