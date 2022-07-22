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

"""Utility module for HTTP GET and POST methods."""
import json
import os
import socket
from typing import Any, Dict, List, Optional, Union
import urllib

from gazoo_device import gdm_logger
import requests
from requests import adapters
from requests.auth import AuthBase
from urllib3 import poolmanager
import urllib3.exceptions

MAX_URL_RETRY = 3

logger = gdm_logger.get_logger()


class SSLAdapter(adapters.HTTPAdapter):
  """An HTTPS Transport Adapter that uses an arbitrary SSL version."""

  def __init__(self, ssl_version: Optional[int] = None, **kwargs: Any):
    self.ssl_version = ssl_version

    super(SSLAdapter, self).__init__(**kwargs)

  def init_poolmanager(self,
                       connections: int,
                       maxsize: int,
                       block: bool = False) -> None:
    self.poolmanager = poolmanager.PoolManager(
        num_pools=connections,
        maxsize=maxsize,
        block=block,
        ssl_version=self.ssl_version)


def download_file(url: str, local_path: str) -> None:
  """Downloads the file to the local path.

  Args:
      url: URL to file.
      local_path: location to download file to.

  Raises:
      RuntimeError: if unable to access domain or to download file in 3 tries.
  """
  for _ in range(MAX_URL_RETRY):
    try:
      validate_url_access(url)
      (_, header) = urllib.request.urlretrieve(url, local_path)
    except Exception as err:
      raise RuntimeError("Unable to download {}".format(url)) from err
    if "last-modified" in header and os.path.exists(local_path):
      logger.info("Successfully downloaded file to {}".format(local_path))
      return
  raise RuntimeError("Unable to download {} after {} tries.".format(
      url, MAX_URL_RETRY))


def read_raw_html_page(url: str) -> str:
  """Returns the raw text on the HTML page.

  Args:
      url: URL for page.

  Returns:
      str: raw text on the HTML page.

  Raises:
      RuntimeError: if unable to access domain or to download file in 3 tries.
  """
  code = 0
  for _ in range(MAX_URL_RETRY):
    try:
      validate_url_access(url)
      response = urllib.request.urlopen(url)
      code = response.getcode()
      raw_page = response.read().decode("utf-8")
      if code == 200:
        # get all relative links to files
        return raw_page
      else:
        err = raw_page
    except urllib.error.HTTPError as err:
      code = err.code  # retry
      raw_page = err
  raise RuntimeError(
      "Unable to get files at URL {}. HTTP return code {}: {}".format(
          url, code, raw_page))


def send_http_get(url: str,
                  auth: Optional[AuthBase] = None,
                  params: Optional[Dict[Any, Any]] = None,
                  data: Optional[Any] = None,
                  headers: Optional[Dict[Any, Any]] = None,
                  ssl_version: Optional[int] = None,
                  valid_return_codes: Optional[List[int]] = None,
                  timeout: int = 10,
                  tries: int = 1) -> requests.Response:
  """Issues a HTTP GET and returns the response if the request is successful.

  Args:
      url: HTTP URL to which HTTP GET request needs to be sent
      auth: HTTP authentication object (i.e. HTTPDigestAuth)
      params: Parameters to send as a query string.
      data: Data for this HTTP GET Request
      headers: Headers for this HTTP GET Request
      ssl_version: SSL version to be used for secure http (https) requests. For
          example, ssl.PROTOCOL_TLSv1_2.
      valid_return_codes: List of valid HTTP return codes.
      timeout: request timeout in seconds
      tries: how many times to try sending the request.

  Raises:
      RuntimeError: if response.status_code returned by requests.get() is not in
          valid_return_codes
      TypeError: if headers is not a dictionary
      RequestException, HTTPError: raised if request fails and are converted
          into a RuntimeError.

  Returns:
      requests.Response: Response returned by requests.get
  """
  valid_return_codes = valid_return_codes or [200]

  if headers and not isinstance(headers, dict):
    raise TypeError(
        "Expecting a dict value in headers param but received: {}".format(
            type(headers)))
  try:
    with requests.Session() as session:
      if ssl_version:
        session.mount("https://", SSLAdapter(ssl_version))
      if data and isinstance(data, dict):
        data = json.dumps(data)

      for attempt in range(tries):
        try:
          response = session.get(
              url,
              auth=auth,
              params=params,
              data=data,
              headers=headers,
              timeout=timeout,
              verify=False)
          break
        except (requests.exceptions.RequestException,
                urllib3.exceptions.HTTPError) as err:
          if attempt < tries - 1:
            logger.debug(
                "HTTP GET to URL {} with data {} failed. Retrying. Error: {!r}"
                .format(url, data, err))
          else:
            raise

  except Exception as err:
    raise RuntimeError(
        "HTTP GET to URL {} with data {} failed".format(url, data)) from err

  if response.status_code not in valid_return_codes:
    raise RuntimeError("HTTP GET to URL {} returned: {}".format(
        url, response.reason))

  return response


