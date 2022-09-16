# GDM device setup: Raspberry Pi (as a supporting device)

Supported models: Raspberry Pi 3 and 4.

Supported kernel images: Raspbian.

## Setup

1.  Flash SD card with the Raspbian kernel. Refer to
    https://www.raspberrypi.org/documentation/installation/installing-images/
    for instructions.

2.  Boot the Pi from the SD card.

3.  Open the RPi configuration utility: `sudo raspi-config` (from RPi)

    1.  Change the default password ("Change User Password")
    2.  Enable SSH ("Interfacing Options" -> "SSH")
    3.  Connect to Wi-Fi ("Network Options" -> "WLAN")
    4.  Select "Finish" to exit the configuration utility
    5.  Reboot the RPi: `reboot`

4.  Follow the Raspbian instructions from
    [Raspberry_Pi_SSH_key_setup](./Raspberry_Pi_SSH_key_setup.md) to ensure that
    GDM can detect the raspberry pi as a `raspberrypi`

5.  Detect the RPi: `gdm detect --static_ips=<IP_ADDRESS>`

## Usage

```shell
gdm issue raspberrypi-1234 - shell "echo 'foo'"
gdm issue raspberrypi-1234 - firmware_version
gdm issue raspberrypi-1234 - reboot
echo "Example file" > /tmp/foo.txt
gdm issue raspberrypi-1234 - file_transfer - send_file_to_device --src=/tmp/foo.txt --dest=/tmp
gdm man raspberrypi  # To see all supported functionality
```

## Troubleshooting

If `gdm detect` detection fails (couldn't recognize your Raspberry Pi), check
if your device is still pingable first:

```
ping <IP_ADDRESS>
```

If it's alive, try the following commands on your host:

```
ssh -T -oPasswordAuthentication=no -oStrictHostKeyChecking=no -oBatchMode=yes -oConnectTimeout=3 -i /gazoo/gdm/keys/gazoo_device_controllers/raspberrypi3_ssh_key pi@<IP_ADDRESS>
```

If it shows permission denied failure, you'll need to manually add the new host
key to RPi's authorized keys.

```
ssh-copy-id -i ~/gazoo/gdm/keys/gazoo_device_controllers/raspberrypi3_ssh_key.pub pi@<IP_ADDRESS>
```
