# Set up Raspberry Pi as a host for GDM

GDM can run on Raspberry Pi 3 and 4.

Supported kernel images: Ubuntu (tested with 64-bit 20.04 LTS). \
Note that the Raspbian image is **not** supported as a host for GDM. It has
issues with detection of serial devices.

## Setup

1. Flash the Ubuntu Server 20.04 LTS image onto an SD card. Refer to
   https://www.raspberrypi.org/documentation/installation/installing-images/
   for instructions.
2. [Optional] Edit the network config to automatically connect the RPi to Wi-Fi.
   1. Open the "network-config" file on the SD card and uncomment the following
      lines:

      ```
      #wifis:
      #  wlan0:
      #    dhcp4: true
      #    optional: true
      #    access-points:
      #      myhomewifi:
      #        password: "S3kr1t"
      ```

   2. Replace `myhomewifi` with the SSID of your Wi-Fi network and set the
      password accordingly.
   3. Note that you'll need to reboot the RPi (`reboot`) after the first login
      to make it connect to Wi-Fi.
3. Boot up the Raspberry Pi from the SD card.
4. Change the default password for the "ubuntu" user.
5. Install GDM on RPi:

   ```shell
   curl -OL https://github.com/google/gazoo-device/releases/latest/download/gdm-install.sh
   sh gdm-install.sh
   ```

6. Verify GDM installed successfully:

   ```shell
   gdm -v
   gdm devices
   ```
