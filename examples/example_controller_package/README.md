# Codelab: User-defined controller packages for gazoo_device

Gazoo Device Manager allows users to register arbitrary controller packages. \
In short, controller packages can define new device controllers and all
supporting functionality (capabilities, communication types, detection queries,
etc.). See [package_registrar.register()]
(https://github.com/google/gazoo-device/blob/master/gazoo_device/package_registrar.py)
documentation for a full list of allowed extensions.

For the purposes of this codelab, we've created an example controller package
which defines a new device type, `linuxexample`. \
This codelab will walk you through the process of building the package,
registering it with GDM, and using it from the CLI and within a Python
environment.

## Table of contents

1. [Prerequisite: install GDM](#prerequisite-install-gdm)
2. [Connect a device to your host](#connect-a-device-to-your-host)
3. [Check out the source code](#check-out-the-source-code)
4. [Configure the controller](#configure-the-controller)
   1. [[Optional] Change SSH username](#optional-change-ssh-username)
   2. [[Optional] Configure passwordless SSH access](#optional-configure-passwordless-ssh-access)
5. [Build and register the controller package](#build-and-register-the-controller-package)
6. [Try using the example controller](#try-using-the-example-controller)
   1. [View controller documentation](#view-controller-documentation)
   2. [CLI controller usage](#cli-controller-usage)
   3. [Examine device logs and events](#examine-device-logs-and-events)
   4. [Python API controller usage](#python-api-controller-usage)
7. [Conclusion & cleanup](#conclusion-cleanup)

## Prerequisite: install GDM

If you haven't installed GDM yet, follow
[the installation steps](https://github.com/google/gazoo-device#install).

## Connect a device to your host

We'll try using the example device controller with a real device. \
The example controller should work with any Linux device which accepts SSH
connections. If you don't have a device, you can still follow along with the
instructions.

Note: GDM controllers require that each physical device must be matched by a
single controller type. This doesn't hold true for this example controller: it
will interfere with detection of other Linux devices communicating over SSH (for
example, Raspberry Pi) by also matching them. We've chosen a generic controller
to avoid dependency on having specific hardware for this codelab. Make sure to
follow the cleanup steps at the end.

The example controller makes [a few assumptions]
(https://github.com/google/gazoo-device/blob/master/examples/example_controller_package/example_linux_device.py)
about SSH accessibility of the target device. Make sure that your device
responds to ping:

```
ping <device_ip>
```

and can be accessed via SSH from the host:

```
ssh <username>@<device_ip>
```

## Check out the source code

Check out the gazoo-device repository:

```shell
git clone https://github.com/google/gazoo-device.git
cd gazoo-device
```

## Configure the controller

You may need to tweak a few SSH communication settings used by GDM for your
device.

### [Optional] Change SSH username

If you use a username that's not `root` when accessing the device via SSH, you
will need to modify
`_SSH_USERNAME` in [example_linux_device.py]
(https://github.com/google/gazoo-device/blob/master/examples/example_controller_package/example_linux_device.py)
:

```python
# TODO(user): You may need to change the value of _SSH_USERNAME for your device.
_SSH_USERNAME = "root"
```

### [Optional] Configure passwordless SSH access

GDM does not use password authentication. If you use password authentication
when accessing the device via SSH, you'll need to set up passwordless SSH access
to the device. There are two ways to do so: using your host's default SSH key or
using a separate key made specifically for the device controller. We'll go with
the easier option: using the default host SSH key, `~/.ssh/id_rsa.pub`. (If
you're interested in setting up a controller-specific key, follow the
instructions marked with `# TODO(user)` in [\_\_init.py\_\_]
(https://github.com/google/gazoo-device/blob/master/examples/example_controller_package/__init__.py)
and [example_linux_device.py]
(https://github.com/google/gazoo-device/blob/master/examples/example_controller_package/example_linux_device.py)
instead.)

Run the following:

```
ssh-copy-id <username>@<host>
```

Your output will look like this:

```
$ ssh-copy-id ubuntu@192.168.1.168
/usr/bin/ssh-copy-id: INFO: attempting to log in with the new key(s), to filter out any that are already installed
/usr/bin/ssh-copy-id: INFO: 2 key(s) remain to be installed -- if you are prompted now it is to install the new keys
ubuntu@192.168.1.168's password:

Number of key(s) added:        2

Now try logging into the machine, with:   "ssh 'ubuntu@192.168.1.168'"
and check to make sure that only the key(s) you wanted were added.
```

## Build and register the controller package

Go to the example controller package directory and build the package:

```shell
cd examples/example_controller_package
python3 setup.py clean
python3 setup.py -v build sdist
```

This will build a distributable version of the package in `dist/`.

```shell
$ ls dist/
example_controller_package-0.0.1.tar.gz
```

Install the example controller package in GDM CLI virtual environment
(`~/gazoo/gdm/virtual_env/`):

```shell
~/gazoo/gdm/virtual_env/bin/pip install dist/example_controller_package-0.0.1.tar.gz
```

Register the example controller package with GDM CLI:

```shell
gdm register example_controller_package
```

GDM will confirm package registration:

```shell
$ gdm register example_controller_package
Registered package 'example_controller_package' with GDM CLI.
```

Note: the `gdm` executable is available as `~/gazoo/bin/gdm` by default. You
will need to add `$HOME/gazoo/bin/gdm` to your system `$PATH` if you haven't
already done so during installation.

## Try using the example controller

### View controller documentation

You can view controller documentation without having a device attached:

```shell
gdm man linuxexample
gdm man linuxexample shell
gdm man linuxexample reboot
```

### CLI controller usage

Let's try running some CLI commands using the example controller.

Detect your device:

```shell
gdm detect --static_ips=<IP_of_device>
```

Your output will look like this:

```shell
$ gdm detect --static-ips=192.168.1.168

##### Step 1/3: Detecting potential new communication addresses. #####

	detecting potential AdbComms communication addresses
WARNING: adb path adb stored in /Users/artorl/gazoo/gdm/conf/gdm.json does not exist.
	detecting potential DockerComms communication addresses
Unable to detect DockerComms communication addresses. Err: FileNotFoundError(2, "No such file or directory: 'docker'")
	detecting potential JlinkSerialComms communication addresses
	detecting potential PtyProcessComms communication addresses
	detecting potential SshComms communication addresses
	detecting potential SerialComms communication addresses
	detecting potential YepkitComms communication addresses
	detecting potential PigweedSerialComms communication addresses
Found 1 possible sshcomms connections:
	192.168.1.168

##### Step 2/3 Identify Device Type of Connections. #####

Identifying sshcomms devices..
	192.168.1.168 is a linuxexample.
	sshcomms device_type detection complete.

##### Step 3/3: Extract Persistent Info from Detected Devices. #####

Getting info from communication port 192.168.1.168 for linuxexample
	linuxexample_detect starting GazooDeviceBase.check_device_ready
	linuxexample_detect waiting up to 3s for device to be connected.
	linuxexample_detect health check 1/3 succeeded: Check device connected.
	linuxexample_detect logging to file /Users/artorl/gazoo/gdm/log/192.168.1.168_detect.txt
	linuxexample_detect health check 2/3 succeeded: Check create switchboard.
	linuxexample_detect health check 3/3 succeeded: Check device responsiveness.
	linuxexample_detect GazooDeviceBase.check_device_ready successful. It took 2s.
	linuxexample_detect starting ExampleLinuxDevice.get_detection_info
	linuxexample_detect starting SshDevice.get_detection_info
	linuxexample_detect closing switchboard processes
	linuxexample_detect SshDevice.get_detection_info successful. It took 0s.
	linuxexample_detect ExampleLinuxDevice.get_detection_info successful. It took 0s.

##### Detection Summary #####

	1 new devices detected:
		linuxexample-1234
Device                     Alias           Type                 Model                Connected
-------------------------- --------------- -------------------- -------------------- ----------
linuxexample-1234          <undefined>     linuxexample         Production           connected

Other Devices              Alias           Type                 Model                Available
-------------------------- --------------- -------------------- -------------------- ----------

1 total Gazoo device(s) available.
```

The device should show as "connected" in output of `gdm devices`:

```shell
$ gdm devices
Device                     Alias           Type                 Model                Connected
-------------------------- --------------- -------------------- -------------------- ----------
linuxexample-1234          <undefined>     linuxexample         Production           connected

Other Devices              Alias           Type                 Model                Available
-------------------------- --------------- -------------------- -------------------- ----------

1 total Gazoo device(s) available.
```

Try running some GDM CLI commands on the device:

```shell
# "exec" and "issue" are keywords which signal executing a device command or
# retrieving a device property. The difference is that "issue" runs health
# checks prior to command execution whereas "exec" does not.
# "-- --help" displays dynamically-generated CLI help.
# Note that this requires a device to be connected (unlike "gdm man").
gdm exec linuxexample-1234 -- --help
gdm exec linuxexample-1234 - shell -- --help
gdm issue linuxexample-1234 - shell "echo 'foo'"
```

```shell
# "get-prop" retrieves device properties.
# There are 3 property types: persistent, dynamic, and optional/settable.
# Firmware version is a dynamic property. Dynamic properties may change and need
# to be retrieved on an ad-hoc basis, which requires communicating with the
# device every time.
gdm get-prop linuxexample-1234 firmware_version
# Hardware architecture is a persistent property. Persistent properties do not
# change. Their values are retrieved during device detection and stored in
# ~/gazoo/gdm/conf/devices.json. Retrieval of persistent properties later does
# not involve communication with the device.
gdm get-prop linuxexample-1234 hardware_architecture
# my_optional_prop is an optional property. Optional properties can be set by
# users. Retrieval of optional properties does not require device communication.
gdm get-prop linuxexample-1234 my_optional_prop
# "set-prop" can set optional properties.
gdm set-prop linuxexample-1234 my_optional_prop some_new_value
gdm get-prop linuxexample-1234 my_optional_prop
# New optional properties properties can be defined on the fly.
# new_optional_prop doesn't exist yet -- retrieval should fail.
gdm get-prop linuxexample-1234 new_optional_prop
gdm set-prop linuxexample-1234 new_optional_prop i_did_not_exist_before
gdm get-prop linuxexample-1234 new_optional_prop

# "get-prop" without any arguments retrieves all device properties.
gdm get-prop linuxexample-1234
```

Your output should look like this (`gdm exec linuxexample-1234 -- --help` output
omitted for brevity):

```shell
$ gdm exec linuxexample-1234 - shell -- --help
Creating linuxexample-1234
NAME
    gdm exec linuxexample-1234 shell - Sends command and returns response and optionally return code.

SYNOPSIS
    gdm exec linuxexample-1234 - shell COMMAND <flags>

DESCRIPTION
    Can try multiple times as connection can sometimes fail.
    See shell_capability init args for setting the number of retry
    attempts.

POSITIONAL ARGUMENTS
    COMMAND
        Command to send to the device.

FLAGS
    --command_name=COMMAND_NAME
        Default: 'shell'
        Identifier for command.
    --timeout=TIMEOUT
        Type: Optional[]
        Default: None
        Time in seconds to wait for device to respond.
    --port=PORT
        Default: 0
        Which port to send on, 0 or 1.
    --searchwindowsize=SEARCHWINDOWSIZE
        Default: 2000
        Number of the last bytes to look at
    --include_return_code=INCLUDE_RETURN_CODE
        Default: False
        flag indicating return code should be returned.

NOTES
    You can also use flags syntax for POSITIONAL ARGUMENTS
```

```shell
$ gdm issue linuxexample-1234 - shell "echo 'foo'"
Creating linuxexample-1234
linuxexample-1234 starting GazooDeviceBase.check_device_ready
linuxexample-1234 waiting up to 3s for device to be connected.
linuxexample-1234 health check 1/3 succeeded: Check device connected.
linuxexample-1234 logging to file /Users/artorl/gazoo/gdm/log/linuxexample-1234-20210503-174754.txt
linuxexample-1234 health check 2/3 succeeded: Check create switchboard.
linuxexample-1234 health check 3/3 succeeded: Check device responsiveness.
linuxexample-1234 GazooDeviceBase.check_device_ready successful. It took 2s.
foo
linuxexample-1234 closing switchboard processes
```

```
$ gdm get-prop linuxexample-1234 firmware_version
Creating linuxexample-1234
linuxexample-1234 starting GazooDeviceBase.check_device_ready
linuxexample-1234 waiting up to 3s for device to be connected.
linuxexample-1234 health check 1/3 succeeded: Check device connected.
linuxexample-1234 logging to file /Users/artorl/gazoo/gdm/log/linuxexample-1234-20210503-220937.txt
linuxexample-1234 health check 2/3 succeeded: Check create switchboard.
linuxexample-1234 health check 3/3 succeeded: Check device responsiveness.
linuxexample-1234 GazooDeviceBase.check_device_ready successful. It took 2s.
linuxexample-1234 closing switchboard processes
  firmware_version        5.4.0-1034-raspi
```

```shell
$ gdm get-prop linuxexample-1234 hardware_architecture
Creating linuxexample-1234
  hardware_architecture   aarch64
```

```shell
$ gdm get-prop linuxexample-1234 my_optional_prop
Creating linuxexample-1234
  my_optional_prop        A default value
```

```shell
$ gdm set-prop linuxexample-1234 my_optional_prop some_new_value
Creating linuxexample-1234
True
```

```shell
$ gdm get-prop linuxexample-1234 my_optional_prop
Creating linuxexample-1234
  my_optional_prop        some_new_value
```

```shell
$ gdm get-prop linuxexample-1234 new_optional_prop
Creating linuxexample-1234
linuxexample-1234 starting GazooDeviceBase.check_device_ready
linuxexample-1234 waiting up to 3s for device to be connected.
linuxexample-1234 health check 1/3 succeeded: Check device connected.
linuxexample-1234 logging to file /Users/artorl/gazoo/gdm/log/linuxexample-1234-20210504-162950.txt
linuxexample-1234 health check 2/3 succeeded: Check create switchboard.
linuxexample-1234 health check 3/3 succeeded: Check device responsiveness.
linuxexample-1234 GazooDeviceBase.check_device_ready successful. It took 2s.
linuxexample-1234 closing switchboard processes
Traceback (most recent call last):
  File "/Users/artorl/gazoo/gdm/virtual_env/bin/gdm", line 8, in <module>
    sys.exit(main())
  File "/Users/artorl/gazoo/gdm/virtual_env/lib/python3.6/site-packages/gazoo_device/gdm_cli.py", line 119, in main
    return execute_command(command)
  File "/Users/artorl/gazoo/gdm/virtual_env/lib/python3.6/site-packages/gazoo_device/gdm_cli.py", line 68, in execute_command
    fire.Fire(manager_inst, commands, name=cli_name)
  File "/Users/artorl/gazoo/gdm/virtual_env/lib/python3.6/site-packages/fire/core.py", line 141, in Fire
    component_trace = _Fire(component, args, parsed_flag_args, context, name)
  File "/Users/artorl/gazoo/gdm/virtual_env/lib/python3.6/site-packages/fire/core.py", line 471, in _Fire
    target=component.__name__)
  File "/Users/artorl/gazoo/gdm/virtual_env/lib/python3.6/site-packages/fire/core.py", line 681, in _CallAndUpdateTrace
    component = fn(*varargs, **kwargs)
  File "/Users/artorl/gazoo/gdm/virtual_env/lib/python3.6/site-packages/gazoo_device/fire_manager.py", line 172, in get_prop
    value = self.get_device_prop(device_name, prop)
  File "/Users/artorl/gazoo/gdm/virtual_env/lib/python3.6/site-packages/gazoo_device/manager.py", line 744, in get_device_prop
    return self._get_device_prop(device_name, prop)
  File "/Users/artorl/gazoo/gdm/virtual_env/lib/python3.6/site-packages/gazoo_device/manager.py", line 1465, in _get_device_prop
    return device.get_property(prop, raise_error=True)
  File "/Users/artorl/gazoo/gdm/virtual_env/lib/python3.6/site-packages/gazoo_device/base_classes/gazoo_device_base.py", line 381, in get_property
    value = getattr(instance, name)
AttributeError: 'ExampleLinuxDevice' object has no attribute 'new_optional_prop'
```

```shell
$ gdm set-prop linuxexample-1234 new_optional_prop i_did_not_exist_before
Creating linuxexample-1234
True
```

```shell
$ gdm get-prop linuxexample-1234 new_optional_prop
Creating linuxexample-1234
  new_optional_prop       i_did_not_exist_before
```

```shell
$ gdm get-prop linuxexample-1234
Creating linuxexample-1234
linuxexample-1234 starting GazooDeviceBase.check_device_ready
linuxexample-1234 waiting up to 3s for device to be connected.
linuxexample-1234 health check 1/3 succeeded: Check device connected.
linuxexample-1234 logging to file /Users/artorl/gazoo/gdm/log/linuxexample-1234-20210503-174928.txt
linuxexample-1234 health check 2/3 succeeded: Check create switchboard.
linuxexample-1234 health check 3/3 succeeded: Check device responsiveness.
linuxexample-1234 GazooDeviceBase.check_device_ready successful. It took 2s.
linuxexample-1234 closing switchboard processes

Persistent Properties:
  COMMUNICATION_TYPE      SshComms
  DETECT_MATCH_CRITERIA   {<GenericQuery.always_true: 'always_true'>: True}
  DEVICE_TYPE             linuxexample
  commands
			  BOOT_UP_COMPLETE          "echo 'gdm hello'"
			  FIRMWARE_VERSION          'uname -r'
			  GDM_HELLO                 "echo 'gdm hello'"
			  INFO_HARDWARE_ARCHITECTURE 'uname -m'
			  LOGGING                   'tail -F -n /var/log/messages'
			  REBOOT                    'reboot'

  communication_address   192.168.1.168
  hardware_architecture   aarch64
  health_checks
			  check_device_connected
			  check_create_switchboard
			  check_device_responsiveness

  ip_address              192.168.1.168
  model                   Production
  name                    linuxexample-1234
  os                      Linux
  owner                   gdm-authors@google.com
  platform                new_top_secret_platform
  regexes                 {}
  serial_number           56781234
  timeouts
			  BOOT_UP                   60
			  CONNECTED                 3
			  DISCONNECT                60
			  PING_TO_SSH_DELAY         10
			  POWER_CYCLE               2
			  SHELL                     10
			  SHELL_DEVICE_RESPONSIVENESS 5


Optional Properties:
  alias                   None

Dynamic Properties:
  connected               True
  event_parser.healthy    True
  file_transfer.healthy   True
  firmware_version        5.4.0-1034-raspi
  log_file_name           /Users/artorl/gazoo/gdm/log/linuxexample-1234-20210503-174928.txt
  shell_capability.healthy  True
  switchboard.healthy     True
  switchboard.number_transports  2
```

### Examine device logs and events

GDM device logs contain all commands sent by GDM and their respective device
responses. GDM streams device logs (such as `/var/log/syslog`) to aid with
firmware debugging. Additionally, primary devices are able to filter event logs
to search for specific events (such as reboots, crashes, or state changes).

Let's issue a GDM command from the CLI and examine the resulting device logs. \
Issue a reboot through GDM:

```shell
gdm issue linuxexample-1234 - reboot
```

Your output will look like this:

```
$ gdm issue linuxexample-1234 - reboot
Creating linuxexample-1234
linuxexample-1234 starting GazooDeviceBase.check_device_ready
linuxexample-1234 waiting up to 3s for device to be connected.
linuxexample-1234 health check 1/3 succeeded: Check device connected.
linuxexample-1234 logging to file /Users/artorl/gazoo/gdm/log/linuxexample-1234-20210524-170927.txt
linuxexample-1234 health check 2/3 succeeded: Check create switchboard.
linuxexample-1234 health check 3/3 succeeded: Check device responsiveness.
linuxexample-1234 GazooDeviceBase.check_device_ready successful. It took 2s.
linuxexample-1234 starting ExampleLinuxDevice.reboot
linuxexample-1234 offline in 3s.
linuxexample-1234 starting SwitchboardDefault.close_all_transports
linuxexample-1234 SwitchboardDefault.close_all_transports successful. It took 0s.
linuxexample-1234 online in 30s
linuxexample-1234 starting SwitchboardDefault.open_all_transports
linuxexample-1234 SwitchboardDefault.open_all_transports successful. It took 0s.
linuxexample-1234 starting SshDevice.wait_for_bootup_complete
linuxexample-1234 SshDevice.wait_for_bootup_complete successful. It took 5s.
linuxexample-1234 booted up successfully in 46s.
linuxexample-1234 starting SshDevice._after_boot_hook
linuxexample-1234 SshDevice._after_boot_hook successful. It took 0s.
linuxexample-1234 ExampleLinuxDevice.reboot successful. It took 54s.
linuxexample-1234 closing switchboard processes
```

Note the following log line:

> linuxexample-1234 logging to file /Users/artorl/gazoo/gdm/log/linuxexample-1234-20210524-170927.txt.

This is the device log file for the current CLI interaction. Try examining the
file in a text editor. Your device logs might look like this (an excerpt):

```
<2021-05-24 17:10:18.301901> GDM-M: Note: expecting any patterns from ['(.*)Return Code: (\\d+)\\n'] using response lines and 2000 search window in 60s
<2021-05-24 17:10:18.302765> GDM-M: Note: wrote command "echo 'gdm hello';echo Return Code: $?\n" to port 0
<2021-05-24 17:10:23.670547> GDM-1: --- GDM Log Marker ---
<2021-05-24 17:10:23.680706> GDM-1: May 25 00:09:29 ubuntu systemd[1]: Stopped Daily apt download activities.
<2021-05-24 17:10:23.681578> GDM-1: May 25 00:09:29 ubuntu systemd[1]: e2scrub_all.timer: Succeeded.
<2021-05-24 17:10:23.681660> GDM-0: gdm hello
<2021-05-24 17:10:23.682677> GDM-0: Return Code: 0
<2021-05-24 17:10:23.682709> GDM-1: May 25 00:09:29 ubuntu systemd[1]: Stopped Periodic ext4 Online Metadata Check for All Filesystems.
<2021-05-24 17:10:23.683684> GDM-1: May 25 00:09:29 ubuntu systemd[1]: fstrim.timer: Succeeded.
<2021-05-24 17:10:23.716220> GDM-M: Note: found pattern '(.*)Return Code: (\\d+)\\n' at index 0
<2021-05-24 17:10:23.716393> GDM-M: Note: mode any expect completed with '' remaining patterns in 5.4131388664245605s
```

- `GDM-M` logs are the commands GDM wrote to the device. They also contain
  information about GDM's expectations for the response (regular expression,
  timeout) and whether a response was found.
- `GDM-0` logs are device responses.
- `GDM-1` are general device logs (in this case from `/var/log/syslog`).

The digit in `GDM-0` or `GDM-1` denotes the transport number from which the line
was received. Typically responses are received from transport 0 and logs from
transport 1. If only one transport is used (for example: communication over
UART), commands and responses are interleaved in a single transport and have to
be discerned through other means such as regular expressions.

For primary devices, GDM creates a log event file for each device log file. The
log event file has a `-events.txt` suffix. For example, the event file in this
case is
`/Users/artorl/gazoo/gdm/log/linuxexample-1234-20210524-170927-events.txt`.

Try examining the log event file. It should look like this:

```json
{"basic.reboot_trigger": [], "log_filename": "linuxexample-1234-20210524-170927.txt", "raw_log_line": "Note: GDM triggered reboot", "system_timestamp": "2021-05-24 17:09:29.455241", "matched_timestamp": "2021-05-24 17:09:29.458663"}
{"basic.bootup": [], "log_filename": "linuxexample-1234-20210524-170927.txt", "raw_log_line": "May 25 00:09:35 ubuntu kernel: [    0.000000] Booting Linux on physical CPU 0x0000000000 [0x410fd083]", "system_timestamp": "2021-05-24 17:10:23.730872", "matched_timestamp": "2021-05-24 17:10:23.733292"}
```

As you can see, GDM captured two events: one for triggering a reboot
(`"basic.reboot_trigger"`) and a corresponding device boot event (`"basic.bootup"`).
Each primary device defines a set of log event filters. Log event filters used
by this example controller can be found in
[log_event_filters/](log_event_filters).

### Python API controller usage

Now try using the example controller from a Python interpreter. \
The snippet below is roughly equivalent to the CLI commands you ran earlier.

```python
import gazoo_device
import example_controller_package

# Register the example controller package with GDM.
# Note that controller package registration through gazoo_device.register()
# is not persistent: known packages are reset when Python interpreter exits.
gazoo_device.register(example_controller_package)

manager = gazoo_device.Manager()
# By default device creation runs health checks. It is not recommended to skip
# them. If you have to skip health checks, set make_device_ready argument to
# "off" when calling Manager.create_device().
device = manager.create_device("linuxexample-1234")

try:
  foo_response = device.shell("echo 'foo'")  # "foo"
  foo_response, return_code = device.shell(
      "echo 'foo'", include_return_code=True)  # "foo", 0

  firmware_version = device.firmware_version  # "5.4.0-1034-raspi"
  hardware_architecture = device.hardware_architecture  # "aarch64"

  my_optional_prop_before = device.my_optional_prop  # "some_new_value"
  device.my_optional_prop = "another_value"
  my_optional_prop_after = device.my_optional_prop  # "another_value"

  # Optional properties defined at runtime do not have getters or setters and
  # have to be set and retrieved via "set_property" and "get_property".
  device.set_property("new_optional_prop_2", "i_did_not_exist_before")
  new_optional_prop_2 = device.get_property(
      "new_optional_prop_2")  # "i_did_not_exist_before"

  # Properties can also be retrieved through the Manager instance.
  # The code above is roughly equivalent to:
  manager.set_prop("linuxexample-1234", "new_optional_prop_2",
                   "i_did_not_exist_before")
  new_optional_prop_2 = manager.get_device_prop(
      "linuxexample-1234", "new_optional_prop_2")  # "i_did_not_exist_before"

  # Reboot to generate reboot trigger and bootup log events.
  device.reboot()

finally:
  # Close the device instance to release all resources (such as serial ports).
  device.close()
  # Closing the Manager instance automatically closes all devices open through
  # that instance. If you want to close all open devices but don't want to
  # close the Manager instance yet, call manager.close_open_device().
  manager.close()
```

## Conclusion & cleanup

You are now familiar with the process of extending GDM with user-defined
controller packages and using them from CLI and within a test!

As you remember, we've cheated by defining a generic controller for this
codelab. \
As a final step, unregister the example controller package from the GDM CLI to
avoid interference with real device controllers:

```shell
gdm unregister example_controller_package
~/gazoo/gdm/virtual_env/bin/pip uninstall example_controller_package
```

GDM will confirm removal of the controller package:

```shell
$ gdm unregister example_controller_package
Removed package 'example_controller_package' from GDM CLI.
```

Note: only CLI packages are remembered by GDM and thus have to be unregistered.
Package registration via `gazoo_device.register(<package>)` is not persistent.
