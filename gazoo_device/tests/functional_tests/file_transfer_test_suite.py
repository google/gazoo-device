"""Test suite for devices using file transfer functions."""
import hashlib
import os
from typing import Type

from gazoo_device.tests.functional_tests.utils import gdm_test_base
import immutabledict
import retry

_COMMANDS = immutabledict.immutabledict({
    "IS_WRITABLE_DIRECTORY": "test -d {path} && test -w {path}",
    "REMOVE_FILE": "rm {path}",
})


def file_sha256(src_file_path: str) -> str:
  """Calculate the SHA256 hash of the given file.

  Args:
    src_file_path: Path to the file to be hashed.

  Returns:
    SHA256 hash of the file in hex digest format.
  """
  sha256sum = hashlib.sha256()
  with open(src_file_path, "rb") as src_file:
    buf = src_file.read(65536)
    while buf:
      sha256sum.update(buf)
      buf = src_file.read(65536)
  return sha256sum.hexdigest()


class FileTransferTestSuite(gdm_test_base.GDMTestBase):
  """Functional test suite for the file transfer capability."""

  @classmethod
  def is_applicable_to(cls, device_type: str,
                       device_class: Type[gdm_test_base.DeviceType],
                       device_name: str) -> bool:
    """Determine if this test suite can run on the given device."""
    return device_class.has_capabilities(["file_transfer"])

  @classmethod
  def requires_pairing(cls) -> bool:
    """Returns True if the device must be paired to run this test suite."""
    return False

  def setUp(self):
    """Creates a text source file for transfer to the device."""
    super().setUp()

    file_contents = "The quick brown dog jumps over the lazy fox\n"
    self.host_source_path = os.path.join(self.get_output_dir(),
                                         "file_transfer_source.txt")
    with open(self.host_source_path, "w") as open_file:
      open_file.write(file_contents)

  @retry.retry(tries=2, delay=10)
  def test_file_transfer(self):
    """Tests sending a file to the device and receiving it."""
    received_file_name = "file_transfer_received.txt"
    device_dir = self._get_writable_directory()
    device_path = os.path.join(device_dir, received_file_name)
    self.device.file_transfer.send_file_to_device(self.host_source_path,
                                                  device_path)
    host_received_path = os.path.join(self.get_output_dir(), received_file_name)
    try:
      self.device.file_transfer.recv_file_from_device(device_path,
                                                      host_received_path)
      self.assertTrue(
          os.path.exists(host_received_path),
          f"recv_file_from_device did not create {host_received_path}")
      with open(self.host_source_path) as source_file:
        with open(host_received_path) as received_file:
          self.assertEqual(source_file.read(), received_file.read(),
                           "Received file was not equal to the sent file")
    finally:
      self.device.shell(_COMMANDS["REMOVE_FILE"].format(path=device_path))

  def _get_writable_directory(self) -> str:
    """Returns a writable directory on the device."""
    possible_dirs = [
        "/tmp",
    ]
    for possible_dir in possible_dirs:
      _, return_code = self.device.shell(
          _COMMANDS["IS_WRITABLE_DIRECTORY"].format(path=possible_dir),
          include_return_code=True)
      if return_code == 0:
        return possible_dir
    self.fail("Failed to find a writable directory on the device. "
              f"Known possible directories {possible_dirs} did not work. "
              "Find an appropriate directory and add it to the list.")


if __name__ == "__main__":
  gdm_test_base.main()
