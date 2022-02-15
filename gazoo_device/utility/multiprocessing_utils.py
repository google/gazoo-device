# Copyright 2022 Google LLC
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

"""Utility module for using the multiprocessing library."""
import multiprocessing
import os

_MP_CONTEXT = multiprocessing.get_context("spawn")


def get_context() -> multiprocessing.context.BaseContext:
  """Returns a multiprocessing context (forkserver- or spawn-based)."""
  return _MP_CONTEXT


def configure_multiprocessing() -> None:
  """Configures multiprocessing. No-op in the open source version."""