def send_http_post(url: str,
                   auth: Optional[AuthBase] = None,
                   data: Optional[Any] = None,
                   params: Optional[Dict[Any, Any]] = None,
                   headers: Optional[Dict[Any, Any]] = None,
                   json_data: Optional[Union[Dict[Any, Any], List[Any]]] = None,
                   ssl_version: Optional[int] = None,
                   valid_return_codes: Optional[List[int]] = None,
                   timeout: int = 10,
                   tries: int = 1) -> requests.Response:
  """Issues a HTTP POST and returns the response if the request is successful.

  Args:
      url: HTTP URL to which HTTP POST request needs to be sent
      auth: HTTP authentication object (i.e. HTTPDigestAuth)
      data: Data for this HTTP POST Request
      params: Parameters for this HTTP POST Request
      headers: Headers for this HTTP POST Request
      json_data: JSON data for this HTTP POST Request
      ssl_version: SSL version to be used for secure http (https) requests. For
          example, ssl.PROTOCOL_TLSv1_2
      valid_return_codes: List of valid HTTP return codes.
      timeout: request timeout in seconds
      tries: how many times to try sending the request.

  Raises:
      RuntimeError: if response.status_code returned by requests.post() is not
          in valid_return_codes
      TypeError: if headers / json_data is not a dictionary or None.
      RequestException, HTTPError: raised if request fails and are converted
          into a RuntimeError.

  Returns:
      requests.Response: Response returned by requests.post
  """
  headers = headers or {}
  json_data = json_data or {}
  valid_return_codes = valid_return_codes or [200]

  if not isinstance(json_data, (dict, list)):
    raise TypeError(
        "Expecting a dict or list value in json_data params but received: "
        "{}.".format(type(json_data)))

  if not isinstance(headers, dict):
    raise TypeError(
        "Expecting a dict value in headers params but received: "
        "{}.".format(type(headers)))

  try:
    with requests.Session() as session:
      if ssl_version:
        session.mount("https://", SSLAdapter(ssl_version))

      for attempt in range(tries):
        try:
          response = session.post(
              url,
              auth=auth,
              data=data,
              json=json_data,
              headers=headers,
              timeout=timeout,
              params=params,
              verify=False)
          break
        except (requests.exceptions.RequestException,
                urllib3.exceptions.HTTPError) as err:
          if attempt < tries - 1:
            logger.debug(
                "HTTP POST to URL {} with headers {}, data {} and json data {} "
                "failed. Retrying. Error: {!r}".format(url, headers, data,
                                                       json_data, err))
          else:
            raise

  except Exception as err:
    raise RuntimeError(
        "HTTP POST to URL {} with headers {}, data {} and json data {} failed"
        .format(url, headers, data, json_data)) from err

  if response.status_code not in valid_return_codes:
    raise RuntimeError(
        "HTTP POST to URL {} with headers {}, data {} and json data {} "
        "returned: {}".format(url, headers, data, json_data, response.reason))

  return response


def is_valid_ip_address(address: str, is_ipv6: bool = False) -> bool:
  """Checks if valid IP address.

  Args:
      address: IP address
      is_ipv6: if IP address is IPv6

  Returns:
      bool: True if valid IP else False
  """
  address_family = socket.AF_INET6 if is_ipv6 else socket.AF_INET
  if is_ipv6 and "%" in address:  # Check for link local Ipv6 address
    # Example: fe80::123:1234:1234:123%en0
    address = address.split("%")[0]
  try:
    socket.inet_pton(address_family, address)
  except socket.error:  # not a valid address
    return False
  return True


def validate_url_access(url: str) -> None:
  """Validates URL access.

  Args:
      url: URL to access.

  Raises:
      RuntimeError: if unable to access domain of URL.
  """
  parsed_uri = urllib.parse.urlparse(url)
  prefix = "{uri.scheme}://{uri.netloc}/".format(uri=parsed_uri)
  response_code = urllib.request.urlopen(prefix).getcode()
  if response_code != 200:
    raise RuntimeError("Unable to reach domain {}. Returned code {}".format(
        prefix, response_code))
