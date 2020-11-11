# Device setup for GDM

Devices used by Gazoo Device Manager can require a special setup
procedure. Refer to the relevant subsection for device-specific setup
instructions.

## Table of contents

1. [Cambrionix USB Hub](#cambrionix-usb-hub)
2. [Raspberry Pi (as a supporting device)](#raspberry-pi-as-a-supporting-device)
3. [Raspberry Pi (as a host)](#raspberry-pi-as-a-host)
4. [Unifi PoE Switch](#unifi-poe-switch)
5. [DLI Web Power Switch](#dli-web-power-switch)

## Cambrionix USB Hub

Manufacturer: https://www.cambrionix.com/.

Supported models: PP15, PP8, U16S.

Port numbers:
![Cambrionix PP8 Port Numbers](images/cambrionix_pp8.jpg)
![Cambrionix PP15 Port Numbers](images/cambrionix_pp15.jpg)

### Setup

There are no special setup steps. \
To detect the Cambrionix, run `gdm detect`.

### Usage

```
gdm issue cambrionix-1234 - switch-power - power-off 2
gdm issue cambrionix-1234 - switch-power - get-mode 2
gdm issue cambrionix-1234 - switch-power - power-on 2
gdm issue cambrionix-1234 - switch-power - get-mode 2
gdm man cambrionix  # To see all supported functionality
```

## Raspberry Pi (as a supporting device)

Supported models: Raspberry Pi 3 and 4.

Supported kernel images: Raspbian.

### Setup

1. Flash SD card with the Raspbian kernel.
2. Boot the Pi from the SD card.
3. Open the RPi configuration utility: `sudo raspi-config` (from RPi)
    1. Change the default password ("Change User Password")
    2. Enable SSH ("Interfacing Options" -> "SSH")
    3. Connect to Wi-Fi ("Network Options" -> "WLAN")
    4. Select "Finish" to exit the configuration utility
    5. Reboot the RPi: `reboot`
4. Install GDM SSH keys: `gdm download-keys` (on the host)
5. Set up passwordless SSH with RPi using the GDM key (on the host):
    ```
    ssh-copy-id -i /gazoo/gdm/keys/raspberrypi3_ssh_key.pub pi@<IP_ADDRESS>
    ```
    * For Mac hosts:
      ```
      ssh-copy-id -i ~/gdm/keys/raspberrypi3_ssh_key.pub pi@<IP_ADDRESS>
      ```
6. Check that the RPi is accessible from the host:
    1. `ping <IP_ADDRESS>`
    2. `ssh -i /gazoo/gdm/keys/raspberrypi3_ssh_key.pub pi@<IP_ADDRESS>`
       * For Mac hosts: `ssh -i ~/gdm/keys/raspberrypi3_ssh_key.pub pi@<IP_ADDRESS>`
7. Detect the RPi: `gdm detect --static_ips=<IP_ADDRESS>`

### Usage

```
gdm issue raspberrypi-1234 - shell "echo 'foo'"
gdm issue raspberrypi-1234 - firmware-version
gdm issue raspberrypi-1234 - reboot
echo "Example file" > /tmp/foo.txt
gdm issue raspberrypi-1234 - file-transfer - send-file-to-device --src=/tmp/foo.txt --dest=/tmp
gdm man raspberrypi  # To see all supported functionality
```

## Raspberry Pi (as a host)

Supported models: Raspberry Pi 3 and 4.

Supported kernel images: Ubuntu (tested with 64-bit 20.04 LTS). \
Note that the Raspbian image is **not** supported as a host for GDM. It
has issues with detection of serial devices.

### Setup

1. Flash the Ubuntu Server 20.04 LTS image onto an SD card.
2. [Optional] Edit the network config to automatically connect the RPi
   to Wi-Fi:
   * Open "network-config" on the SD card and uncomment the following lines:
     ```
     #wifis:
     #  wlan0:
     #    dhcp4: true
     #    optional: true
     #    access-points:
     #      myhomewifi:
     #        password: "S3kr1t"
     ```
   * Replace `myhomewifi` with the SSID of your Wi-Fi network and set
     the password accordingly.
   * Note that you'll need to reboot the RPi (`reboot`) after the first
     login to make it connect to Wi-Fi.
3. Boot up the Raspberry Pi from the SD card.
4. Change the default password for the "ubuntu" user.
5. Install GDM on RPi:
    1. `curl -OL https://github.com/google/gazoo-device/releases/latest/download/gdm-install.sh`
    2. `sh gdm-install.sh`
6. Verify GDM installed successfully:
   ```
   gdm -v
   gdm devices
   ```

## Unifi PoE Switch

Supported models: Unifi PoE switches US-8-150W, US-16-150W, US-24-250W,
US-24-500W, US-48-500W, US-48-750W (only [US‑8‑150W](https://www.ui.com/unifi-switching/unifi-switch-8-150w/)
has been tested).

### Setup

1. Install Unifi Controller:
   ```
   sudo apt-get update
   sudo apt-get install ca-certificates wget -y
   wget https://get.glennr.nl/unifi/install/install_latest/unifi-latest.sh
   sh unifi-latest.sh
   # Verify Unifi Controller is running
   ps -u unifi
   ```
2. Navigate to https://localhost:8443 in a browser to configure the
   switch.
3. Follow the UniFi setup Wizard. Set the Time zone, and provide the
   administrator account information. Set the Controller Name.
4. Select "Switch to Advanced Setup". Toggle off both "Enable Remote
   Access" and "Use your Ubiquiti account for local access" and enter
   your credentials.
5. Accept the defaults and click "Next".
6. Select the Unifi Switch to configure.
   * If no devices show up don’t worry. You can manually provision the
     device after the Unifi Controller initial setup is complete.
7. Input "WiFi Name" and "Wifi Password".
8. Set country and timezone.

If you were unable to see a Unifi Switch during the setup of the Unifi
Controller you provision the device following these instructions. Before
provisioning the Unifi_Switch make sure:
* The Unifi_Switch and the Unifi Controller (device running the Unifi
  Controller software) are on the same VLAN.
* The Unifi_Switch is not already associated with a different Unifi
  Controller.
  * If the Unifi_Switch is already associated with a different Unifi
    Controller you can:
    1. Factory Reset the Unifi_Switch via the ‘reset’ button at the
       front.
    2. SSH to the Unifi_Switch and in the Unifi CLI run command
       `set-default` to deallocate the device from the previous Unifi
       Controller by restoring settings to factory defaults.

To provision a Unifi_Switch:
1. Login to the Unifi Controller GUI
   1. In a web browser navigate to <Unifi Controller host IP>:8443
   2. Select "Device" on the First Page.
   3. Select "Adopt" to adopt the Unifi_Switch by the Unifi Controller.
      * It will take a bit of time and the Unifi_Switch status will go
        from "Pending Adoption" to "Provisioning" and then to
        "Connected".
      * The switch will do a factory reset during the adoption.

Install the GDM public SSH key on the Unifi switch:
1. Run `gdm download-keys` to install keys on the host.
2. Log into the Unifi Controller web interface (open
   <Unifi Controller host IP>:8443 in a browser).
3. Navigate to "Settings" (gear icon) -> "Try new settings" ->
   "SSH keys" -> "Add new SSH key".
4. Name the key "unifi_switch_ssh_key".
5. Copy the content of /gazoo/gdm/keys/unifi_switch_ssh_key.pub
   (~/gdm/keys/ on Macs) into the "Key" field.
6. Click "Apply" and "Apply Changes".

Detect the Unifi switch:
```
gdm detect --static_ips <IP of Unifi switch>
```

### Usage

```
gdm issue unifi_switch-1234 - switch_power - power_off --port 0
gdm issue unifi_switch-1234 - switch_power - get_mode --port 0
gdm issue unifi_switch-1234 - switch_power - power_on --port 0
gdm issue unifi_switch-1234 - switch_power - get_mode --port 0
gdm man unifi_switch  # To see all supported functionality
```

## DLI Web Power Switch

Supported model: [DLI Web Power Switch Pro](https://dlidirect.com/products/new-pro-switch).

### Setup

1. Connect the switch to a network (Wi-Fi or via Ethernet).
2. Configure the power switch to enable REST API:
   1. Open the power switch web interface in a browser and log in.
      The default IP is 192.168.0.100. The user name is "admin".
      The default password is "1234".
   2. Navigate to "External APIs" and select "Allow REST-style API".
3. Detect the power switch: `gdm detect --static_ips=<IP_ADDRESS_OF_POWER_SWITCH>`.

### Usage

Note: Powerswitch labels its ports 1 - 8, but ports are addressed 0 - 7
in GDM.

```
gdm issue powerswitch-3570 - switch_power - power_off --port 0
gdm issue powerswitch-3570 - switch_power - get_mode --port 0
gdm issue powerswitch-3570 - switch_power - power_on --port 0
gdm issue powerswitch-3570 - switch_power - get_mode --port 0
gdm man powerswitch  # To see all supported functionality
```
