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

"""Test suite for devices using file transfer functions."""
import hashlib
import os

import subprocess
from mobly import asserts
from functional_tests import gdm_test_base


def file_sha256(src_file_path):
    """Calculate the SHA256 hash of the given file.

    Args:
      src_file_path: path to the file to be hashed

    Returns:
      SHA256 hash of the file in hex digest format
    """

    sha256sum = hashlib.sha256()
    with open(src_file_path, 'rb') as src_file:
        buf = src_file.read(65536)
        while buf:
            sha256sum.update(buf)
            buf = src_file.read(65536)
    return sha256sum.hexdigest()


class FileTransferTestSuite(gdm_test_base.GDMTestBase):
    """Tests send file and recv file from device."""

    @classmethod
    def is_applicable_to(cls, device_type, device_class, device_name):
        """Determine if this test suite can run on the given device."""
        return device_class.has_capabilities(["file_transfer"])

    @classmethod
    def requires_pairing(cls):
        """Returns True if the device in the testbed must be paired to run this test suite."""
        return False

    def test_5501_recv_file_from_device(self):
        device_dir = self._get_writable_directory()
        local_file_path = os.path.join(self.log_path, "recv_file_from_device.txt")
        catch_phrase = "The quick brown dog jumps over the lazy fox"
        self.device.shell(
            'echo "{}" >> {}/recv_file_from_device.txt'.format(catch_phrase, device_dir))
        device_path = "{}/recv_file_from_device.txt".format(device_dir)
        output = self.device.shell("cat " + device_path)
        asserts.assert_true(
            catch_phrase in output,
            "echo did not work. Unable to set up test. Output: {}".format(output))

        try:
            self.device.file_transfer.recv_file_from_device(device_path, self.log_path)
            asserts.assert_true(os.path.exists(local_file_path),
                                "Expected file {} to exist but it does not.".format(
                                    local_file_path))
            output = subprocess.check_output(["cat", local_file_path]).decode("utf-8")
            asserts.assert_true(catch_phrase in output,
                                "Expected catchphrase in transferred file, got: {}".format(
                                    output))

        finally:
            self.device.shell("rm " + device_path)
            if os.path.exists(local_file_path):
                os.remove(local_file_path)

    def test_5502_send_file_to_device(self):
        device_dir = self._get_writable_directory()

        local_file_path = os.path.join(self.log_path, "send_file_to_device.txt")
        catch_phrase = "The quick brown dog jumps over the lazy fox"
        with open(local_file_path, 'w') as open_file:
            open_file.write(catch_phrase + "\n")
        output = subprocess.check_output(["cat", local_file_path]).decode("utf-8")
        asserts.assert_true(
            catch_phrase in output,
            "writing to local file did not work. Unable to set up test. Output: {}".format(output))
        try:
            device_path = os.path.join(device_dir, "send_file_to_device.txt")
            self.device.file_transfer.send_file_to_device(local_file_path, device_dir)
            output = self.device.shell("cat " + device_path)
            asserts.assert_true(catch_phrase in output,
                                "Expected catchphrase in transferred file, got: {}".format(output))

        finally:
            self.device.shell("rm " + device_path)
            os.remove(local_file_path)

    def _get_writable_directory(self):
        possible_dirs = ["/tmp", "/data/misc"]
        for possible_dir in possible_dirs:

            output, return_code = self.device.shell(
                "ls -la {}".format(possible_dir), include_return_code=True)
            if return_code == 0 and "w" in output:
                return possible_dir
        self.asserts_fail("{} do not exist on device."
                          "Find an appropriate directory and add to list".format(possible_dirs))


if __name__ == "__main__":
    gdm_test_base.main()
