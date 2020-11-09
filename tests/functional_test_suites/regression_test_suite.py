# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Regression Test Suite.

Test suite that runs the regression tests for a particular testbed model.

Note: There are 3 types of regression tests:
1) Slow tests. These are stable, but too slow to run in presubmit. These only run in nightly
   regressions.
2) Volatile tests. These do not run in presubmit due to flakiness, but do run in nightly
   regressions.
3) Do not run tests. Either the device type does not support that functionality,
   or the test can put the device in a bad state. These tests do not run.

All other tests (formerly "regression tests") are 1) stable and 2) quick enough to run in presubmit
    (suite run time under ~30 minutes). They run in both presubmit and nightly regressions.
    The set of applicable regression tests is identified at runtime by checking whether each
    available test suite is applicable to the device type under test.

Examples:
   Run the Cambrionix presubmit tests (excludes volatile & slow):
   ./run_tests.sh -d functional_test_suites -f regression_test_suite.py -t One-Cambrionix

   Run just the volatile tests:
   ./run_tests.sh -d functional_test_suites -f regression_test_suite.py -t One-Cambrionix \
        --tests volatile

   Run all applicable tests (stable + volatile + slow):
   ./run_tests.sh -d functional_test_suites -f regression_test_suite.py -t One-Cambrionix \
        --tests all

Note:
    Determines "slow", "volatile", and "do_not_run" tests via
    ../functional_test_configs/<device_type>_test_config.json.

Keys used in functional test configs:
    "volatile_tests": flaky tests to skip in presubmit for the given device type.
    "slow_tests": stable tests too slow to run in presubmit. Note that a test can be present in
        "slow" and "volatile" categories simutaneously.
    "do_not_run_tests": tests which should never run for that device type.

    All tests are specified as a list of full test names or test suite names. For example:
    ["CommonTestSuite.test_0001_factory_reset", "WifiConnectTestSuite"].
