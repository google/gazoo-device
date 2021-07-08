# Copyright 2021 Google LLC
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

"""Library for standard gazoo inputs.
"""
import os
from typing import Any
from typing import Optional

from absl import flags
from gazoo_device.tests.functional_tests.utils import testbed_config_pb2
from google.protobuf import text_format

FLAGS = flags.FLAGS
FLAG_TB_CONFIG = "testbed_config"
TESTBED_CONFIG = flags.DEFINE_string(
    FLAG_TB_CONFIG,
    default=None,
    help="Path to the testbed config file",
    short_name="t")

_ENV_VAR_OUTPUT_DIR = "TEST_UNDECLARED_OUTPUTS_DIR"
_ENV_VAR_TB_CONFIG = "TESTBED_CONFIG_PATH"


def get_testbed_config() -> testbed_config_pb2.TestbedConfig:
  """Returns the testbed config loaded from the testbed textproto.

  In the lab environment, the testbed textproto information can be found
    by reading environment variable $TESTBED_CONFIG_PATH.
  For local runs, provide the path to the testbed config file in
    --testbed_config (-t) CLI flag. The value of the CLI flag takes precedence
    over the value of $TESTBED_CONFIG_PATH.

  Returns:
    TestbedConfig: Testbed config object.

  Raises:
    RuntimeError: if the testbed config file isn't specified;
                  if the testbed config isn't a valid file.
  """
  file_name = get_testbed_config_file()
  if not file_name:
    raise RuntimeError(
        f"Testbed config hasn't been specified. Provide the path to the "
        f"testbed config file via --{FLAG_TB_CONFIG} (-t) flag.")
  return load_testbed_config(file_name)


def load_testbed_config(file_name) -> testbed_config_pb2.TestbedConfig:
  """Returns the testbed config loaded from the file name."""
  with open(file_name) as open_file:
    return text_format.Parse(open_file.read(),
                             testbed_config_pb2.TestbedConfig())


def get_testbed_config_file() -> Any:
  """Returns the testbed config file name.

  In the lab environment, the testbed textproto information can be found
    by reading environment variable $TESTBED_CONFIG_PATH.
  For local runs, provide the path to the testbed config file in
    --testbed_config (-t) CLI flag. The value of the CLI flag takes precedence
    over the value of $TESTBED_CONFIG_PATH.

  Returns:
    Any: Testbed config filename or None
  """
  if TESTBED_CONFIG.value:
    return TESTBED_CONFIG.value
  return os.environ.get(_ENV_VAR_TB_CONFIG)


def get_output_dir_setting() -> Optional[str]:
  """Returns the name of the test output directory.

  Uses $TEST_UNDECLARED_OUTPUTS_DIR environment variable.

  Returns:
    str: path to the test output (artifact) directory if set.
    None: if the env variable is not set.
  """
  return os.environ.get(_ENV_VAR_OUTPUT_DIR)
