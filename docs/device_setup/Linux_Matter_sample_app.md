# Matter linux sample app on Raspberry Pi 4

Supported models: Raspberry Pi 4 with at least 4GB of memory.

Supported kernel images: Ubuntu for Raspberry Pi

## Setup manually

**1. Flash SD card with Ubuntu OS**

Install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your
host, pick up the build of **Ubuntu for Raspberry Pi Server 20.04 LTS (64-bit
server OS for arm64 architectures)** and flash it to your SD card.

**2. Set up wifi on Ubuntu** (You may skip this part if you use ethernet for
connection)

Set up wifi on ubuntu host (note that is different from setting up on Raspbian
kernel): edit the network configuration file `/etc/netplan/50-cloud-init.yaml`
and add your wifi ssid and password. A complete configuration file will look
like:

```
network:
    ethernets:
        eth0:
            dhcp4: true
            optional: true
    version: 2
    wifis:
         wlan0:
            optional: true
            access-points:
                "my-ssid":
                    password: "my-pwd"
            dhcp4: true
```

Save the file and reboot your RPi. You should have your wifi setup once RPi is
up and running again. Use `hostname -I` to obtain the IP address of your RPi.

**3. Set up passwordless SSH configuration**

Ubuntu image only has a default user `ubuntu`. Make sure to login and change the
default password first and follow the Ubuntu instructions from
[Raspberry_Pi_SSH_key_setup](./Raspberry_Pi_SSH_key_setup.md). You should be
able to SSH to your RPi without password after the setup.

```
ssh ubuntu@<pi's IP address>
```

**4. Getting linux sample app build**

Simply follow the build instruction in
[CHIP Linux Lighting Example](https://github.com/project-chip/connectedhomeip/tree/master/examples/lighting-app/linux#chip-linux-lighting-example).

**5. Register sample app as a linux service**

Copy the sample app to your RPi and rename it as `matter-linux-app` under
`/home/ubuntu`. The name and directory must be correct otherwise the GDM
detection won't work.

```
scp chip-lighting-app ubuntu@<pi's IP address>:/home/ubuntu/matter-linux-app
```

Raspberry pi running Ubuntu 22.04 or later may encounter an issue with
incompatible SSL library.

```shell
chip-tool: error while loading shared libraries: libssl.so.1.1: cannot open shared object file: No such file or directory
```

As a workaround, force install `libssl1.1` using the command below:

```
wget http://security.debian.org/pool/updates/main/o/openssl/libssl1.1_1.1.1n-0+deb10u3_arm64.deb
sudo dpkg -i libssl1.1_1.1.1n-0+deb10u3_arm64.deb
```

Create a linux service file `/etc/systemd/system/matter-linux-app.service` (need
`sudo`) and put the following content:

```
[Unit]
Description=Matter Linux Sample App on RPi

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=sudo /home/ubuntu/matter-linux-app
Restart=always

[Install]
WantedBy=multi-user.target
```

To enable and start the service:

```
sudo systemctl enable matter-linux-app.service
sudo systemctl start matter-linux-app.service
```

**6. Device detection**

Detect the Linux Matter sample app: `gdm detect --statics_ips=[<pi's IP
address>]`. The output should be like:

```
Device                         Alias           Type                     Model                Connected
------------------------------ --------------- ------------------------ -------------------- ----------
rpimatter-c0b2                 <undefined>     rpimatter                PROTO                connected

Other Devices                  Alias           Type                     Model                Available
------------------------------ --------------- ------------------------ -------------------- ----------
```

## Usage

### CLI

```
gdm issue rpimatter-c0b2 - pw_rpc_common - qr_code
gdm issue rpimatter-c0b2 - matter_endpoints - list
```

### Python console

Activate GDM virtual env and open the console:

```
source ~/gazoo/gdm/virtual_env/bin/activate
python
```

Inside python console:

```
>>> from gazoo_device import Manager
>>> m = Manager()
>>> pi = m.create_device('rpimatter-c0b2')
>>> pi.pw_rpc_common.qr_code
>>> pi.matter_endpoints.list()
>>> pi.close()
```

### Pigweed RPCs

The linux sample app on RPi supports various Pigweed RPC calls:

**Reboot and factory reset**

```
>>> pi.reboot()
>>> pi.factory_reset()
```

**Get device pairing QR code and state**

```
>>> pi.pw_rpc_common.qr_code
>>> pi.pw_rpc_common.qr_code_url
>>> pi.pw_rpc_common.pairing_state
```

Use `gdm issue rpimatter-c0b2 - pw_rpc_common --help` to see more available
APIs.

### Sample app control and management

The linux sample app controller offers a `matter_sample_app` capability where
the user can control and manage the sample app from RPi:

**Restart the sample app**

```
>>> pi.matter_sample_app.restart()
```

**Register the sample app service**

```
>>> pi.matter_sample_app.enable_service()
```

**Upgrade the sample app**

Note: See the above section **Getting linux sample app build** to get the sample
app binary.

```
>>> pi.matter_sample_app.upgrade("/path/to/the/sample-app-binary")
```

Use `gdm issue rpimatter-c0b2 - matter_sample_app --help` to see more available
APIs. Note that `gdm man rpimatter-c0b2`and `gdm man rpimatter
matter_sample_app` CLI commands also work without connecting to a real device
but the information is not as detailed as the above command.

### Bluetooth service management

**Check bluetooth is active or not**

```
>>> pi.bluetooth_service.status
```

**Start bluetooth service**

```
>>> pi.bluetooth_service.start()
```

**Stop bluetooth service**

```
>>> pi.bluetooth_service.stop()
```

**Restart bluetooth service**

```
>>> pi.bluetooth_service.restart()
```

### Matter endpoints

The linux sample app uses Descriptor cluster to list the supported endpoints on
the device, users can use `matter_endpoints.get` or alias to access the
supported endpoint. Accessing an invalid endpoint will raise a `DeviceError`.
(Invalid endpoint means either: the given endpoint id is not available on the
device, or the endpoint alias is not supported on the device.)

Please visit [Matter Endpoint Doc](../Matter_endpoints.md) for more information.

**1. List supported endpoints**

```
>>> pi.matter_endpoints.list()
{1: <class 'gazoo_device.capabilities.matter_endpoints.dimmable_light.DimmableLightEndpoint'>}
```

The keys in the mapping are Matter endpoint IDs on the device.

**2. Access the endpoint by `get`**

```
>>> pi.matter_endpoints.get(1).on_off.onoff
True
```

**3. Access the endpoint by alias**

```
>>> pi.dimmable_light.on_off.onoff
True
```

**4. Access an invalid endpoint**

Assume `pi` does not have a `DoorLock` endpoint.

```
>>> pi.door_lock
rpimatter-c0b2 starting MatterEndpointsAccessorPwRpc.get_endpoint_instance_by_class(endpoint_class=<class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'>)
rpimatter-c0b2 starting MatterEndpointsAccessorPwRpc.get_endpoint_id(endpoint_class=<class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'>)
Traceback (most recent call last):
  ....
    raise errors.DeviceError(
gazoo_device.errors.DeviceError: Class <class 'gazoo_device.capabilities.matter_endpoints.door_lock.DoorLockEndpoint'> is not supported on rpimatter-c0b2.
```
