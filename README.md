# Gazoo Device Manager (also known as gazoo_device or GDM)

gazoo_device is a python package for interacting with smart devices. \
It contains Gazoo Device Manager (GDM), which defines a common device
interface. The common device interface standardizes device interactions
and allows test writers to share tests across devices despite the
underlying differences in communication types, OSes, and logic. \
GDM is available as a Python package for use in tests and comes with
its own CLI for quick device interactions. \
GDM is the open-source architecture which enables device-agnostic
interations. Device controllers used by GDM are contained in separate
Python packages and can be registered with the GDM architecture\*. \
GDM runs on the test host and communicates with the physical devices via
one or more device transports (such as SSH, ADB, HTTPS, UART). GDM does
not require any additional support from the device firmware.

The GDM architecture is used for on-device testing at Google Nest.

**This is an "early access" version of Gazoo Device Manager for early
prototyping. The full release of GDM will happen in February 2021.
Backwards compatibility of the full release with this early access
version is not guaranteed**, although it will be very close (some
modules will be moved around).

\* The separation of GDM architecture and device controller packages
isn't ready yet. If you're interested in using GDM to prototype at this
early stage, check out the repository and make a local commit with your
device controller(s) on top of it.

## Table of contents

1. [Install](#install)
    1. [Uninstall](#uninstall)
2. [Quick start](#quick-start)
3. [Virtual environment](#virtual-environment)
4. [Device controllers in GDM](#device-controllers-in-gdm)
5. [Config files](#config-files)
6. [Logs](#logs)
7. [Detecting devices](#detecting-devices)
8. [Using the CLI](#using-the-cli)
    1. [Exploring device capabilities without a physical device](#exploring-device-capabilities-without-a-physical-device)
    2. [Exploring device capabilities with a physical device](#exploring-device-capabilities-with-a-physical-device)
    3. [Basic CLI usage](#basic-cli-usage)
9. [Using the gazoo_device python package](#using-the-gazoo_device-python-package)
10. [How to use GDM with test frameworks](#how-to-use-gdm-with-test-frameworks)
    1. [GDM with Mobly](#gdm-with-mobly)
    2. [GDM with Unittest](#gdm-with-unittest)
11. [Contributor documentation](#contributor-documentation)
12. [License](#license)
13. [Disclaimer](#disclaimer)

## Install

Supported host operating systems:

* Debian;
* Ubuntu;
* MacOS.

Note: Raspberry Pi 4 on 64-bit Ubuntu 20.04 LTS is also supported as a
host (see the relevant
[device setup section](docs/DEVICE_SETUP.md#raspberry-pi-as-a-host)).

MacOS prerequisites:

1. Install Xcode Command Line Tools:

   `xcode-select --install`

2. Install Brew (MacOS package manager):

   https://brew.sh/


Installation steps:

1. Download the GDM installer archive:
   ```
   curl -OL https://github.com/google/gazoo-device/releases/latest/download/gdm-install.sh
   ```

2. Run `sh gdm-install.sh`.

You should see the following message at the end of the installation:
```
Install done (exit 0)
```

Run a few GDM CLI command to verify GDM works:
```
gdm -v
gdm devices
gdm
```

`gdm -v` should display versions of the GDM launcher and of the python
package:
```
Gazoo Device Manager launcher 0.01
Gazoo Device Manager 0.0.6
```

Typical output of `gdm devices`:
```
Device          Alias           Type         Model                Connected
--------------- --------------- -----------  ----------------     ------------

Other Devices   Alias           Type         Model                Available
--------------- --------------- -----------  ----------------     ------------

0 total Gazoo device(s) available.
```

`gdm` should display a help menu.

To update GDM to the latest version:
```
gdm update-gdm
```

To update (or downgrade) GDM to a specific version:
```
gdm update-gdm <version>  # Example: gdm update-gdm 0.0.6
```

To install GDM in a virtual environment:
```
/path_to_virtual_env/bin/pip install gazoo-device
```

### Uninstall

To uninstall GDM:
```
curl -OL https://github.com/google/gazoo-device/releases/latest/download/gdm-cleanup.sh
sh gdm-cleanup.sh
```

## Quick start

This is the quickest way to get your hands dirty with GDM. You'll need a
Raspberry Pi.

1. [Install GDM on the host](#install).
2. [Set up your Raspberry Pi as an auxiliary device in GDM and try out the CLI](docs/DEVICE_SETUP.md#raspberry-pi-as-a-supporting-device).
3. Run `gdm devices` and record the name of your Raspberry Pi (like `raspberrypi-1234`).
4. Create a Mobly testbed for your Raspberry Pi:
   ```
   sudo cp /opt/gazoo/testbeds/One-Exampledevice.yml /opt/gazoo/testbeds/One-Raspberrypi.yml
   sudo vi /opt/gazoo/testbeds/One-Raspberrypi.yml  # Or use a text editor of your choice
   # Replace "exampledevice-1234" with your device name (like "raspberrypi-1234")
   # Update the testbed name ("Testbed-One-Exampledevice-01" -> "Testbed-One-Raspberrypi-01")
   ```
5. Check out the GDM repo (which includes on-device regression tests):
   ```
   git clone https://github.com/google/gazoo-device.git
   ```
6. Run the GDM regression test suite for Raspberry Pi on your device:
   ```
   cd gazoo-device/tests/
   ./run_tests.sh -d functional_test_suites/ -f regression_test_suite.py -c /opt/gazoo/testbeds/One-Raspberrypi.yml
   ```

## Virtual environment

GDM installs a shared virtual environment at
`/usr/local/gazoo/gdm/virtual_env`.

On Linux a symlink to `/usr/local/gazoo` is created (`/gazoo`).

To use GDM in the shared virtual environment do the following:
1. `source /gazoo/gdm/virtual_env/bin/activate`
2. Then use GDM (`gdm`) as usual.

To use GDM in a different virtual environment do the following:
1. `source /path/to_other_virtual_environment/bin/activate`
2. Install GDM in this other virtual environment (if needed):
   `/usr/local/bin/gdm update-gdm`
3. Then use GDM as usual.

## Device controllers in GDM

To interact with devices, GDM creates one Python device controller
object for each physical device. The lifecycle of GDM device controllers
is as follows:
1. a new device is connected to the host and is detected by GDM through
   `gdm detect` (once), which makes the device known to GDM;
2. a device controller instance is created at the beginning of a test or
   a CLI device interaction;
3. one or more device commands are issued through the device controller
   instance;
4. the device controller instance is closed when the test is finished or
   the CLI interaction completes;
5. if the device is permanently disconnected from the host, it is
   removed from the list of devices known to GDM through
   ```
   gdm delete device-1234
   ```
   (also once).

Note that the term "device" is ambiguous in the context of GDM: it can
refer to either the device controller or the physical device. Device
controllers can also be referred to as device classes.

## Config files

GDM device configs are found in `/gazoo/gdm/conf` on Linux and
`$HOME/gazoo/gdm/conf` on MacOS.

You're not expected to modify them directly. Instead, use `set-prop` and
`get-prop` commands:
* `gdm set-prop device-1234 property-name property-value` to set an
  optional device property;
* `gdm get-prop device-1234 property-name` to retrieve the property
  value;
* `gdm set-prop property-name property-value` to set a GDM property;
* `gdm get-prop property-name` to retrieve the value of a GDM property.

## Logs

By default all GDM logs go to `/gazoo/gdm/log/`. On Macs, logs are
collected in `~/gdm/log/`. Log verbosity, output directory, and standard
output behavior can be configured via arguments to `Manager.__init__`
(see [gazoo_device/manager.py](gazoo_device/manager.py)).

GDM creates three types of log files.

### The `gdm.txt` log

All GDM logs go here. Device logs are **not** captured in this file.
This log file persists across GDM invocations. It provides the best
history, but it can be difficult to pinpoint the logs for a particular
device interaction.

### Device log files, such as `linuxexample-1eb2-20201113-123538.txt`

These capture all communications between GDM and the device.
Each log line is prefixed with `GDM-<letter_or_digit>`, such as `GDM-M`,
`GDM-0`, or `GDM-1`.

`GDM-M` are logs written by GDM. These include the commands that GDM
wrote, the regular expressions GDM expects to find after writing a
command and the maximum time window for the response, and the result of
the expect (which regular expression matched, if any).

`GDM-0`, `GDM-1`, and other `GDM-<digit>` logs come from device
transports. The digit corresponds to the index of the transport (as
defined by `get_transport_list()` methods of communication types in
[gazoo_device/switchboard/communication_types.py](gazoo_device/switchboard/communication_types.py)). \
For some communication types, such as SSH and ADB, logs and command
responses come from different transports. In that case device responses
come from `GDM-0` and device logs come from `GDM-1`. \
For other communication types, there may only be a single transport, in
which case both device responses and logs come from `GDM-0`.

The names of device log files are logged during every CLI interaction.
For example:
```
linuxexample-1eb2 logging to file /Users/artorl/gdm/log/linuxexample-1eb2-20201113-123548.txt
```

### Device log event files, such as `linuxexample-1eb2-20201113-123548-events.txt`

These contain device log events. The log events to be captured are
defined by log event filters in
[gazoo_device/filters/](gazoo_device/filters/).

A log filtering process receives all device logs in real time
and captures lines which match any of the device log filters
into the device log event file.

The name of the log event file is constructed as
`<name_of_log_file>-events.txt`. For example,
`linuxexample-1eb2-20201113-123548-events.txt` is the log event file for
the `linuxexample-1eb2-20201113-123548.txt` device log file.

## Detecting devices

To detect all devices attached to your host, run `gdm detect` on the
host. This is a one-time step that is required when GDM is installed on
the host or when a new device is connected to the host. Devices
typically require a special setup before being usable with GDM. This can
include a special cable connection configuration, renaming serial
cables, updating device firmware to a specific version, setting up the
device on a static IP address, or setting up passwordless SSH access to
the device. Refer to [docs/DEVICE_SETUP.md](docs/DEVICE_SETUP.md) for
instructions.

Device detection populates device configs:
* persistent properties are stored in  `/gazoo/gdm/conf/devices.json`;
* optional (settable) properties are stored in
  `/gazoo/gdm/conf/device_options.json`.

To view all devices currently known to GDM, run `gdm devices`.

Sample detection output (`cambrionix-kljo` was detected):
```
$ gdm detect

##### Step 1/3: Detecting potential new communication addresses. #####

    detecting potential AdbComms communication addresses
    detecting potential DockerComms communication addresses
Unable to detect DockerComms communication addresses. Err: FileNotFoundError(2, 'No such file or directory')
    detecting potential JlinkSerialComms communication addresses
    detecting potential PtyProcessComms communication addresses
    detecting potential SerialComms communication addresses
Warning: no read/write permission for these serial address(es): ['/dev/bus/usb/001/001', '/dev/bus/usb/001/002', '/dev/bus/usb/002/001']
    detecting potential SshComms communication addresses
    detecting potential YepkitComms communication addresses
Found 1 possible serialcomms connections:
    /dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DM01KLJO-if00-port0

##### Step 2/3 Identify Device Type of Connections. #####

Identifying serialcomms devices..
    /dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DM01KLJO-if00-port0 is a cambrionix.
    serialcomms device_type detection complete.

##### Step 3/3: Extract Persistent Info from Detected Devices. #####

Getting info from communication port /dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_DM01KLJO-if00-port0 for cambrionix
    cambrionix_detect starting AuxiliaryDevice.check_device_ready
    cambrionix_detect health check 1/2 succeeded: Device is connected.
    cambrionix_detect health check 2/2 succeeded: Clear flags.
    cambrionix_detect AuxiliaryDevice.check_device_ready successful. It took 0s.
    cambrionix_detect starting Cambrionix.get_detection_info
    cambrionix_detect Cambrionix.get_detection_info successful. It took 1s.

##### Detection Summary #####

    1 new devices detected:
        cambrionix-kljo
Device          Alias           Type         Model                Connected
--------------- --------------- -----------  ----------------     ------------

Other Devices   Alias           Type         Model                Available
--------------- --------------- -----------  ----------------     ------------
cambrionix-kljo <undefined>     cambrionix   PP15S                available

0 total device(s) available.
```

Device names are created as `devicetype-1234`, where the device type is
provided by the device controller, and the digits are the last 4 digits
of the device's serial number.

Detection only detects *new* devices. It does not re-detect already
known devices. \
To delete a known device: `gdm delete device-1234`. \
To redetect a device: `gdm redetect device-1234`.

## Using the CLI

### Exploring device capabilities without a physical device

GDM comes equipped with auto-generated documentation. To access it, you
do not need a device.

To see all commands available through the Manager class, run: `gdm`. You
can also explore Manager functionality via the dynamic Fire CLI. For
example:
```
gdm -- --help
gdm create_device -- --help
```

To start exploring device documentation, run `gdm man`. It will list
all supported devices and provide commands to run if you're interested
in exploring capabilities of a specific device.

To see what's supported by a device type: `gdm man device-type`.
For example: `gdm man raspberrypi`.

To explore a device method, property, or capability, issue
`gdm man device-type attribute-name`. For example:
```
gdm man raspberrypi firmware_version
gdm man raspberrypi reboot
gdm man raspberrypi file_transfer
```

Note that there is a limit on the amount of nesting suppored by static
documentation. `gdm man` takes a maximum of two arguments. For example,
`gdm man raspberrypi file_transfer send_file_to_device` will not work.

### Exploring device capabilities with a physical device

If you have a physical device, you can use the dynamic Fire CLI
to get help about any attribute of the device. There are no limitations
to this documentation, and it's more detailed and more accurate, but the
drawback is that it requires a physical device. For example, assuming a
`raspberrypi-kljo` is attached:
```
gdm issue raspberrypi-kljo -- --help
gdm issue raspberrypi-kljo - reboot -- --help
```

### Basic CLI usage

Let's assume you have a `raspberrypi-kljo` connected.

Here are a few commonly used CLI commands:

* list all known devices: `gdm devices`;
* detect new devices: `gdm detect` or `gdm detect --static_ips=10.20.30.40,50.60.70.80`
  * Detection will not remove devices which are already known to GDM.
* set a device property (such as an alias):
  `gdm set-prop raspberrypi-kljo alias rpi`;
* check GDM version: `gdm -v`;
* run health checks on a device: `gdm health-check raspberrypi-kljo`
  * `gdm health-check rpi` will also work if you've set the alias above;
* run health checks, then issue a device command or retrieve a property:
  `gdm issue raspberrypi-kljo - reboot`;
* issue a device command or retrieve a property *without* running health
  checks: `gdm exec raspberrypi-kljo - reboot`;
* use a device capability:
  ```
  gdm issue raspberrypi-kljo - file_transfer - recv_file_from_device --src="/tmp/foo" --dest="/tmp/bar"
  ```
  (or use `exec` to skip health checks).

Sometimes passing the arguments to the Fire CLI gets a bit tricky.
Refer to the [Python Fire documentation](https://google.github.io/python-fire/guide/)
and definitely review the [argument parsing section](https://google.github.io/python-fire/guide/#argument-parsing).

The most commonly used device method is `shell`. It runs a shell
command on the device. It's required for primary devices, but is
optional for auxiliary devices. The only auxiliary device included with
GDM that implements `shell()` is Raspberry Pi. If you have a Raspberry
Pi connected, you can try it out:
`gdm issue raspberrypi-1234 - shell "echo 'foo'"`.

## Using the gazoo_device python package

Launch Python from a virtual environment with gazoo_device installed. \
You can use the GDM virtual environment:
`/gazoo/gdm/virtual_env/bin/python`.

```
from gazoo_device import Manager
mgr = Manager()
rpi = mgr.create_device('raspberrypi-962c')
rpi.reboot()
```

Note that the device you're creating should be shown as "available" in
the output of `gdm devices`.

## How to use GDM with test frameworks

### GDM with [Mobly](https://github.com/google/mobly)

Example testbed file (`/opt/gazoo/testbeds/One-Raspberrypi.yml`):

```
TestBeds:
  - Name: Testbed-One-Raspberrypi-01
    Controllers:
      GazooDevice:
        - 'raspberrypi-kljo'
```

Example device test using GDM with Mobly:
[example_mobly_test.py](tests/functional_test_examples/example_mobly_test.py).

For working examples of gazoo_device + mobly, see GDM's functional
tests in [tests/functional_tests/](tests/functional_tests/).

### GDM with [Unittest](https://docs.python.org/3/library/unittest.html#module-unittest)

Example device test using GDM with Unittest:
[example_unittest_test.py](tests/functional_test_examples/example_unittest_test.py).

## Contributor documentation

If you're interested in adding support for your device(s) to GDM, refer
to [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Licensed under the
[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) License.

## Disclaimer

This is not an official Google product.
