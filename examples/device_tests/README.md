# Example device tests with GDM

This directory contains an example device test using GDM with two different test
frameworks:
[unittest](https://docs.python.org/3/library/unittest.html#module-unittest) and
[Mobly](https://github.com/google/mobly). \
GDM is framework-agnostic and can be used with any Python test framework.

## Table of contents

1. [Common prerequisites](#common_prerequisites)
2. [GDM + unittest](#gdm_unittest)
3. [GDM + Mobly](#gdm_mobly)

## Common prerequisites

All examples below require that you have:

1. [installed GDM](https://github.com/google/gazoo-device/blob/master/README.md#install);
2. [connected a device to your host and detected the device with GDM](https://github.com/google/gazoo-device/tree/master/docs/device_setup);
3. checked that your device is shown as "connected" or "available" in output of
   `gdm devices`;
4. checked out the source code for the example tests:

   ```shell
   git clone https://github.com/google/gazoo-device.git
   cd gazoo-device/examples/device_tests
   ```

5. created and activated a virtual environment for the test:

   ```shell
   python3 -m virtualenv test_env
   source test_env/bin/activate
   ```

   If `virtualenv` is not installed on your host, run `pip3 install virtualenv`.

## GDM + [unittest](https://docs.python.org/3/library/unittest.html#module-unittest)

This is the simplest device test example. It uses Python's built-in `unittest`
framework and does not provide any advanced testbed configuration capabilities.
All test setup information (such as the name of the device to use) is provided
via CLI flags.

Source code: [unittest_example_test.py](unittest_example_test.py).

### Prerequisites

#### Install test requirements in your virtual environment

```shell
pip install -r unittest_test_requirements.txt
```

### How to run

This simple test setup directly accepts the name of the device (`device-1234` in
the example below) as a command-line argument:

```
python3 unittest_example_test.py -d device-1234
```

Test output should look like this:

```
$ python3 unittest_example_test.py -d cambrionix-jl0y
test_reboot (__main__.UnittestExampleRebootTest)
Reboots the device. ... 06-01 18:08:58.933 INFO Creating cambrionix-jl0y
06-01 18:08:58.934 INFO cambrionix-jl0y starting AuxiliaryDevice.check_device_ready
06-01 18:08:58.934 INFO cambrionix-jl0y health check 1/2 succeeded: Check device connected.
06-01 18:08:59.139 INFO cambrionix-jl0y health check 2/2 succeeded: Check clear flags.
06-01 18:08:59.139 INFO cambrionix-jl0y AuxiliaryDevice.check_device_ready successful. It took 0s.
06-01 18:08:59.139 INFO Created device for test: cambrionix-jl0y
06-01 18:08:59.140 INFO cambrionix-jl0y starting Cambrionix.reboot
06-01 18:09:02.272 INFO cambrionix-jl0y Cambrionix.reboot successful. It took 3s.
ok

----------------------------------------------------------------------
Ran 1 test in 3.368s

OK
```

## GDM + [Mobly](https://github.com/google/mobly)

Mobly allows users to specify testbed configuration via YAML files and provides
a predefined logging configuration.

Source code: [mobly_example_test.py](mobly_example_test.py).

### Prerequisites

#### Create a testbed file for the device

1. Find the GDM device name:

   ```
   gdm devices
   ```

2. Make a copy of the provided example testbed and replace the placeholder
   device name and type:

   ```shell
   cp ~/gazoo/testbeds/One-Exampledevice.yml ~/gazoo/testbeds/<your_device_name>.yml
   # Now update the testbed name and device name in the testbed file.
   ```

Here's an example of what your testbed file could look like for a Raspberry Pi
(`~/gazoo/testbeds/raspberrypi-1234.yml`):

```
TestBeds:
  - Name: Testbed-One-Raspberrypi-01
    Controllers:
      GazooDevice:
        - id: 'raspberrypi-k23o'
```

#### Install test requirements in your virtual environment

```shell
pip install -r mobly_test_requirements.txt
```

### How to run

Provide the Mobly testbed config as a command-line argument to the test:

```shell
python3 mobly_example_test.py --config ~/gazoo/testbeds/<your_device_name>.yml
```

Your test output should look like this:

```
$ python3 mobly_example_test.py --config ~/gazoo/testbeds/cambrionix-jl0y.yml
[Testbed-One-Cambrionix-01] 06-01 18:15:20.732 INFO Test output folder: "/tmp/logs/mobly/Testbed-One-Cambrionix-01/06-01-2021_18-15-20-732"
[Testbed-One-Cambrionix-01] 06-01 18:15:20.733 INFO ==========> MoblyExampleRebootTest <==========
[Testbed-One-Cambrionix-01] 06-01 18:15:20.755 INFO [Test] test_reboot
[Testbed-One-Cambrionix-01] 06-01 18:15:20.756 INFO Creating cambrionix-jl0y
[Testbed-One-Cambrionix-01] 06-01 18:15:20.756 INFO cambrionix-jl0y starting AuxiliaryDevice.check_device_ready
[Testbed-One-Cambrionix-01] 06-01 18:15:20.757 INFO cambrionix-jl0y health check 1/2 succeeded: Check device connected.
[Testbed-One-Cambrionix-01] 06-01 18:15:20.996 INFO cambrionix-jl0y health check 2/2 succeeded: Check clear flags.
[Testbed-One-Cambrionix-01] 06-01 18:15:20.997 INFO cambrionix-jl0y AuxiliaryDevice.check_device_ready successful. It took 0s.
[Testbed-One-Cambrionix-01] 06-01 18:15:20.998 INFO Created devices for test: ['cambrionix-jl0y']
[Testbed-One-Cambrionix-01] 06-01 18:15:20.999 INFO cambrionix-jl0y starting Cambrionix.reboot
[Testbed-One-Cambrionix-01] 06-01 18:15:24.136 INFO cambrionix-jl0y Cambrionix.reboot successful. It took 3s.
[Testbed-One-Cambrionix-01] 06-01 18:15:24.140 INFO [Test] test_reboot PASS
[Testbed-One-Cambrionix-01] 06-01 18:15:24.149 INFO Summary for test class MoblyExampleRebootTest: Error 0, Executed 1, Failed 0, Passed 1, Requested 1, Skipped 0
[Testbed-One-Cambrionix-01] 06-01 18:15:24.151 INFO Summary for test run Testbed-One-Cambrionix-01@06-01-2021_18-15-20-732: Error 0, Executed 1, Failed 0, Passed 1, Requested 1, Skipped 0
```
