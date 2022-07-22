# GDM device setup: Unifi PoE switch

Supported models: Unifi PoE switches US-8-150W, US-16-150W, US-24-250W,
US-24-500W, US-48-500W, US-48-750W (only
[US‑8‑150W](https://www.ui.com/unifi-switching/unifi-switch-8-150w/) has been
tested).

## Setup

1. Install Unifi Controller:

   ```shell
   sudo apt-get update
   sudo apt-get install ca-certificates wget -y
   wget https://get.glennr.nl/unifi/install/install_latest/unifi-latest.sh
   sh unifi-latest.sh
   # Verify Unifi Controller is running
   ps -u unifi
   ```

2. Navigate to https://localhost:8443 in a browser to configure the switch.
3. Follow the UniFi setup Wizard. Set the Time zone, and provide the
   administrator account information. Set the Controller Name.
4. Select "Switch to Advanced Setup". Toggle off both "Enable Remote Access" and
   "Use your Ubiquiti account for local access" and enter your credentials.
5. Accept the defaults and click "Next".
6. Select the Unifi Switch to configure.
   * If no devices show up, don’t worry. You can manually provision the device
     after the Unifi Controller initial setup is complete.
7. Input "WiFi Name" and "Wifi Password".
8. Set country and timezone.

If you were unable to see a Unifi Switch during the setup of the Unifi
Controller you provision the device following these instructions. Before
provisioning the Unifi_Switch make sure:
* The Unifi_Switch and the Unifi Controller (device running the Unifi Controller
  software) are on the same VLAN.
* The Unifi_Switch is not already associated with a different Unifi Controller.
  * If the Unifi_Switch is already associated with a different Unifi Controller,
    you can:
    1. Factory Reset the Unifi_Switch via the ‘reset’ button at the front.
    2. SSH to the Unifi_Switch and in the Unifi CLI run command `set-default` to
       deallocate the device from the previous Unifi Controller by restoring
       settings to factory defaults.

To provision a Unifi_Switch:
1. Login to the Unifi Controller GUI
   1. In a web browser navigate to `<Unifi Controller host IP>:8443`
   2. Select "Device" on the First Page.
   3. Select "Adopt" to adopt the Unifi_Switch by the Unifi Controller.
      * It will take a bit of time and the Unifi_Switch status will go from
        "Pending Adoption" to "Provisioning" and then to "Connected".
      * The switch will do a factory reset during the adoption.

Install the GDM public SSH key on the Unifi switch:

1.  Configure GDM SSH keys: run `gdm download-keys` on the host.
    *   If you don't have a key in
        `~/gazoo/gdm/keys/gazoo_device_controllers/unifi_switch_ssh_key`, you'll
        see an error prompting you to generate a key. Follow the prompt to
        generate all required keys.
        *   Alternatively, you can copy an existing private/public SSH key pair
            to `~/gazoo/gdm/keys/gazoo_device_controllers/unifi_switch_ssh_key`
            and
            `~/gazoo/gdm/keys/gazoo_device_controllers/unifi_switch_ssh_key.pub`.
2.  Log into the Unifi Controller web interface (open `<Unifi Controller host
    IP>:8443` in a browser).
3.  Navigate to "Settings" (gear icon) -> "Try new settings" -> "SSH keys" ->
    "Add new SSH key".
4.  Name the key "unifi_switch_ssh_key".
5.  Copy the contents of
    `~/gazoo/gdm/keys/gazoo_device_controllers/unifi_switch_ssh_key.pub` into
    the "Key" field.
6.  Click "Apply" and "Apply Changes".

Detect the Unifi switch:

```shell
gdm detect --static_ips <IP of Unifi switch>
```

## Usage

```shell
gdm issue unifi_switch-1234 - switch_power - power_off --port 0
gdm issue unifi_switch-1234 - switch_power - get_mode --port 0
gdm issue unifi_switch-1234 - switch_power - power_on --port 0
gdm issue unifi_switch-1234 - switch_power - get_mode --port 0
# To see all supported functionality:
gdm man unifi_switch
gdm man unifi_switch switch_power
```