"""
import functools
import inspect
import json
import os
import shutil
import collections
import sys
import coverage
import yaml

from gazoo_device import manager
from gazoo_device.utility import reflection_utils
from mobly import suite_runner
from mobly import test_runner

import functional_tests
from functional_tests import common_test_suite
from functional_tests import gdm_test_base

# Class definition for a test suite: suite name + list of full test names
# Note that the tuple is actually mutable since 2nd argument is a list
SuiteTuple = collections.namedtuple("SuiteTuple", ["suite_name", "test_list"])

cov = coverage.Coverage(source=["gazoo_device"])
cov.start()

CUR_LOCATION = os.path.dirname(os.path.abspath(__file__))
USER_SETTINGS_FILE = os.path.join(CUR_LOCATION, "user_settings.json")
TESTBED_DIRECTORY = "/opt/gazoo/testbeds"

DO_NOT_RUN_KEY = "do_not_run_tests"
SLOW_KEY = "slow_tests"
VOLATILE_KEY = "volatile_tests"

RUN_TYPE_ALL = "all"  # Run all supported tests. Runs nightly.
RUN_TYPE_CUSTOM = "custom"  # Run only the specified tests.
RUN_TYPE_REGRESSION = "regression"  # Exclude flaky and long-running tests. Runs in presubmit.
RUN_TYPE_STABLE = "stable"  # Exclude flaky tests.
RUN_TYPE_VOLATILE = "volatile"  # Run only flaky tests.
RUN_TYPES = [RUN_TYPE_ALL, RUN_TYPE_CUSTOM, RUN_TYPE_REGRESSION, RUN_TYPE_STABLE, RUN_TYPE_ALL]
RUN_TYPE_CONFIG_KEY = "run_type"


def _get_possible_test_suites():
    """Returns a dict of all available regression test suites (which inherit from GDMTestBase)."""
    module_to_classes = reflection_utils.get_all_subclasses_in_package(
        parent_class=gdm_test_base.GDMTestBase, package=functional_tests,
        excluded_modules=[gdm_test_base])
    suite_classes = functools.reduce(set.union, module_to_classes.values(), set())
    return {suite.__name__: suite for suite in suite_classes}


def _load_config(device_type):
    """Returns dict of test_config given device_type name.

    Mapped to functional_test_configs/<device_type>_test_config.json).
    """

    file_name = "{}/functional_test_configs/{}_test_config.json".format(CUR_LOCATION, device_type)
    try:
        with open(file_name, "r") as open_file:
            config = json.load(open_file)
    except Exception as err:
        raise RuntimeError("Unable to load config {}. Bad format? Err: {}".format(file_name, err))

    return config


def _extract_testbed_device_info(config):
    """Extracts the device type and name from the first testbed and checks testbed validity.

    Args:
        config (str): path to the testbed config

    Raises:
        RuntimeError: the testbed doesn't have any devices or has more than 1 device in it.

    Returns:
        tuple: (testbed device type, testbed device name)
    """
    file_name = config
    with open(file_name) as open_file:
        file_content = yaml.load(open_file)
    controllers = file_content["TestBeds"][0]["Controllers"]

    devices = controllers.get("GazooDevice", [])
    if not devices:
        raise RuntimeError("No valid devices available in testbed in {}".format(file_name))
    if len(devices) > 2:
        raise RuntimeError("Please use a testbed with just one device. "
                           "{} devices in first testbed in {}".format(
                               len(devices), file_name))

    device_id = devices[0]
    if isinstance(device_id, dict):
        device_id = device_id["id"]
    manager_instance = manager.Manager()
    device_type = manager_instance.get_device_prop(device_id, "device_type")
    manager_instance.close()
    return device_type, device_id


def _validate_device_type(device_type):
    """Check that the device found in the testbed is supported by GDM."""
    device_types = manager.Manager.get_supported_device_types()
    if device_type not in device_types:
        raise RuntimeError("Device type {} not supported. Supported types: {}".format(
            device_type, device_types))


def _get_supported_test_suites(all_test_suites, device_type, device_name):
    """Find the test suites which are supported by the given device."""
    device_class = manager.Manager.get_supported_device_class(device_type)
    dynamic_test_suites = set()
    for suite_class in all_test_suites.values():
        if (suite_class.is_applicable_to(device_type, device_class, device_name)
                and not suite_class.requires_pairing()):
            # All devices on GDM regression servers are unpaired.
            dynamic_test_suites.add(suite_class)

    applicable_suite_names = "\n".join("\t{}".format(suite.__name__)
                                       for suite in dynamic_test_suites)
    inapplicable_suites = set(all_test_suites.values()) - dynamic_test_suites
    inapplicable_suite_names = "\n".join("\t{}".format(suite.__name__)
                                         for suite in inapplicable_suites)
    print("Test suites applicable to device {!r}:\n{}"
          .format(device_name, applicable_suite_names))
    print("Test suites not applicable to device {!r}:\n{}"
          .format(device_name, inapplicable_suite_names))

    test_suites = list(dynamic_test_suites)
    # Ensure CommonTestSuite runs first as it also upgrades the device to a specific firmware.
    if common_test_suite.CommonTestSuite in test_suites:
        common_test_suite_pos = test_suites.index(common_test_suite.CommonTestSuite)
        test_suites.insert(0, test_suites.pop(common_test_suite_pos))
    return test_suites


def _gather_all_regression_tests(regression_class_list):
    """Returns a list of all possible functional tests.

    Returns:
        list: list of SuiteTuple objects.

    Example return value:
        [(suite_name=SuiteName, test_list=[SuiteName.TestName1, SuiteName.TestName2, ...]), <...>]
    """
    regression_test_list = []
    for test_class in regression_class_list:
        class_name = test_class.__name__

        test_names = [attr for attr in dir(test_class) if attr.startswith(
            "test") and inspect.isroutine(getattr(test_class, attr))]

        full_test_names = ["{}.{}".format(class_name, name) for name in test_names]
        regression_test_list.append(SuiteTuple(class_name, full_test_names))
    return regression_test_list


def _find_suite_tuple(full_test_list, suite_name):
    """Return suite tuple with suite_name from the list if found, None otherwise."""
    for suite_tuple in full_test_list:
        if suite_tuple.suite_name == suite_name:
            return suite_tuple


def _load_test_category(config, full_test_list, key):
    """Loads the test category specified by the key from the test config."""
    test_list = [str(t) for t in config.get(key, [])]
    not_found_names = []
    valid_test_names = []
    for full_name in test_list:
        if "." in full_name:  # name is SuiteName.test_name
            class_name = full_name.split(".")[0]
            suite_tuple = _find_suite_tuple(full_test_list, class_name)
            is_test_valid = suite_tuple is not None and full_name in suite_tuple.test_list

            if is_test_valid:
                valid_test_names.append(full_name)
            else:
                not_found_names.append(full_name)

        else:  # its presumably SuiteName
            suite_tuple = _find_suite_tuple(full_test_list, full_name)
            if suite_tuple is not None:
                valid_test_names.extend(suite_tuple.test_list)
            else:
                not_found_names.append(full_name)

    if not_found_names:
        print("WARNING: Unable to find the following {} in the regression suite ".format(key))
        print("Check the spelling and ensure format is: 'CommonTest.test100' ", end=' ')
        print("(or 'CommonTestSuite' for a suite)")
        print(not_found_names)
    return valid_test_names


def _determine_run_type(tests_arg):
    if not tests_arg or tests_arg[0] == RUN_TYPE_REGRESSION:
        run_type = RUN_TYPE_REGRESSION
    elif tests_arg[0] == RUN_TYPE_VOLATILE:
        run_type = RUN_TYPE_VOLATILE
    elif tests_arg[0] == RUN_TYPE_ALL:
        run_type = RUN_TYPE_ALL
    elif tests_arg[0] == RUN_TYPE_STABLE:
        run_type = RUN_TYPE_STABLE
    else:
        run_type = RUN_TYPE_CUSTOM

    print("**** Single device {} test suite ****".format(run_type))
    return run_type


def _get_all_test_names(full_test_list):
    """Returns a combined list of all test names in all suites."""
    full_name_list = []
    for _, test_list in full_test_list:
        full_name_list.extend(test_list)
    return full_name_list


def _determine_tests_to_run(config, run_type, tests_arg, regression_class_list):
    """Tweaks the args to reflect the type of run.

    Args:
        config (dict): functional test config.
        run_type (str): regression run type. One of RUN_TYPES.
        tests_arg (list): list of test names to run.
        regression_class_list (list): list of supported functional test suites.

    Returns:
        list: list of test names to run.

    Note:
        '--tests regression' [DEFAULT] is all regression tests but those filtered out, slow,
                             or volatile
        '--tests stable' is all tests except for volatile and filtered out
        '--tests volatile' is volatile tests only (excludes filtered out tests)
        '--tests all' is all tests but those filtered out
        '--tests ANYTHING, ELSE' custom runs just the tests given

    Raises:
        ValueError: invalid regression run type provided.
    """
    # Accumulate all tests by full name: CommmonTestSuite.test100 if they are not filtered
    full_test_list = _gather_all_regression_tests(regression_class_list)
    # Get skiped tests, volatile tests and remove any mistyped tests
    do_not_run_tests = _load_test_category(config, full_test_list, DO_NOT_RUN_KEY)
    slow_tests = _load_test_category(config, full_test_list, SLOW_KEY)
    volatile_tests = _load_test_category(config, full_test_list, VOLATILE_KEY)
    regression_tests = _get_all_test_names(full_test_list)

    tests_to_run = []
    tests_to_skip = []
    if run_type == RUN_TYPE_REGRESSION:
        tests_to_skip = list(set(do_not_run_tests + volatile_tests + slow_tests))  # Deduplicate
        tests_to_run = [t for t in regression_tests if t not in tests_to_skip]
    elif run_type == RUN_TYPE_VOLATILE:
        tests_to_run = [t for t in volatile_tests if t not in do_not_run_tests]
        tests_to_skip = [t for t in regression_tests if t not in tests_to_run]
    elif run_type == RUN_TYPE_ALL:
        tests_to_skip = do_not_run_tests
        tests_to_run = [t for t in regression_tests if t not in tests_to_skip]
    elif run_type == RUN_TYPE_STABLE:
        tests_to_skip = list(set(do_not_run_tests + volatile_tests))  # Deduplicate
        tests_to_run = [t for t in regression_tests if t not in tests_to_skip]
    elif run_type == RUN_TYPE_CUSTOM:
        tests_to_run = tests_arg
    else:
        raise ValueError("Unknown run type {!r}. Valid run types: {}.".format(run_type, RUN_TYPES))

    print("Running {} tests: {}.".format(len(tests_to_run), tests_to_run))
    print("Skipping {} tests: {}.".format(len(tests_to_skip), tests_to_skip))
    return tests_to_run


def _construct_mobly_args(parsed_args, tests_to_run):
    """Reconstructs Mobly CLI args from parsed_args. Sets --tests arg to tests_to_run."""
    mobly_args = []
    for arg in ["config", "list_tests"]:
        value = getattr(parsed_args, arg, None)
        if value:
            mobly_args.extend(["--{}".format(arg), value])

    key = "list_tests"
    value = getattr(parsed_args, key, None)
    if value:
        mobly_args.append("--{}".format(key))

    mobly_args.append("--tests")
    mobly_args.extend(tests_to_run)
    return mobly_args


def _get_adjusted_cli_args():
    """Replaces '-t <testbed_name>' with '-c <path_to_testbed_config>.'"""
    adjusted_argv = sys.argv.copy()
    if "-t" in adjusted_argv:
        index = adjusted_argv.index("-t")
        adjusted_argv[index] = "-c"
        if index < len(adjusted_argv) - 1:
            adjusted_argv[index + 1] = os.path.join(TESTBED_DIRECTORY,
                                                    "{}.yml".format(adjusted_argv[index + 1]))
    return adjusted_argv


def _run_tests(supported_test_suites, tests_to_run, parsed_args):
    """Run the functional tests.

    Args:
        supported_test_suites (list): list of all test suite classes that can run on the device.
        tests_to_run (list): list of test names to run.
        parsed_args (Namespace): parsed CLI arguments.
    """
    if not tests_to_run:
        print("Nothing to run.")
        return

    suite_runner_args = _construct_mobly_args(parsed_args, tests_to_run)
    suite_runner.run_suite(supported_test_suites, argv=suite_runner_args)


def _save_coverage(destination):
    cov.stop()
    cov.save()
    if os.path.exists(".coverage"):
        shutil.move(".coverage", destination)


def _update_user_settings_file(key, value):
    with open(USER_SETTINGS_FILE, "r") as open_file:
        user_settings = json.load(open_file)
    user_settings[key] = value
    with open(USER_SETTINGS_FILE, "w") as open_file:
        json.dump(user_settings, open_file)


def main():
    adjusted_args = _get_adjusted_cli_args()
    parsed_args = test_runner.parse_mobly_cli_args(argv=adjusted_args)
    device_type, device_name = _extract_testbed_device_info(parsed_args.config)
    _validate_device_type(device_type)
    test_config = _load_config(device_type)

    run_type = _determine_run_type(parsed_args.tests)
    # Pass the run type into the test suite through user_settings.json file.
    _update_user_settings_file(RUN_TYPE_CONFIG_KEY, run_type)

    all_test_suites = _get_possible_test_suites()
    supported_test_suites = _get_supported_test_suites(all_test_suites, device_type, device_name)

    tests_to_run = _determine_tests_to_run(test_config, run_type, parsed_args.tests,
                                           supported_test_suites)
    _run_tests(supported_test_suites, tests_to_run, parsed_args)

    log_path = os.environ.get("MH_GEN_FILE_DIR", os.environ.get("MOBLY_LOGPATH", "artifacts"))
    coverage_destination = "{}/coverage.regression_test_suite.{}".format(log_path, device_type)
    _save_coverage(destination=coverage_destination)


if __name__ == "__main__":
    main()
