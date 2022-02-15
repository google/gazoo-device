# GDM functional (on-device) tests

## Overview

All test suites inherit from a common base class (*GdmTestBase*). \
Each test suite defines a condition for its applicability to a given device. \
For example:

- *CommonTestSuite* is applicable to all primary and virtual devices;
- *AuxiliaryDeviceCommonTestSuite* is applicable to all auxiliary devices;
- *FileTransferTestSuite* is applicable to all devices with a
  *file_transfer* capability;
- *SwitchPowerTestSuite* is applicable to devices with any flavor of
  *switch_power* capability other than *switch_power_ethernet*.
- Other test suites may be applicable only to certain device types, devices
  with only certain methods or properties, or devices with specific optional
  properties set (such as a port number on a programmable power delivery unit
  which powers the device).

The full regression test suite for a device type is comprised of all test suites
that are applicable to it.

### Special test labels

There are 3 types of special regression test labels:

1. Slow tests. These are stable, but too slow to run in presubmit. These only
   run in nightly regression testing.
2. Volatile tests. These tests run are flaky and are automatically retried once.
   Volatile tests run in presubmit and nightly regression.
3. Do not run tests. Either the device type does not support that functionality,
   or the test can put the device in a bad state. These tests do not run.

Tests that do not have any of these 3 labels constitute the majority of the
tests and run in both presubmit and nightly regression testing.

The labels apply to a combination of a device type and a test rather than
to the test itself. Most of the on-device tests are shared between multiple
devices. A test that is flaky on one device can be stable on a different device.

### Functional test configs

Each device type has a dedicated functional test config
(*\<device_type\>_test_config.json*) which contains test label information and
some variables required by the test suites. The configs can be found in the
[configs/](configs/) directory.

"volatile_tests", "slow_tests", and "do_not_run_tests" config entries identify
individual tests or entire test suites which are volatile, slow, or should not
be run for a given device type.

Tests in functional test configs are specified as a list of test names (format: SuiteName.TestName) or
test suite names (format: SuiteName). For example:

```json
"do_not_run_tests": ["CommonTestSuite.test_0001_factory_reset", "FileTransferTestSuite"]
```

### Run types

The regression run type determines the set of tests that is going to be run. \
4 run types are supported:

* **Full** (nightly regression) runs exclude only "do_not_run" tests. "volatile"
  tests are retried once.
* **Presubmit** runs exclude "do_not_run", "slow", tests. "volatile" tests are
  retried once.
* **Stable** runs exclude "do_not_run" and "volatile" tests.
* **Volatile** runs only include "volatile" tests which aren't labeled as
  "do_not_run".

## Running on-device tests

If a list of test suites to run is not specified, all applicable test suites for
the given device will be run. Similarly, if individual tests to run are not
specified, all tests in the applicable (or selected) test suites will be run.

### Prerequisites

1. [Install GDM on the host](https://github.com/google/gazoo-device#install)
   (if you haven't already).
2. [Set up a local device and detect it with GDM](https://github.com/google/gazoo-device/blob/master/docs/device_setup).
3. Create a testbed file for the device.

   Find the GDM device name:

   ```
   gdm devices
   ```

   Then make a copy of the provided example testbed and replace "device-1234"
   and "device" with your device name and type:

   ```shell
   cp ~/gazoo/testbeds/One-Exampledevice.yml ~/gazoo/testbeds/<your-device-name>.yml
   # Now update the "Name" and "id" fields in
   # ~/gazoo/testbeds/<your-device-name>.yml.
   ```

4. Set up a virtual environment and install *gazoo-device* and
   *gazoo-device.tests* in editable mode:

   ```shell
   cd gazoo_device/tests/
   python3 -m virtualenv test_env
   source test_env/bin/activate
   pip install -e ../../ ./
   ```

### Run tests

* Run all presubmit tests (excludes slow tests):

  ```shell
  python3 functional_test_runner.py --config ~/gazoo/testbeds/device-1234.yml \
    --run_type presubmit
  ```

* Run all applicable tests (presubmit + volatile + slow, aka full regression):

  ```shell
  python3 functional_test_runner.py --config ~/gazoo/testbeds/device-1234.yml
  ```

* Run specific functional test files (in order):

  ```shell
  python3 functional_test_runner.py --config ~/gazoo/testbeds/device-1234.yml \
    --files switch_power_test_suite,auxiliary_device_common_test_suite
  ```

* Run specific functional tests (in order; tests can be from different suites):

  ```shell
  python3 functional_test_runner.py --config ~/gazoo/testbeds/device-1234.yml \
    --tests \
  CommonTestSuite.test_shell,SwitchPowerTestSuite.test_switch_power_on_and_off
  ```

* Run only volatile tests:

  ```shell
  python3 functional_test_runner.py --config ~/gazoo/testbeds/device-1234.yml \
    --run_type volatile
  ```
