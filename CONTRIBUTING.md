# How to Contribute

This section is for you if you're interested in adding support for your
device(s) to GDM.

**Contributions to the repository are not allowed yet.**
This is an "early access" version of Gazoo Device Manager.
The full release of GDM will happen in February 2021, after which
we'll be happy to accept external contributions. However, you're welcome
to write your own *local* device controllers on top of the repository
(you just can't check them in yet).

With the full GDM release, device controller packages will be separate
from the GDM architecture. However, since this is an "early access"
prototype, the separation isn't there yet. To experiment with adding a
new device, check out the GDM source code and make a local commit on
top of it.

This documentation is a brief overview of the contributor process. More
detailed documentation will be available with the full GDM
release. In the meantime, it's best to reference existing examples of
device/base classes, communication types and transports, and
capabilities. If you have specific questions, feel free to email
gdm-authors@google.com with your question.

## Table of contents

1. [Contributor License Agreement](#contributor-license-argreement)
2. [Code reviews](#code-reviews)
3. [Community guidelines](#community-guidelines)
4. [Contributor workflow (Future)](#contributor-workflow-future)
5. [Overview of GDM architecture](#overview-of-gdm-architecture)
    1. [Manager](#manager)
    2. [Base classes](#base-classes)
    3. [Device classes](#device-classes)
    4. [Auxiliary devices](#auxiliary-devices)
    5. [Capabilities](#capabilities)
    6. [Device communication architecture (Switchboard)](#device-communication-architecture-switchboard)
6. [Adding a new device controller](#adding-a-new-device-controller)
    1. [Primary device controller](#adding-a-new-device-controller)
        1. [Health check flow](#health-check-flow)
    2. [Auxiliary device controller](#adding-a-new-device-controller)
7. [Adding a new communication type](#adding-a-new-communication-type)
8. [Adding a new transport type](#adding-a-new-communication-type)
9. [Adding a new capability](#adding-a-new-capability)

## Contributor License Agreement

Contributions to this project must be accompanied by a Contributor License
Agreement. You (or your employer) retain the copyright to your contribution;
this simply gives us permission to use and redistribute your contributions as
part of the project. Head over to <https://cla.developers.google.com/> to see
your current agreements on file or to sign a new one.

You generally only need to submit a CLA once, so if you've already submitted one
(even if it was for a different project), you probably don't need to do it
again.

## Code reviews

All submissions, including submissions by project members, require review. We
use GitHub pull requests for this purpose. Consult
[GitHub Help](https://help.github.com/articles/about-pull-requests/) for more
information on using pull requests.

## Community guidelines

This project follows [Google's Open Source Community
Guidelines](https://opensource.google/conduct/).

## Contributor workflow (future)

TODO: provide more detailed contributor instructions. This is not
applicable at the moment as external contributions to the repository are
not allowed.

1. Open a new issue (or use an existing one) to provide context on the
   bug or feature request. Include a description of the proposed
   implementation. We'll review it and provide suggestions.
2. After your implementation idea is reviewed, proceed to writing code
   and tests.
3. Your change must have unit test coverage of >= 90% and pass
   all unit tests. Use the `run_tests.sh` script to run all unit tests
   and report on unit test diff coverage. If your coverage is lower than
   90%, add more unit tests to cover your changes.
   See [tests/README.md](tests/README.md) and
   [tests/functional_tests/README.md](tests/functional_tests/README.md)
   for more information about unit and functional (on-device) GDM
   regression tests.
4. Include proof of functional (on-device) testing. For now this can be
   accomplished by interacting with a device from a Python interpreter.
   Your interaction must test the functionality you're changing.

## Overview of GDM architecture

### Manager

The `Manager` class ([gazoo_device/manager.py](gazoo_device/manager.py))
is responsible for managing known devices and their configuration files.
It also keeps track of open device instances. `FireManager`, a subclass
of `Manager`, serves as the entry point for the GDM dynamic CLI.

### Base classes

Devices commonly share a platform, which means that intractions with
many smart devices are similar. Such platform-specific features
typically go into base classes. For example, a base class for all smart
devices running on Linux could be `LinuxDevice`. Features which go into
the base class are often tied to the communication type (for example:
`shell()` method implementation and a `file_transfer` capability) or to
a platform-specific binary. Base classes can be found in
[gazoo_device/base_classes/](gazoo_device/base_classes/). GDM comes with a
working example of a base class: `SshDevice`
([gazoo_device/base_classes/ssh_device.py](gazoo_device/base_classes/ssh_device.py)).

All base classes inherit from the common device interface defined in
[gazoo_device/base_classes/first_party_device_base.py](gazoo_device/base_classes/first_party_device_base.py)
(the "first_party" name is historic). Base classes may remain abstract.

### Device classes

A device class is a controller for a certain device. There's a 1:1
mapping between physical devices and the corresponding device classes.
Device classes typically derive from base classes, although this is not
required (for example, if you have a very unique device controller).
Device classes typically extend the base class with device-specific
functionality. Device classes may not be abstract (in other words, they
must implement every method and property defined by the abstract
`FirstPartyDeviceBase` interface).

### Auxiliary devices

GDM recognizes several supporting (auxiliary) devices. These are
typically used to interact with the device under test. For example,
Cambrionix is a USB power supply, which allows to turn USB power or or
off programmatically, which can come in handy during power testing.
Auxiliary devices are typically not used directly, but are rather
interacted with through methods or capabilities of primary devices. For
example, the `device_power` capability corresponds to the ability of
Cambrionix to toggle device power.

### Capabilities

Any additional features beyond the basics required by
`FirstPartyDeviceBase` should be implemented as capabilities. Whereas
the device classes and base classes follow an inheritance model,
capabilities are based on composition. Device classes can mix and match
different capability flavors (implementations).

All capabilities inherit from the `CapabilityBase` interface defined in
[gazoo_device/capabilities/interfaces/capability_base.py](gazoo_device/capabilities/interfaces/capability_base.py).

A capability consists of the following:
* an abstract interface in [gazoo_device/capabilities/interfaces/](gazoo_device/capabilities/interfaces/).
* One or more flavors of the capability. All flavors of a capability
must implement the abstract interface. Ideally API signatures of
different capability flavors are identical (even though the
implementation is different).
* A capability definition in a base or device class. The definition
adds the capability to the device or base class and supplies it with the
necessary arguments.

### Device communication architecture (Switchboard)

Switchboard is the multiprocessing architecture behind GDM's device
communications. It handles device communication, logging, and event
filtering. The `Switchboard` class
([gazoo_device/switchboard/switcboard.py](gazoo_device/switchboard/switcboard.py))
exposes several high-level device communication methods, such as
`send_and_expect()` and `expect()`. Base and device classes use
Switchboard to communicate with physical devices.

Switchboard uses several child processes to accomplish its goals. It
uses 1 or more `TransportProcess`es, a `LogFilterProcess`, and a
`LogWriterProcess`.
* Each `TransportProcess` manages a single device transport, which is a
bidirectional communication channel with the device (such as an `ssh`
subprocess).
* The `LogWriterProcess` records all device communications to a device
log file.
* The `LogFilterProcess` looks for specific event markers in the logs
and records them to a separate event file. The event markers are defined
by JSON filters ([gazoo_device/filters/](gazoo_device/filters/)).

## Adding a new device controller

### Primary device controller

Primary device controllers implement all methods of the
`FirstPartyDeviceBase` interface
([gazoo_device/base_classes/first_party_device_base.py](gazoo_device/base_classes/first_party_device_base.py)).
The typical pattern is to create a base class corresponding to a common
device platform and then create one or more device controllers
inheriting from the base class. However, creating a base class is not
required, and all device functionality can reside directly in the device
controller. Base classes go under
[gazoo_device/base_classes/](gazoo_device/base_classes/), and primary
device controllers go under
[gazoo_device/primary_devices/](gazoo_device/primary_devices/). The new
base class (or the device controller class) must inherit from
`GazooDeviceBase`
([gazoo_device/base_classes/gazoo_device_base.py](gazoo_device/base_classes/gazoo_device_base.py)).
GDM comes with a functional base class
([gazoo_device/base_classes/ssh_device.py](gazoo_device/base_classes/ssh_device.py))
and a somewhat contrived example of a primary device controller
([gazoo_device/primary_devices/linux_example.py](gazoo_device/primary_devices/linux_example.py)).

A device controller typically has the following:
* a logger instance (`logger = gdm_logger.get_gdm_logger()`).
* A `COMMANDS` dictionary, where the key is a human-readable command
  description (`"FIRMWARE_VERSION"`), and the value is the command to
  retrieve it.
* A `REGEXES` dictionary, where the key is a human-readable description
  typically matching the COMMANDS entry (`"FIRMWARE_VERSION"`), and the
  value is the regex to retrieve the desired value from the command
  response (`r"(\d.\d+)"`).
* A `TIMEOUTS` dictionary, where the key is the name of the operation,
  and the value is the timeout in seconds for it (`{"REBOOT": 30}`).
* A `COMMUNICATION_TYPE` class constant, which is a string specifying
  which communication type should be used
  (`COMMUNICATION_TYPE = "SshComms"`). All possible communication types
  can be found in
  [gazoo_device/switchboard/communication_types.py](gazoo_device/switchboard/communication_types.py)
  (see `SUPPORTED_CLASSES`).
* A `_COMMUNICATION_KWARGS` class dictionary, which contains all
  communication arguments *other* than the communication address
  (`comms_address`). For example:
  `_COMMUNICATION_KWARGS = {"ssh_key_type": None, "username": "root"}`.
  Refer to `__init__` methods of communication type classes to see the
  supported arguments and their purpose.
* A `_default_filters` class constant, which is a list of strings
  specifying the relative paths to log event filters for the device
  (`_default_filters = ["linux/basic.json", "linux/crashes.json"]`).
* One or more log event filters (under
  [gazoo_device/filters/](gazoo_device/filters/)). See the
  included event filters to understand the expected JSON format.
  * At a minimum, each device has a *basic.json* filter, which declares
    "bootup" and "reboot_trigger" events. The "bootup" event should
    match a log line emitted by the device only once during boot up. The
    "reboot_trigger" events are logged by GDM itself. A typical reboot
    implementation will log a certain message and then issue a device
    command to reboot. Make sure that log line emitted by the device
    controller matches the event filter (`GDM triggered reboot` is
    typical).
  * Additional events, such as crashes or state changes, can be appended
    to the *basic.json* filter or a separate filter file.
  * The event name used by GDM is a combination of the filter file name
    and the event name (`"basic.bootup"`, `"basic.reboot_trigger"`).
* An `__init__` method, which updates `self.commands`, `self.regexes`,
  and `self.timeouts` with key-value pairs from `COMMANDS`, `REGEXES`,
  and `TIMEOUTS` dictionaries.
* An `is_connected` class method, which determines whether the device is
  connected to the host. The method is given the full device config
  (`device_config`). The typical implementation checks whether the main
  communication port
  (`device_config["persistent"]["console_port_name"]`) is visible to the
  host, which may be pinging the IP address or checking if the serial
  path exists.
* One or more health check methods (the naming convention is
  `check_<action>`, such as `check_device_responsiveness`).
  * Health check methods check that the device is ready for use. Typical
    use cases are checking device responsiveness and ensuring the
    testbed is set up correctly. If the device is not ready, an error
    specifying the issue should be raised. Errors raised by health
    checks must be subclasses of `CheckDeviceReadyError`. See
    [gazoo_device/errors.py](gazoo_device/errors.py) for a full list of
    possible errors. While most of the common errors already exist, you
    might want to define a new error type if you have a more specific
    health check.
  * The full list of health checks to run must be declared in a
    `health_checks` property. The property must return a list of
    methods. The health checks will run in order. Note that
    `GazooDeviceBase` defines two additional health check methods which
    are typically run by all devices. The typical return value of
    `health_checks` is `[self.device_is_connected, self.check_create_switchboard, <additional health checks>]`.
* A `recover` method, which accepts an error raised by a health check
  (a subclass of `CheckDeviceReadyError`) and runs an appropriate
  recovery mechanism. If there's no recovery mechanism for the given
  error, it should be reraised (`raise error`). Note that the most
  common recovery mechanism is rebooting or power cycling the device.
* A `shell` method, which executes a given shell command on the device.
  The typical implementation sends the command to the device and expects
  a regular expression (response + [optionally] a return code) back.
  `shell()` is typically implemented by calling
  `self.switchboard.send_and_expect`. Note that in some cases there may
  not be a `shell` method (if the device doesn't support shell command
  execution), but the vast majority of devices should implement it.
  * Most other methods (such as `reboot()`) should use `shell()` to
    control the device instead of calling `send_and_expect()` directly.
* A `get_detection_info` method, which queries the device for all
  persistent properties (`self.props["persistent_identifiers"]`) during
  detection. Optional (settable) properties (`self.props["options"]`)
  should be initialized to an appropriate value (typically `None`) here
  as well. The method should return a tuple of
  `self.props["persistent_identifiers"], self.props["options"]`.
  * You don't need to worry about storing the values in a file. GDM
    automatically stores persistent and optional device configs to files
    (`/gazoo/gdm/conf/devices.json` and
    `/gazoo/gdm/conf/device_options.json`).
  * The communication address of the device will already be populated by
    GDM. It is available as `self.communication_address`.
  * There are two persistent properties that must be populated: "model"
    and "serial_number".
    * "model" refers to the hardware model of the device (such as
      prototype, development, or production).
    * "serial_number" is typically the device's serial number, but can
      be any persistent *unique* identifier. Note that the 4 last
      characters of this property are used to create the device name,
      which has the format `devicetype-1234`.
* Implementations of other abstract methods (such as `reboot`,
  `wait_for_bootup_complete`). These methods should use the `shell`
  method to communicate with the device (where possible).
* Additional properties. There are 3 types of properties: persistent,
  dynamic, and settable (formerly known as optional). Use the
  appropriate decorator to define each property type
  (`@decorators.PersistentProperty`, `@decorators.DynamicProperty`, or
  `@decorators.SettableProperty`). The decorators can be found in
  [gazoo_device/decorators.py](gazoo_device/decorators.py).
  * Persistent properties are constant for a physical device. A good
    example is the device's serial number. These properties are
    retrieved during detection (`gdm detect`) and stored in a config
    file.
  * Dynamic properties can change at any time. The values of these
    properties are not cached. Instead, they are always retrieved at
    runtime. An example of a dynamic property is "firmware_version".
  * Settable properties are optional properties which can be set by the
    user, but are not required by GDM. Some examples include accounts,
    passwords, or names and ports of optional supporting devices (such
    as a USB hub).
* Additional capability definitions.
  * All device functionality beyond the basics required by
    `FirstPartyDeviceBase` should go into capabilities.
  * Each capability must be denoted by
    `@decorators.CapabilityDecorator(<capability class>)`. Note that the
    name of the capability definition must match the expected name for
    the capability. The expected name is generated from the interface by
    removing the "Base" suffix and converting the `PascalCase` interface
    name into `snake_case` capability name:
    `FileTransferBase` -> `file_transfer`.
  * The capability definition should return
    `self.lazy_init(<capability_class>, arg1=value1, arg2=value2)`.
    Capabilities use lazy initialization via
    `GazooDeviceBase.lazy_init`. It is strongly preferred to pass all
    capability `__init__` arguments via keywords.
  * Capability definitions allow for additional flexibility. For
    example, it is possible to pass some device-specific values (like a
    `self.commands` dictionary) during initialization.
  * To reset (re-initialize) a capability, issue
    `self.reset_capability(<capability_class>)` and access the
    capability again.
  * Full example of a capability definition:
  ```
    @decorators.CapabilityDecorator(file_transfer_scp.FileTransferScp)
    def file_transfer(self):
        """File transfer capability for moving files from and to the device.

        Returns:
            FileTransferScp: file transfer capability using "scp" command.
        """
        return self.lazy_init(file_transfer_scp.FileTransferScp,
                              ip_address_or_fn=self.ip_address,
                              device_name=self.name,
                              add_log_note_fn=self.switchboard.add_log_note,
                              user=self._COMMUNICATION_KWARGS["username"],
                              ssh_key_type=self._COMMUNICATION_KWARGS["ssh_key_type"])
  ```

All public methods which do not return a value must be decorated with
`@decorators.LogDecorator(logger)`. The log decorator will log messages
when a method begins and finishes executing (including how long the
method took), as well as specially-formatted messages for errors.
Decorator compliance (capability, property, and log decorator) will be
enforced via unit tests. It is currently not enforced as unit tests have
not been released to the public yet (GDM is at a prototype stage).

#### Health check flow

There are 3 ways to execute health checks:
1. during device detection (required; see the caveat below);
2. during device creation (optional as `make_device_ready` can be set to
   `off`, but is strongly recommended);
3. on-demand via `<device>.make_device_ready()` or through
   `Manager`/`FireManager` methods.

There are 3 modes (settings) in which health checks
(`make_device_ready`) can run:
1. if the setting is `off`, `make_device_ready` returns immediately
   without checking anything.
2. If the setting is `check_only`, any encountered errors will be
   reraised, and recovery will **not** be attempted;
3. If the setting is `on`, recovery (if available) will be attempted in
   case any error is encountered.

When health checks (`make_device_ready`) are called:
1. if the setting is `off`, `make_device_ready` returns immediately
   without checking anything.
2. `check_device_ready()` is called, which will call each health check
   method in order.
3. If `check_device_ready()` doesn't raise an error, the flow is
   complete. Otherwise, if an error is encountered, it is caught, and
   `recover(error)` is called.
   * If recover() does not define a recovery method for the error, it is
     reraised.
   * If recover() does define a recovery method for the error, it is
     called.
4. `check_device_ready()` is called again to verify that the device has
   successfully recovered from the error. If an error is encountered
   (even a different one), it is reraised.
   * Note that `make_device_ready()` currently cannot recover from more
     than 1 error in a single call.

Caveat: be careful with accessing persistent properties (and
capabilities which use them) in health checks. There's nothing special
about running health checks during device creation or on-demand later,
but running them during device detection presents a corner case. When
health checks run during detection, persistent properties have not been
populated by `get_detection_info` yet. If you must use a persistent
property during a health check, consider making a getter function for it
and using the getter during the health check. The function can then be
used to populate the persistent property in `get_detection_info`.
Alternatively, if the health check depends on persistent properties and
is not essential, it can be skipped during the detection process by
checking the value of `self.is_detected()`, which is `False` during the
detection process.

### Auxiliary device controller

Auxiliary devices are very similar to primary devices, but the
requirements are much less stringent. Auxiliary devices have their own
interface and base class (`AuxiliaryDeviceBase` and `AuxiliaryDevice` in
[gazoo_device/base_classes/](gazoo_device/base_classes/)). New auxiliary
devices should go under
[gazoo_device/auxiliary_devices/](gazoo_device/auxiliary_devices/) and
must inherit from `AuxiliaryDevice`. Auxiliary devices are not required
to have a Switchboard and define a communication type. In fact, only
Raspberry Pi currently does so. Auxiliary devices are very similar to
primary devices in all other aspects.

## Adding a new communication type

A communication type is a combination of one or more transports. Some
(included) examples are `SerialComms` and `SshComms`. An imaginary
example could be `SerialSshComms`, which would use a serial transport
and an SSH one. Communication types are defined in
[gazoo_device/switchboard/communication_types.py](gazoo_device/switchboard/communication_types.py)
and derive from the `CommunicationType` abstract base class (ABC).
Communication types typically implement the following methods:
* `get_comms_addresses()`: returns a list of all communication addresses
(such as IP address or a serial path) on the host which can be used by a
device using this communication address. For example, for serial
devices, this typically means listing USB entries under /dev. IP
addresses are typically provided as an argument to detection
(`--static_ips`).
* `get_transport_list()`: returns a list of initialized transports to be
used by the communication type.
* `get_identifier()`: returns a line identifier, which tells GDM whether
an incoming log line is a log, a device response, or should get
classified as "unknown". Line identifiers can be found in
[gazoo_device/switchboard/line_identifier.py](gazoo_device/switchboard/line_identifier.py).

Each device class defines what communication type it uses in the
`COMMUNICATION_TYPE` class constant (such as
`COMMUNICATION_TYPE = "SshComms"`). Any additional keyword arguments
pertinent to the communication setup (besides the main communication
address) are placed in the `_COMMUNICATION_KWARGS` dictionary of the
device class. The main communication address gets populated by GDM
automatically after detection.

Each communication type defines new (or reuses existing) detection
queries for the communication type in
[gazoo_device/detect_criteria.py](gazoo_device/detect_criteria.py).
For example, for serial devices, the query is to retrieve the USB
product name. For SSH devices, there are several queries, each of which
runs a certain shell command on the device. During the detection
process, GDM:
1. identifies all potential connections by calling
`get_comms_addresses()` of all supported communication types;
2. filters out connections corresponding to already known devices;
3. runs all detection queries and records their responses for each
potential connection;
4. identifies all device classes which could use this communication type
by checking their communication type
(`<device_class>.COMMUNICATION_TYPE`).
5. asks each applicable device class whether the connection should be
associated with the device class by checking whether the recorded
detection query responses satisfy the detection match criteria specified
by the device class (`<device_class>.DETECT_MATCH_CRITERIA`).

## Adding a new transport type

A transport is a bidirectional communication channel with the device.
Most GDM device communications go through transports. The most prominent
exception to this is HTTP requests, which don't quite fit in with the
line-based transport architecture, and are performed by
[gazoo_device/utility/http_utils.py](gazoo_device/utility/http_utils.py).

Transports can be found in the
[gazoo_device/switchboard/](gazoo_device/switchboard/) folder
(\*\_transport.py). Each transport implements a basic transport
interface defined in
[gazoo_device/switchboard/transport_base.py](gazoo_device/switchboard/transport_base.py),
main methods of which are for closing, opening, reading from, and
writing to the transport.

Note that transports are managed by `TransportProcess`es
([gazoo_device/switchboard/transport_process.py](gazoo_device/switchboard/transport_process.py)),
which are child processes. The main process does not interact with
transports directly. Instead, it sends commands to the child processes.

For a typical trasport which implements the read/write/close/open
methods, you do not need to modify the `TransportProcess` class.
However, sometimes a transport needs to have extra capabilities. In this
case you'll want to enable the `TransportProcess` class to handle
additional commands. This is seldom used, so this architecture isn't
the cleanest. For an example of how to do this, see how the
`JLinkTransport`
([gazoo_device/switchboard/jlink_transport.py](gazoo_device/switchboard/jlink_transport.py))
handles flashing devices (the `flash()` method). To understand how the
command is sent from the main process (Switchboard) to the transport,
search for "CMD_TRANSPORT_JLINK_FLASH" in
[gazoo_device/switchboard/switchboard.py](gazoo_device/switchboard/switchboard.py)
and
[gazoo_device/switchboard/transport_process.py](gazoo_device/switchboard/transport_process.py).

## Adding a new capability

Any public functionality beyond the basics required by the primary
device interface should be placed in capabilities.

Each capability consists of 3 parts:

1. Capability interface. These are found in
   [gazoo_device/capabilities/interfaces](gazoo_device/capabilities/interfaces).
   The capability interface defines a device-agnostic contract which all
   implementations will adhere to. Each interface must inherit from the
   CapabilityBase class and should be abstract. Note that the capability
   name is derived from the interface class name. For example:
   `FileTransferBase` -> `file_transfer`.
2. One or more capability flavors (implementations). Each must inherit
   from the relevant capability interface. For example:
   `FileTransferBase` -> `FileTransferScp`, `FileTransferAdb`.
   Make sure to call
   `super().__init__(device_name=<name of the device using the capability>)`
    in the capability's `__init__`.
3. Device capability definitions. This part defines that a certain
   device has a capability. Note that the capability name must match
   the name derived from the interface. For example, a class using
   `FileTransferAdb` must define the capability as
   `def file_transfer(self):`. Use the capability decorator
   (`CapabilityDecorator` in
   [gazoo_device/decorators.py](gazoo_device/decorators.py)) to denote
   capability definitions. Use `GazooDeviceBase.lazy_init` to initialize
   the capability.
