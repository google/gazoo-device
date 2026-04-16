"""Unit tests for version.py."""
from unittest import mock

from gazoo_device import version
from gazoo_device.tests.unit_tests.utils import unit_test_case


class VersionTests(unit_test_case.UnitTestCase):
  """Unit tests for version.py."""

  def test_get_version_pip(self):
    """Tests get_version() in .pip distribution."""
    self.assertEqual(version._get_version(), version._SEMANTIC_VERSION)


if __name__ == "__main__":
  unit_test_case.main()
