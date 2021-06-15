# Gazoo Device Manager (also known as gazoo_device or GDM)

gazoo_device is a python package for interacting with smart devices. \
It contains Gazoo Device Manager (GDM), which defines a common device interface.
The common device interface standardizes device interactions and allows test
writers to share tests across devices despite the underlying differences in
communication types, OSes, and logic. \
GDM is available as a Python package for use in tests and comes with its own CLI
for quick device interactions. \
GDM is the open-source architecture which enables device-agnostic interations.
Device controllers used by GDM are contained in separate Python packages and can
be registered with the GDM architecture. \
GDM runs on the test host and communicates with the physical devices via one or
more device transports (such as SSH, ADB, HTTPS, UART). GDM does not require any
additional support from the device firmware.

GDM is used for on-device testing at Google Nest.

## Table of contents

1.  [Install](#install)
    1.  [Uninstall](#uninstall)
2.  [Quick start](#quick-start)
3.  [Device controllers in GDM](#device-controllers-in-gdm)
4.  [Config files](#config-files)
5.  [Logs](#logs)
6.  [Detecting devices](#detecting-devices)
7.  [Using the CLI](#using-the-cli)
    1.  [Exploring device capabilities without a physical device](#exploring-device-capabilities-without-a-physical-device)
    2.  [Exploring device capabilities with a physical device](#exploring-device-capabilities-with-a-physical-device)
    3.  [Basic CLI usage](#basic-cli-usage)
8.  [Using the gazoo_device python package](#using-the-gazoo_device-python-package)
9.  [How to use GDM with test frameworks](#how-to-use-gdm-with-test-frameworks)
    1.  [GDM with Mobly](#gdm-with-mobly)
    2.  [GDM with Unittest](#gdm-with-unittest)
10. [Contributor documentation](#contributor-documentation)
11. [License](#license)
12. [Disclaimer](#disclaimer)

## Install

Supported host operating systems:

*   Debian;
*   Ubuntu;
*   MacOS.

Windows is not supported.

Note: Raspberry Pi 4 on 64-bit Ubuntu 20.04 LTS is also supported as a host (see
the relevant [device setup section](docs/Raspberry_Pi_as_host.md)).

MacOS prerequisites:

1. Install Xcode Command Line Tools:

   ```shell
   xcode-select --install
   ```

2. Install Brew (MacOS package manager):

   https://brew.sh/


Installation steps:

1.  Download the GDM installer archive:

    ```shell
    curl -OL https://github.com/google/gazoo-device/releases/latest/download/gdm-install.sh
    ```

2.  Run the installer:

    ```shell
    bash gdm-install.sh
    ```

    You should see the following message at the end of the installation:

    ```
    Install done (exit 0)
    ```

3.  Add `gdm` to your `$PATH`:

    Add the following line to `~/.bash_profile` or `~/.bashrc`:

    ```shell
    export PATH="${PATH}:${HOME}/gazoo/bin"
    ```

GDM installation creates a virtual environment for the CLI at
`~/gazoo/gdm/virtual_env`. \
`gdm` CLI commands run in this virtual environment.

Run a few GDM CLI commands to verify GDM works:

```shell
gdm -v
gdm devices
gdm
```

`gdm -v` displays versions of the GDM launcher and of the python package:

```
Gazoo Device Manager launcher 1.0
Gazoo Device Manager 1.0.0
```

Typical output of `gdm devices`:

```
Device          Alias           Type         Model                Connected
--------------- --------------- -----------  ----------------     ------------

Other Devices   Alias           Type         Model                Available
--------------- --------------- -----------  ----------------     ------------

0 total Gazoo device(s) available.
```

`gdm` displays a help menu.

To update GDM to the latest version:

```
gdm update-gdm
```

To update (or downgrade) GDM to a specific version:

```
gdm update-gdm <version>  # Example: gdm update-gdm 1.0.0
```

To install GDM in a virtual environment:

```
/path_to_virtual_env/bin/pip install gazoo-device
```

Important: one of GDM's dependencies, [Pigweed](https://pigweed.dev/), is not
available on PyPI yet. You will have to manually download and install Pigweed
wheels in your virtual environment (the installer does this automatically for
the GDM CLI virtual environment). You can use the following snippet to download
Pigweed wheels:

```shell
PIGWEED_WHEELS="button_service-0.0.1-py3-none-any.whl
device_service-0.0.1-py3-none-any.whl
lighting_app-0.0.1-py3-none-any.whl
lighting_service-0.0.1-py3-none-any.whl
pw_cli-0.0.1-py3-none-any.whl
pw_protobuf-0.0.1-py3-none-any.whl
pw_protobuf_compiler-0.0.1-py3-none-any.whl
pw_protobuf_protos-0.0.1-py3-none-any.whl
pw_rpc-0.0.1-py3-none-any.whl
pw_status-0.0.1-py3-none-any.whl
pw_hdlc-0.0.1-py3-none-any.whl"

for wheel in $PIGWEED_WHEELS; do
  url="https://github.com/google/gazoo-device/releases/latest/download/$wheel"
  local_file="/tmp/$wheel"
  echo "Downloading and installing $url"
  curl -L "$url" -o "$local_file"
  pip3 install "$local_file"  # You might need to use a different pip path here.
  rm "$local_file"
done
```

### Uninstall

To uninstall GDM:

```
curl -OL https://github.com/google/gazoo-device/releases/latest/download/gdm-cleanup.sh
bash gdm-cleanup.sh
```

## Quick start

This is the quickest way to get your hands dirty with GDM. You will need a
Raspberry Pi.

1.  [Install GDM on the host](#install).
2.  [Set up your Raspberry Pi as an auxiliary device in GDM and try out the CLI](docs/device_setup/Raspberry_Pi_as_supporting_device.md).
3.  [Run the example on-device test with a test framework of your choice](https://github.com/google/gazoo-device/blob/master/examples/device_tests/README.md).

## Device controllers in GDM

To interact with devices, GDM creates one Python device controller object for
each physical device. The lifecycle of GDM device controllers is as follows:

1.  a new device is connected to the host and is detected by GDM (one-time setup
    step), which makes the device known to GDM:

    ```
    gdm detect
    ```

2.  a device controller instance is created at the beginning of a test or a CLI
    device interaction;

3.  one or more device commands are issued through the device controller
    instance;

4.  the device controller instance is closed when the test is finished or the
    CLI interaction completes;

5.  if the device is permanently disconnected from the host, it is removed from
    the list of devices known to GDM (also a one-time step) through

    ```
    gdm delete device-1234
    ```

Note that the term "device" is ambiguous in the context of GDM: it can refer to
either the device controller or the physical device. Device controllers can also
be referred to as device classes.

## Config files

GDM device configs are found in `~/gazoo/gdm/conf`.

You should not modify them directly. Instead, use `set-prop` and `get-prop`
commands:

* To set an optional device property:

  ```
  gdm set-prop device-1234 property-name property-value
  ```

* To retrieve a device property:

  ```
  gdm get-prop device-1234 property-name
  ```

* To set a Manager property:

  ```
  gdm set-prop manager property-name property-value
  ```

* To retrieve a Manager property:

  ```
  gdm get-prop manager property-name
  ```

## Logs

By default all GDM logs go to `~/gazoo/gdm/log/`. Log verbosity, output
directory, and standard output behavior can be configured via arguments to
`Manager.__init__` (see [gazoo_device/manager.py](gazoo_device/manager.py)).

GDM creates three types of log files.

### The `gdm.txt` log

All GDM logs go here. Device logs are **not** captured in this file. This log
file persists across GDM invocations. It provides the best history, but it can
be difficult to pinpoint the logs for a particular device interaction.

### Device log files, such as `linuxexample-1eb2-20201113-123538.txt`

These capture all communications between GDM and the device. Each log line is
prefixed with `GDM-<letter_or_digit>`, such as `GDM-M`, `GDM-0`, or `GDM-1`.

`GDM-M` are logs written by GDM. These include the commands that GDM wrote, the
regular expressions GDM expects to find after writing a command and the maximum
time window for the response, and the result of the expect (which regular
expression matched, if any).

`GDM-0`, `GDM-1`, and other `GDM-<digit>` logs come from device transports. The
digit corresponds to the index of the transport (as defined by
`get_transport_list()` methods of communication types in
[gazoo_device/switchboard/communication_types.py](gazoo_device/switchboard/communication_types.py)).
\
For some communication types, such as SSH and ADB, logs and command responses
come from different transports. In that case device responses come from `GDM-0`
and device logs come from `GDM-1`. \
For other communication types, there may only be a single transport, in which
case both device responses and logs come from `GDM-0`.

The names of device log files are logged during every CLI interaction. For
example: `linuxexample-1eb2 logging to file
/Users/artorl/gdm/log/linuxexample-1eb2-20201113-123548.txt`

### Device log event files, such as `linuxexample-1eb2-20201113-123548-events.txt`

These contain device log events. The log events to be captured are defined by
log event filters in [gazoo_device/filters/](gazoo_device/filters/).

A log filtering process receives all device logs in real time and captures lines
which match any of the device log filters into the device log event file.

The name of the log event file is constructed as
`<name_of_log_file>-events.txt`. For example,
`linuxexample-1eb2-20201113-123548-events.txt` is the log event file for the
`linuxexample-1eb2-20201113-123548.txt` device log file.

## Detecting devices

To detect all devices attached to your host, run `gdm detect` on the host. This
is a one-time step that is required when GDM is installed on the host or when a
new device is connected to the host. Devices typically require a special setup
before being usable with GDM. This can include a special cable connection
configuration, renaming serial cables, updating device firmware to a specific
version, setting up the device on a static IP address, or setting up
passwordless SSH access to the device. Refer to
[docs/device_setup/](docs/device_setup/) for instructions.

Device detection populates device configs:

*   persistent properties are stored in `~/gazoo/gdm/conf/devices.json`;
*   optional (settable) properties are stored in
    `~/gazoo/gdm/conf/device_options.json`.

To view all devices currently known to GDM, run `gdm devices`.

Sample detection output (`cambrionix-kljo` was detected):

```
$ gdm detect

##### Step 1/3: Detecting potential new communication addresses. #####

        detecting potential AdbComms communication addresses
        detecting potential DockerComms communication addresses
'docker' is not installed. Cannot get Docker devices.
        detecting potential JlinkSerialComms communication addresses
        detecting potential PtyProcessComms communication addresses
        detecting potential SshComms communication addresses
        detecting potential SerialComms communication addresses
        detecting potential YepkitComms communication addresses
'ykushcmd' is not installed. Cannot get Yepkit serials.
        detecting potential PigweedSerialComms communication addresses
Found 1 possible serialcomms connections:
        /dev/tty.usbserial-DM01KLJO

##### Step 2/3 Identify Device Type of Connections. #####

Identifying serialcomms devices..
        /dev/tty.usbserial-DM01KLJO is a cambrionix.
        serialcomms device_type detection complete.

##### Step 3/3: Extract Persistent Info from Detected Devices. #####

Getting info from communication port /dev/tty.usbserial-DM01KLJO for cambrionix
        cambrionix_detect checking device readiness: attempt 1 of 1
        cambrionix_detect starting AuxiliaryDevice.check_device_ready
        cambrionix_detect health check 1/2 succeeded: Check device connected.
        cambrionix_detect health check 2/2 succeeded: Check clear flags.
        cambrionix_detect AuxiliaryDevice.check_device_ready successful. It took 0s.
        cambrionix_detect starting Cambrionix.get_detection_info
        cambrionix_detect Cambrionix.get_detection_info successful. It took 0s.

##### Detection Summary #####

        1 new devices detected:
                cambrionix-kljo
Device                     Alias           Type                 Model                Connected
-------------------------- --------------- -------------------- -------------------- ----------

Other Devices              Alias           Type                 Model                Available
-------------------------- --------------- -------------------- -------------------- ----------
cambrionix-kljo            <undefined>     cambrionix           PP15S                available

0 total Gazoo device(s) available.
```

Device names are created as `devicetype-1234`, where the device type is provided
by the device controller, and the digits are the last 4 digits of the device's
serial number.

Detection only detects *new* devices. It does not re-detect already known
devices.

* To delete a known device:

  ```
  gdm delete device-1234
  ```

* To redetect a device:

  ```
  gdm redetect device-1234
  ```

## Using the CLI

### Exploring device capabilities without a physical device

GDM comes equipped with auto-generated documentation. To access it, you do not
need a device.

To see all commands available through the Manager class, run:

```
gdm
```

To start exploring device documentation, run:

```
gdm man
```

It will list all supported devices and provide commands to run if you are
interested in exploring capabilities of a specific device.

To see what is supported by a device type:

```
gdm man device_type
```

For example:

```
gdm man raspberrypi
```

To explore a device method, property, or capability, issue:

```
gdm man device_type attribute_name
```

For example:

```
gdm man raspberrypi firmware_version
gdm man raspberrypi reboot
gdm man raspberrypi file_transfer
```

To explore a capability method or property, issue:

```
gdm man device_type capability_name method_or_property_name
```

For example:

```
gdm man cambrionix switch_power off
gdm man raspberrypi file_transfer send_file_to_device
```

You can also explore GDM functionality via the dynamic Fire CLI. For example:

```
gdm -- --help
gdm create_device -- --help
```

### Exploring device capabilities with a physical device

If you have a physical device, you can use the dynamic Fire CLI to get help
about any attribute of the device. There are no limitations to this
documentation, and it is more detailed and more accurate, but the drawback is
that it requires a physical device. For example, assuming a `raspberrypi-kljo`
is attached:

```
gdm issue raspberrypi-kljo -- --help
gdm issue raspberrypi-kljo - reboot -- --help
```

### Basic CLI usage

Let us assume you have a `raspberrypi-kljo` connected.

Here are a few commonly used CLI commands:

*   list all known devices:

    ```
    gdm devices
    ```

*   detect new devices:

    ```
    gdm detect
    ```

    or

    ```
    gdm detect --static_ips=10.20.30.40,50.60.70.80
    ```

    Note: detection does not remove devices which are already known to GDM.

*   set a device property (such as an alias):

    ```
    gdm set-prop raspberrypi-kljo alias rpi
    ```

*   check GDM version:

    ```
    gdm -v
    ```

*   run health checks on a device:

    ```
    gdm health-check raspberrypi-kljo
    ```

    if you set the alias above, the following will also work:

    ```
    gdm health-check rpi
    ```

*   run health checks, then issue a device command or retrieve a property:

    ```
    gdm issue raspberrypi-kljo - reboot
    ```

*   issue a device command or retrieve a property *without* running health
    checks:

    ```
    gdm exec raspberrypi-kljo - reboot
    ```

*   use a device capability:

    ```
    gdm issue raspberrypi-kljo - file_transfer - recv_file_from_device --src="/tmp/foo" --dest="/tmp/bar"
    ```

    (or use `gdm exec` to skip health checks).

Sometimes passing the arguments to the Fire CLI gets a bit tricky. Refer to the
[Python Fire documentation](https://google.github.io/python-fire/guide/) and
definitely review the
[argument parsing section](https://google.github.io/python-fire/guide/#argument-parsing).

The most commonly used device method is `shell`. It runs a shell command on the
device. It is required for primary devices, but is optional for auxiliary
devices. The only auxiliary device included with GDM that implements `shell()`
is Raspberry Pi. If you have a Raspberry Pi connected, you can try it out:

```
gdm issue raspberrypi-1234 - shell "echo 'foo'"
```

## Using the gazoo_device python package

Launch Python from a virtual environment with gazoo_device installed. \
You can use the GDM CLI virtual environment:
`~/gazoo/gdm/virtual_env/bin/python`.

```
from gazoo_device import Manager
manager = Manager()
rpi = manager.create_device('raspberrypi-962c')
rpi.reboot()
```

Note that the device you are creating should be shown as "available" in the
output of `gdm devices`.

## How to use GDM with test frameworks

GDM is framework-agnostic and can be used with any Python test framework. \
See
[examples/device_tests/README.md](https://github.com/google/gazoo-device/blob/master/examples/device_tests/README.md)
for GDM + unittest and GDM + Mobly examples.

## Contributor documentation

If you are interested in adding support for your device(s) to GDM, refer to
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

Licensed under the
[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) License.

## Disclaimer

This is not an official Google product.
