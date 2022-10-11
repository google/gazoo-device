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
"""Unit tests for gazoo_device.utility.http_utils.py."""

import datetime
import http.client
import http.server
import json
import os.path
import socket
import socketserver
import ssl
import tempfile
import threading
from unittest import mock
import urllib

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from gazoo_device.tests.unit_tests.utils import unit_test_case
from gazoo_device.utility import http_utils
import requests
import urllib3

SSL_VERSION = ssl.PROTOCOL_TLSv1_2


class FakeURLResponse:
  """Fake URL response."""

  def __init__(self, code=200, content=""):
    self.code = code
    self.content = content

  def getcode(self):
    return self.code

  def read(self):
    return self.content


class UnixStreamHttpServer(socketserver.ThreadingMixIn,
                           socketserver.UnixStreamServer):

  def get_request(self):
    newsocket, _ = self.socket.accept()
    return (newsocket, ["local", 0])


class SecureUnixStreamHttpServer(UnixStreamHttpServer):

  def __init__(self, *args):
    super().__init__(*args)
    certbytes, keybytes = self._generate_https_certificate_and_key()

    with tempfile.NamedTemporaryFile(delete=False) as certfile:
      certfile.write(certbytes)
      self.cert = certfile.name

    with tempfile.NamedTemporaryFile(delete=False) as keyfile:
      keyfile.write(keybytes)
      self.key = keyfile.name

    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain(certfile=self.cert, keyfile=self.key)
    context.verify_mode = ssl.CERT_NONE

    sslsocket = context.wrap_socket(self.socket, server_side=True)
    self.socket.close()
    self.socket = sslsocket

  def _generate_https_certificate_and_key(self):
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    subject = x509.Name([
        x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, u"localhost"),
    ])
    cert = x509.CertificateBuilder()
    cert = cert.subject_name(subject)
    cert = cert.issuer_name(subject)
    cert = cert.public_key(key.public_key())
    cert = cert.serial_number(x509.random_serial_number())
    cert = cert.not_valid_before(datetime.datetime.now())
    cert = cert.not_valid_after(datetime.datetime.now() +
                                datetime.timedelta(hours=1))
    cert = cert.add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=True)
    cert = cert.add_extension(
        x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
        critical=False)
    cert = cert.add_extension(
        x509.ExtendedKeyUsage([
            x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
        ]),
        critical=False)
    cert = cert.sign(key, hashes.SHA256())

    certbytes = cert.public_bytes(serialization.Encoding.PEM)
    keybytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption())
    return (certbytes, keybytes)


class HelloWorldHttpHandler(http.server.BaseHTTPRequestHandler):
  protocol_version = "HTTP/1.1"  # Overrides BaseHTTPRequestHandler to use 1.1
  RESPONSE = b"Hello world!"

  def do_GET(self):  # pylint: disable=invalid-name
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.send_header("Content-Length", str(len(self.RESPONSE)))
    self.end_headers()
    self.wfile.write(self.RESPONSE)
    return

  def do_POST(self):  # pylint: disable=invalid-name
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.send_header("Content-Length", str(len(self.RESPONSE)))
    self.end_headers()
    self.wfile.write(self.RESPONSE)
    return


