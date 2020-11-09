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

"""Digital Loggers Web Power Switch."""
import requests

from gazoo_device import decorators
from gazoo_device import gdm_logger
from gazoo_device.base_classes import auxiliary_device
from gazoo_device.utility import http_utils
from gazoo_device.utility import host_utils
from gazoo_device.switchboard import log_process
from gazoo_device.capabilities import switch_power_dli_powerswitch
from gazoo_device import detect_criteria

logger = gdm_logger.get_gdm_logger()

CLASS_NAME = "DliPowerSwitch"
AUTH = requests.auth.HTTPDigestAuth("admin", "1234")
HTTP_FRAMEWORK = "http://{ip}/restapi/"
GET_CONFIG = HTTP_FRAMEWORK + "config/="

HEADERS = {
    "GET_PROP": {"Accept": "application/json"},
    "SET_PROP": {"Accept": "application/json",
                 "X-CSRF": "x",
                 "X-HTTP-Method": "PUT"},
}

COMMANDS = {
    "FIRMWARE_VERSION": GET_CONFIG + "version/",
    "SERIAL_NUMBER": GET_CONFIG + "serial/",
    "DEVICE_MANUFACTURER": GET_CONFIG + "brand_company_name/",
    "DEVICE_NAME": GET_CONFIG + "brand_name/",
    "ADJUST_PORTS_MODE": HTTP_FRAMEWORK + "relay/outlets/{}/state/"
}

REGEXES = {
    "COMMAND_RESPONSE": ['[', '"', ']']
}


class DliPowerSwitch(auxiliary_device.AuxiliaryDevice):
    """Device class for a DLI Power Switch."""
    COMMUNICATION_TYPE = "SshComms"
    DETECT_MATCH_CRITERIA = {detect_criteria.SSH_QUERY.is_dli: True}
    DEVICE_TYPE = "powerswitch"
    _MODEL = "LPC9"
    _NUMBER_OF_PORTS = 8
    _VALID_RETURN_CODES = [200, 206, 207]

    def __init__(self,
                 manager,
                 device_config,
                 log_file_name=None,
                 log_directory=None):
        super().__init__(manager,
                         device_config,
                         log_file_name=log_file_name,
                         log_directory=log_directory)
        self._regexes.update(REGEXES)
        self._commands.update(COMMANDS)

    @decorators.PersistentProperty
    def ip_address(self):
        """Global IP address."""
        return self.communication_address

    @decorators.DynamicProperty
    def firmware_version(self):
        """Version of Power Switch.

        Returns:
            str: Power Switch firmware version.
        """
        return self.write_command("GET",
                                  self.commands["FIRMWARE_VERSION"].format(ip=self.ip_address),
                                  HEADERS["GET_PROP"])

    @decorators.CapabilityDecorator(switch_power_dli_powerswitch.SwitchPowerDliPowerswitch)
    def switch_power(self):
        """Returns a switch_power object to send commands.

        Returns:
            object: switch_power_dli_powerswitch
        """
        return self.lazy_init(
            switch_power_dli_powerswitch.SwitchPowerDliPowerswitch,
            http_fn=self.write_command,
            ip_address=self.ip_address,
            command_dict=self.commands,
            headers_dict=HEADERS,
            device_name=self.name,
            total_ports=self._NUMBER_OF_PORTS)

    @decorators.PersistentProperty
    def health_checks(self):
        """Returns list of methods to execute as health checks."""
        return [self.device_is_connected]

    @decorators.LogDecorator(logger)
    def get_detection_info(self):
        """Gets the persistent and optional attributes of a DLI Power Switch.

        Returns:
          tuple: (dict, dict) dictionary of persistent attributes,
                  dictionary of optional attributes.

        Notes:
            persistent: model, serial_number
        """
        self.props['optional'] = {}
        self.props["persistent_identifiers"]["model"] = self._MODEL
        self.props["persistent_identifiers"]["serial_number"] = self.write_command(
            "GET",
            self.commands["SERIAL_NUMBER"].format(ip=self.ip_address),
            headers=HEADERS["GET_PROP"])
        return self.props["persistent_identifiers"], self.props["optional"]

    @classmethod
    def is_connected(cls, device_config):
        """Checks whether or not the DLI Power Switch is connected.

        Args:
          device_config (dict): contains "persistent" dict

        Returns:
            bool: whether the device responds to a ping.
        """

        return host_utils.is_pingable(device_config["persistent"]["console_port_name"])

    @decorators.LogDecorator(logger)
    def reboot(self):
        """Issues a soft reboot command.

        Raises:
            NotImplementedError: not supported.
        """
        raise NotImplementedError("{}: reboot is not supported by {}."
                                  .format(self.name, self.DEVICE_TYPE))

    @decorators.LogDecorator(logger)
    def recover(self, error):
        """Attempts to recover device based on the type of error specified."""
        pass

    def write_command(self, method, url, headers, data=None, json_data=None):
        """Sends an HTTP request via specified method.

        Args:
            method (str): Method of HTTP request. Choices: "GET", "POST".
            url (str): HTTP formated command to send to the device.
            headers (dict): Headers required for the HTTP request.
            data (dict): Data that is needed for the HTTP POST Request
            json_data (dict): JSON data that is needed for the HTTP POST Request

        Raises:
            RuntimeError: if response.status_code returned by requests.get or requests.post is not
                          in valid_return_codes
            TypeError: if headers / json_data is not a dictionary or None.

        Returns:
            str: Formatted GET/POST HTTP response

        """
        log_message = "Sending command '{command}' to {device} via http {method} method.".format(
            command=url, device=self.name, method=method)
        self._log_to_file(log_message)
        try:
            if "GET" in method:
                response = http_utils.send_http_get(
                    url,
                    auth=AUTH,
                    headers=headers,
                    valid_return_codes=self._VALID_RETURN_CODES)
            else:
                response = http_utils.send_http_post(
                    url,
                    auth=AUTH,
                    headers=headers,
                    data=data,
                    json_data=json_data,
                    valid_return_codes=self._VALID_RETURN_CODES)

        except (RuntimeError, TypeError) as err:
            log_message = "Command '{command}' failed".format(command=url)
            self._log_to_file(log_message)
            raise err

        log_message = "Command '{command}' sent successfully. Return Code: {return_code}".format(
            command=url,
            return_code=response.status_code)
        self._log_to_file(log_message)
        return self._format_response(response)

    @classmethod
    def _format_response(cls, response):
        """Removes extraneous formatting from requests library response.text.

        Args:
            response (requests.Response): requests library response object
        Returns:
            str: returns a formatted string of response.text
        """
        return "".join(i for i in response.text if i not in REGEXES["COMMAND_RESPONSE"])

    def _log_to_file(self, log_message, port="M"):
        """Adds a log message for each command."""
        if not log_message.endswith('\n'):
            log_message += '\n'
        with open(self.log_file_name, 'a') as out_file:
            logline = log_process._add_log_header(log_message, port=port)
            out_file.write(logline)

    def _list_properties_dynamic_powerswitch(self):
        """Returns a set of dynamic properties.

        Returns:
            set: dynamic properties that can be queried during get-prop CLI/API operation.
        """
        return set(["firmware_version"])
