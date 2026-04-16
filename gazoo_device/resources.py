"""Functions for obtaining GDM's resources: filters, scripts, APKs, binaries."""
import os.path

_PACKAGE_PATH = os.path.dirname(os.path.abspath(__file__))


def extract(resource_path: str) -> str:
  """Returns the host path of an extracted resource.

  When running from a .par, forces extraction of the resource to a temporary
  directory. This should only be called at the time the resource is actually
  used to avoid unnecessary extractions (e. g. this shouldn't be called at
  import time to define module or class constants). See b/293211987#comment11.

  Args:
    resource_path: Resource path relative to the gazoo_device directory, e. g.
      "filters/adb/basic.json".
  """
  return os.path.join(_PACKAGE_PATH, resource_path)