class HTTPUtilsTests(unit_test_case.UnitTestCase):
  """Unit tests for gazoo_device.utility.http_utils.py."""

  @mock.patch.object(requests.Session, "get")
  def test_send_http_get(self, mock_requests_get):
    """Test sending an HTTP get request."""
    mock_requests_get.return_value = requests.Response()
    mock_requests_get.return_value.status_code = 200
    http_utils.send_http_get(
        url="http://sometesturl:1234/some/endpoint", headers=None)

    http_utils.send_http_get(
        url="http://sometesturl:1234/some/endpoint",
        headers=None,
        ssl_version=SSL_VERSION)

    mock_requests_get.reset_mock()

    mock_requests_get.return_value = requests.Response()
    mock_requests_get.return_value.status_code = 400
    mock_requests_get.return_value.reason = "400 Bad Request"
    with self.assertRaises(RuntimeError):
      http_utils.send_http_get(url="invalid_url")

    with self.assertRaises(TypeError):
      http_utils.send_http_get(
          url="http://sometesturl:1234/some/endpoint",
          headers="invalid_headers")

  @mock.patch.object(requests.Session, "get")
  @mock.patch.object(requests.Session, "post")
  def test_send_http_post(self, mock_requests_post, mock_requests_get):
    """Test sending an HTTP post request."""
    mock_requests_post.return_value = requests.Response()
    mock_requests_post.return_value.status_code = 200

    mock_requests_get.return_value = requests.Response()
    mock_requests_get.return_value.status_code = 200

    http_utils.send_http_post(
        url="http://sometesturl:1234/some/endpoint",
        headers={"Content-Type": "application/json"},
        json_data={"params": "now"})

    http_utils.send_http_post(
        url="http://sometesturl:1234/some/endpoint",
        headers={"Content-Type": "application/json"},
        json_data={"params": "now"},
        ssl_version=SSL_VERSION)

    mock_requests_post.reset_mock()

    mock_requests_post.return_value = requests.Response()
    mock_requests_post.return_value.status_code = 400
    mock_requests_post.return_value.reason = "400 Bad Request"
    with self.assertRaises(RuntimeError):
      http_utils.send_http_post(
          url="invalid_url",
          headers={"Content-Type": "application/json"},
          json_data={"params": "now"})

    with self.assertRaises(TypeError) as error:
      http_utils.send_http_post(
          url="http://sometesturl:1234/some/endpoint",
          headers="invalid_headers",
          json_data={})
    self.assertNotIn("Expecting a dict value in headers", str(error))

    with self.assertRaises(TypeError) as error:
      http_utils.send_http_post(
          url="http://sometesturl:1234/some/endpoint",
          headers={},
          json_data="invalid_headers")
    self.assertNotIn("Expecting a dict or list value in json_data", str(error))

  @mock.patch.object(
      urllib.request, "urlopen", return_value=FakeURLResponse(200))
  @mock.patch.object(
      urllib.request, "urlretrieve", return_value=("", "last-modified"))
  @mock.patch.object(os.path, "exists", return_value=True)
  def test_020_download_file(self, mock_exists, mock_url_retrieve,
                             mock_url_open):
    """Test download_file() succeeding."""
    http_utils.download_file("http://fake.com/file.txt", "fake_destination")
    mock_url_open.assert_called()
    mock_url_retrieve.assert_called()
    mock_exists.assert_called()

  @mock.patch.object(
      urllib.request, "urlopen", return_value=FakeURLResponse(200))
  @mock.patch.object(urllib.request, "urlretrieve", return_value=("", ""))
  def test_021_download_fails_with_empty_file(self, mock_url_retrieve,
                                              mock_url_open):
    """Test download_file() failing due to the file being empty."""
    with self.assertRaisesRegex(RuntimeError,
                                "Unable to download http://fake.com/file.txt"):
      http_utils.download_file("http://fake.com/file.txt", "fake.txt")
    # Ensure multiple attempts were made
    self.assertGreater(mock_url_retrieve.call_count, 2)
    mock_url_open.assert_called()

  @mock.patch.object(
      urllib.request, "urlopen", return_value=FakeURLResponse(200))
  @mock.patch.object(
      urllib.request,
      "urlretrieve",
      side_effect=RuntimeError("Something", "Fake"))
  def test_022_download_fails_with_error(self, mock_url_retrieve,
                                         mock_url_open):
    """Test download_file() failing with an error."""
    with self.assertRaisesRegex(RuntimeError,
                                "Unable to download http://fake.com/file.txt"):
      http_utils.download_file("http://fake.com/file.txt", "fake.txt")
    mock_url_retrieve.assert_called()
    mock_url_open.assert_called()

  @mock.patch.object(socket, "inet_pton", side_effect=["", socket.error("")])
  def test_024_valid_ipv4_address(self, mock_socket_inet_pton):
    """Test is_valid_ip_address() succeeding with an ipv4 address."""
    self.assertTrue(http_utils.is_valid_ip_address("123.123.123"))
    self.assertFalse(http_utils.is_valid_ip_address("123.123.124"))
    mock_socket_inet_pton.assert_called()

  @mock.patch.object(
      socket, "inet_pton", side_effect=["", "", socket.error("")])
  def test_025_valid_ipv6_address(self, mock_socket_inet_pton):
    """Test is_valid_ip_address() succeeding with an ipv6 address."""
    self.assertTrue(
        http_utils.is_valid_ip_address("fe80::123:1234:1234:123%en0", True))
    self.assertTrue(
        http_utils.is_valid_ip_address("1234:123:123:123:123:1234:1234:123",
                                       True))
    self.assertFalse(http_utils.is_valid_ip_address("123.123.124", True))
    mock_socket_inet_pton.assert_called()

  @mock.patch.object(requests.Session, "get")
  def test_026_verify_invalid_return_code_rasies_exception_get(
      self, mock_requests_get):
    """Test send_http_get() raising an exception for an invalid return code."""
    mock_requests_get.return_value = requests.Response()
    mock_requests_get.return_value.status_code = 400
    mock_requests_get.return_value.headers = None
    mock_requests_get.return_value.reason = "400 Bad Request"
    err = "HTTP GET to URL test_URL returned: 400 Bad Request"
    with self.assertRaisesRegex(RuntimeError, err):
      http_utils.send_http_get("test_URL")

  @mock.patch.object(requests.Session, "post")
  def test_026_verify_invalid_return_code_raises_exception_post(
      self, mock_requests_post):
    """Test send_http_post() raising an exception for an invalid return code."""
    mock_requests_post.return_value = requests.Response()
    mock_requests_post.return_value.status_code = 400
    mock_requests_post.return_value.reason = "400 Bad Request"
    err = ("HTTP POST to URL test_URL with headers {}, data None and json "
           "data {} returned: 400 Bad Request")
    with self.assertRaisesRegex(RuntimeError, err):
      http_utils.send_http_post("test_URL", headers=None, json_data=None)

  @mock.patch.object(requests.Session, "get")
  def test_029_send_http_get_params_serialized_json_data(
      self, mock_requests_get):
    """Test executing an http get request with params and serialized json data."""
    test_url = "https://www.google.com"
    test_params = {"key": ["List item 1"]}
    test_data = {"test": "serialize me"}
    mock_requests_get.return_value = requests.Response()
    mock_requests_get.return_value.status_code = 200

    http_utils.send_http_get(url=test_url, params=test_params, data=test_data)
    mock_requests_get.assert_called_once_with(
        test_url,
        auth=None,
        params=test_params,
        data=json.dumps(test_data),
        headers=None,
        timeout=10,
        verify=False)

  @mock.patch.object(requests.Session, "get")
  def test_030_send_http_get_params_string_data(self, mock_requests_get):
    """Test executing an http get request with params and string data."""
    test_url = "https://www.google.com"
    test_params = {"key": ["List item 1"]}
    test_data = "test"
    mock_requests_get.return_value = requests.Response()
    mock_requests_get.return_value.status_code = 200

    http_utils.send_http_get(url=test_url, params=test_params, data=test_data)
    mock_requests_get.assert_called_once_with(
        test_url,
        auth=None,
        params=test_params,
        data=test_data,
        headers=None,
        timeout=10,
        verify=False)

  def test_30_send_http_get_retries_on_error(self):
    """Verify send_http_get retries on HTTP errors if # of attempts has not been exceeded."""
    http_err = http.client.RemoteDisconnected(
        "Remote end closed connection without response")
    urllib3_err = urllib3.exceptions.ProtocolError("Connection aborted.",
                                                   http_err)
    requests_err = requests.exceptions.ConnectionError(
        urllib3_err, request=mock.MagicMock())
    good_resp = requests.Response()
    good_resp.status_code = 200
    good_resp.reason = "OK"
    with mock.patch.object(
        requests.Session, "get", side_effect=[requests_err, good_resp]):
      http_utils.send_http_get(
          url="http://sometesturl:1234/some/endpoint", tries=2)

    with mock.patch.object(
        requests.Session, "get", side_effect=[requests_err, good_resp]):
      with self.assertRaises(RuntimeError):
        http_utils.send_http_get(
            url="http://sometesturl:1234/some/endpoint", tries=1)

  def test_31_send_http_post_retries_on_error(self):
    """Verify send_http_post retries on HTTP errors if # of attempts has not been exceeded."""
    http_err = http.client.RemoteDisconnected(
        "Remote end closed connection without response")
    urllib3_err = urllib3.exceptions.ProtocolError("Connection aborted.",
                                                   http_err)
    requests_err = requests.exceptions.ConnectionError(
        urllib3_err, request=mock.MagicMock())
    good_resp = requests.Response()
    good_resp.status_code = 200
    good_resp.reason = "OK"
    with mock.patch.object(
        requests.Session, "post", side_effect=[requests_err, good_resp]):
      http_utils.send_http_post(
          url="http://sometesturl:1234/some/endpoint", tries=2)

    with mock.patch.object(
        requests.Session, "post", side_effect=[requests_err, good_resp]):
      with self.assertRaises(RuntimeError):
        http_utils.send_http_post(
            url="http://sometesturl:1234/some/endpoint", tries=1)

  def test_32_uds_https(self):
    with tempfile.TemporaryDirectory() as tempdir:
      sock_path = f"{tempdir}/https.socket"
      server = SecureUnixStreamHttpServer(sock_path, HelloWorldHttpHandler)
      thread = threading.Thread(target=server.serve_forever, daemon=True)
      thread.start()

      try:

        def get_session():
          return http_utils.unix_socket_http_session(sock_path)

        response = http_utils.send_http_get(
            url="udss://localhost/tests",
            session_factory=get_session,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, HelloWorldHttpHandler.RESPONSE.decode())

      finally:
        server.shutdown()
        thread.join()

  def test_33_uds_http(self):
    with tempfile.TemporaryDirectory() as tempdir:
      sock_path = f"{tempdir}/http.socket"
      server = UnixStreamHttpServer(sock_path, HelloWorldHttpHandler)
      thread = threading.Thread(target=server.serve_forever, daemon=True)
      thread.start()

      try:

        def get_session():
          return http_utils.unix_socket_http_session(sock_path)

        response = http_utils.send_http_get(
            url="uds://localhost/tests",
            session_factory=get_session,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, HelloWorldHttpHandler.RESPONSE.decode())
      finally:
        server.shutdown()
        thread.join()


if __name__ == "__main__":
  unit_test_case.main()
