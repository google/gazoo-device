# GDM unit tests

### Prerequisites

Set up a virtual environment and install *gazoo-device* and *gazoo-device.tests*
in editable mode:

```shell
cd gazoo_device/tests/
python3 -m virtualenv test_env
source test_env/bin/activate
pip install -e ../../ ./
```

### Run tests

*   Run the full suite of GDM unit tests:

    ```
    python3 unit_test_suite.py
    ```

    (or, equivalently, `python3 -m gazoo_device.tests.unit_test_suite`.)

*   Exclude slow tests (switchboard tests):

    ```
    python3 unit_test_suite.py -s
    ```

*   Run a single test module:

    ```
    python3 unit_tests/some_module_test.py
    ```

