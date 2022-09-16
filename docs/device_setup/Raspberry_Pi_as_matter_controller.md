# GDM device setup: Raspberry Pi (as a Matter controller)

Supported models: Raspberry Pi 4 with at least 4GB of memory.

Supported kernel images: Ubuntu 21.04 or later.

## Setup

1.  Follow the instructions from
    [Installing prerequisites on Raspberry Pi 4](https://github.com/project-chip/connectedhomeip/blob/master/docs/guides/BUILDING.md#installing-prerequisites-on-raspberry-pi-4)
    section of
    [project-chip/connectedhomeip](https://github.com/project-chip/connectedhomeip)'s
    Building Matter guide to set up the Raspberry Pi.
2.  On the raspberry pi, build `chip-tool` and install it to
    `/usr/local/bin/chip-tool`. Follow the instructions on
    https://github.com/project-chip/connectedhomeip/tree/master/examples/chip-tool#building-the-example-application.

    Ensure that `chip-tool` binary can be run without any issues. The binary
    should produce the output below:

    ```shell
    [1660844066.237092][304338:304338] CHIP:TOO: Missing cluster name
    Usage:
    chip-tool cluster_name command_name [param1 param2 ...]

    +-------------------------------------------------------------------------------------+
    | Clusters:                                                                           |
    +-------------------------------------------------------------------------------------+
    | * accesscontrol                                                                     |
    | * accountlogin                                                                      |
    | * actions                                                                           |
    | * administratorcommissioning                                                        |
    ...
    ```

    Raspberry pi running Ubuntu 22.04 or later may encounter an issue with
    incompatible SSL library.

    ```shell
    chip-tool: error while loading shared libraries: libssl.so.1.1: cannot open shared object file: No such file or directory
    ```

    As a workaround, force install libssl1.1 using the command below:

    ```
    wget http://security.debian.org/pool/updates/main/o/openssl/libssl1.1_1.1.1n-0+deb10u3_arm64.deb
    sudo dpkg -i libssl1.1_1.1.1n-0+deb10u3_arm64.deb
    ```

3.  On the raspberry pi, save the commit SHA the `chip-tool` was built at by
    running

    ```shell
    echo $COMMIT_SHA > ~/.matter_sdk_version
    ```

4.  Ensure that user `pi` can write to `/usr/local/bin` directory. This is
    required for `matter_controller.upgrade` functionality to work properly. Run
    the command below on the raspberry pi:

    ```shell
    sudo chown -R `whoami`:pi /usr/local/bin
    ```

5.  Follow the Raspbian instructions from
    [Raspberry_Pi_SSH_key_setup](./Raspberry_Pi_SSH_key_setup.md) to ensure that
    GDM can detect the raspberry pi as a `rpi_matter_controller`. The output of
    `gdm devices` command should look like:

    ```shell
    $ gdm devices
    Device                         Alias           Type                     Model                Connected
    ------------------------------ --------------- ------------------------ -------------------- ----------

    Other Devices                  Alias           Type                     Model                Available
    ------------------------------ --------------- ------------------------ -------------------- ----------
    rpi_matter_controller-1234     <undefined>     rpi_matter_controller    4 Model B Rev 1.4   available
    ```

6.  For `onnetwork` commissioning, ensure that the raspberry pi and end devices
    of interest are part of the same network either via Ethernet or WiFi.

    If needed, follow the steps below to connect the raspberry pi to WiFi.

    ```shell
    sudo apt-get install network-manager
    sudo nmcli dev wifi connect <SSID> password <PSK>
    ```

    Verify that the raspberry pi can reach the end devices using `ping` command.

7.  Some devices may require PAA certificate information for commissioning.
    Ensure that the relevant certs are available on the Raspberry Pi.
    Development credentials can be found in the
    [credentials/development/paa-root-certs](https://github.com/project-chip/connectedhomeip/tree/master/credentials/development/paa-root-certs)
    directory of project-chip/connectedhomeip repository.

    The default certificate path is `/opt/matter/certs`.

### Optional: Thread Border Router Setup

Requirement:
[NRF52840-DONGLE](https://www.nordicsemi.com/Products/Development-hardware/nrf52840-dongle)

1.  On the host machine, follow the instructions from
    [project-chip/connectedhomeip](https://github.com/project-chip/connectedhomeip)'s
    [Configuring OpenThread Radio Co-processor on nRF52840 Dongle](https://github.com/project-chip/connectedhomeip/blob/master/docs/guides/openthread_rcp_nrf_dongle.md)
    page to build and install the NRF52840-DONGLE RCP firmware.

2.  Plug the NRF52840-DONGLE to the raspberry pi.

3.  On the raspberry pi, install the OpenThread Border Router following Step 2
    and 3 from this
    [instructions](https://openthread.io/codelabs/openthread-border-router#0).

    In Step 2 “Setup OTBR”, use eth0 as the infrastructure network as the
    Raspberry Pi should be connected to the WiFi router via the ethernet (eth0)
    interface:

    ```shell
    INFRA_IF_NAME=eth0 ./script/setup
    ```

    In
    [Step 2 “Setup OTBR”](https://openthread.io/codelabs/openthread-border-router#1),
    skip the part about flashing the RCP firmware if this was done successfully
    in step 1 above.

    After
    [Step 3 “Form a Thread Network”](https://openthread.io/codelabs/openthread-border-router#1),
    you can stop - you have created a Thread network and are ready to commission
    CHIP devices onto it. Note the thread dataset as it will be needed to
    commission CHIP devices onto the network:

    ```shell
    sudo ot-ctl dataset active -x

    0e080000000000010000000300001835060004001fffe00208161de905837b6ba10708fdd61eb482e203ad0510fe8c68576cef838b184b41df13c9e694030f4f70656e5468726561642d323832610102282a0410615a57bd3d170a24ac2a461d37c8e97c0c0402a0fff8
    ```

4.  Set `operational_dataset` as a property for the rpi_matter_controller.

    ```shell
    gdm set-prop <DEVICE NAME> operational_dataset <OPERATIONAL DATASET>
    ```

    Running `gdm get-prop <DEVICE NAME> operational_dataset` should print out
    the operational dataset generated in step 3 above.

## Usage

```shell
# Commission a device on network with 20202021 setup code and assign it node id 100.
gdm issue rpi_matter_controller-1234 - matter_controller commission 100 20202021 --paa_trust_store_path /opt/matter/certs

# Commission a device over thread using dataset generated from `Optional: Thread Border Router Setup` step
gdm issue rpi_matter_controller-1234 - matter_controller commission 100 20202021 --operational_dataset 0e080000000000010000000300001835060004001fffe00208161de905837b6ba10708fdd61eb482e203ad0510fe8c68576cef838b184b41df13c9e694030f4f70656e5468726561642d323832610102282a0410615a57bd3d170a24ac2a461d37c8e97c0c0402a0fff8

# Send a toggle command to the device's onoff cluster at endpoint 1.
gdm issue rpi_matter_controller-1234 - matter_controller send 100 1 onoff toggle []

# Upgrade chip-tool version using a binary from the host machine.
gdm issue rpi_matter_controller-1234 - matter_controller upgrade --build_file=/path/to/chip-tool --build_id=$COMMIT_SHA

# Print commit SHA the chip-tool was built at.
gdm issue rpi_matter_controller-1234 - matter_controller version

# To see all supported functionality
gdm man rpi_matter_controller
```
