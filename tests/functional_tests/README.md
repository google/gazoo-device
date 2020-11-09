# Functional (on-device) test suites for Gazoo devices

## Overview

All test suites inherit from a base class (GdmTestBase).
Each test suite defines the condition for whether its applicable to a
given device. For example:

- CommonTestSuite is applicable to all primary and virtual devices;
- AuxiliaryDeviceCommonTestSuite is applicable to all auxiliary devices;
- FileTransferTestSuite is applicable to all devices with a
  "file_transfer" capability;
- CommPowerCambrionixTestSuite test suite is only applicable to devices
  with a "comm_power_cambrionix" flavor of "comm_power" capability.
- Other test suites may be applicable only to certain device types, or
  to devices only with certain methods or properties.

The full regression test suite for a device type is comprised of all
test suites applicable to it.

## Running on-device tests

To run a test suite:

../run_tests.sh will set up a virtualenv automatically (named test_env),
install the requirements and give you diff coverage stats.
If you already have a virtualenv, you can run the test suites straight
from python.

../run_tests.sh -d functional_tests \
  -f auxiliary_device_common_test_suite.py -t One-Cambrionix

Or:

<test_env>/bin/python auxiliary_device_common_test_suite.py \
  -t One-Cambrionix

To run a specific test:

../run_tests.sh -d functional_tests \
  -f auxiliary_device_common_test_suite.py -t One-Cambrionix \
  --tests test_2002_get_device_prop_can_execute

Or:

<test_env>/bin/python auxiliary_device_common_test_suite.py \
  -t One-Cambrionix --tests AuxiliaryDeviceCommonTestSuite.test_2002_get_device_prop_can_execute

To run several specific tests:

../run_tests.sh -d functional_tests \
  -f auxiliary_device_common_test_suite.py -t One-Cambrionix \
  --tests test_2002_get_device_prop_can_execute, test_2003_redetect

Or:

<test_env>/bin/python auxiliary_device_common_test_suite.py \
  -t One-Cambrionix --tests AuxiliaryDeviceCommonTestSuite.test_2002_get_device_prop_can_execute, \
  AuxiliaryDeviceCommonTestSuite.test_2003_redetect


To run the full regression suite:
../run_tests.sh -d functional_test_suites -f regression_test_suite.py \
  -t One-Cambrionix

Or:

<test_env>/bin/python functional_test_suites/regression_test_suite.py \
  -t One-Cambrionix

## Overview of functional test configs

Each device type has a test config associated with it:
functional_test_configs/{device_type}_test_config.json.
This test config gets loaded anytime a GDM on-device test is run.
The config uses the first device in the provided testbed config.
For example, running a test suite on a Cambrionix testbed
(-t One-Cambrionix) loads
functional_test_configs/cambrionix_test_config.json.

The test configs supply variables needed for specific tests suites, as
well as specify which tests should be run.
"do_not_run_tests" never run.
"slow_tests" and "volatile_tests" do not run in "regression" mode, but
do run in "all" mode of the full regression test suite.
See functional_test_suites/regression_test_suite.py for a more detailed
overview of the functional test runner.

The variables each test suite needs are returned by the
"required_test_config_variables" method of the test suite.
