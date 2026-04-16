# Copyright 2024 Google LLC
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
"""Device controllers and capabilities built into GDM."""
from typing import Any

from gazoo_device import version
from gazoo_device.auxiliary_devices import cambrionix
from gazoo_device.auxiliary_devices import chip_tool
from gazoo_device.auxiliary_devices import dc2200
from gazoo_device.auxiliary_devices import dli_powerswitch
from gazoo_device.auxiliary_devices import dlink_switch
from gazoo_device.auxiliary_devices import efr32
from gazoo_device.auxiliary_devices import esp32
from gazoo_device.auxiliary_devices import m5stick
from gazoo_device.auxiliary_devices import nrf52840
from gazoo_device.auxiliary_devices import nrf_openthread
from gazoo_device.auxiliary_devices import raspberry_pi
from gazoo_device.auxiliary_devices import raspberry_pi_matter_controller
from gazoo_device.auxiliary_devices import unifi_poe_switch
from gazoo_device.auxiliary_devices import yepkit
from gazoo_device.capabilities import bluetooth_service_linux
from gazoo_device.capabilities import comm_power_default
from gazoo_device.capabilities import device_power_default
from gazoo_device.capabilities import embedded_script_dli_powerswitch
from gazoo_device.capabilities import event_parser_default
from gazoo_device.capabilities import fastboot_default
from gazoo_device.capabilities import file_transfer_adb
from gazoo_device.capabilities import file_transfer_scp
from gazoo_device.capabilities import flash_build_commander
from gazoo_device.capabilities import flash_build_esptool
from gazoo_device.capabilities import flash_build_nrfjprog
from gazoo_device.capabilities import led_driver_default
from gazoo_device.capabilities import matter_controller_chip_tool
from gazoo_device.capabilities import matter_endpoints_accessor_chip_tool
from gazoo_device.capabilities import matter_endpoints_accessor_pw_rpc
from gazoo_device.capabilities import matter_sample_app_shell
from gazoo_device.capabilities import package_management_android
from gazoo_device.capabilities import pwrpc_button_default
from gazoo_device.capabilities import pwrpc_common_default
from gazoo_device.capabilities import pwrpc_event_subscription_default
from gazoo_device.capabilities import pwrpc_wifi_default
from gazoo_device.capabilities import shell_ssh
from gazoo_device.capabilities import switch_power_dli_powerswitch
from gazoo_device.capabilities import switch_power_snmp
from gazoo_device.capabilities import switch_power_unifi_switch
from gazoo_device.capabilities import switch_power_usb_default
from gazoo_device.capabilities import switch_power_usb_with_charge
from gazoo_device.capabilities import usb_hub_default
from gazoo_device.capabilities import wpan_nrf_ot
from gazoo_device.capabilities.interfaces import bluetooth_service_base
from gazoo_device.capabilities.interfaces import comm_power_base
from gazoo_device.capabilities.interfaces import device_power_base
from gazoo_device.capabilities.interfaces import embedded_script_base
from gazoo_device.capabilities.interfaces import event_parser_base
from gazoo_device.capabilities.interfaces import fastboot_base
from gazoo_device.capabilities.interfaces import file_transfer_base
from gazoo_device.capabilities.interfaces import flash_build_base
from gazoo_device.capabilities.interfaces import led_driver_base
from gazoo_device.capabilities.interfaces import matter_controller_base
from gazoo_device.capabilities.interfaces import matter_endpoints_base
from gazoo_device.capabilities.interfaces import matter_sample_app_base
from gazoo_device.capabilities.interfaces import package_management_base
from gazoo_device.capabilities.interfaces import pwrpc_button_base
from gazoo_device.capabilities.interfaces import pwrpc_common_base
from gazoo_device.capabilities.interfaces import pwrpc_event_subscription_base
from gazoo_device.capabilities.interfaces import pwrpc_wifi_base
from gazoo_device.capabilities.interfaces import shell_base
from gazoo_device.capabilities.interfaces import switch_power_base
from gazoo_device.capabilities.interfaces import switchboard_base
from gazoo_device.capabilities.interfaces import usb_hub_base
from gazoo_device.capabilities.interfaces import wpan_base
from gazoo_device.capabilities.matter_clusters import basic_information_chip_tool
from gazoo_device.capabilities.matter_clusters import basic_information_pw_rpc
from gazoo_device.capabilities.matter_clusters import boolean_state_pw_rpc
from gazoo_device.capabilities.matter_clusters import color_control_pw_rpc
from gazoo_device.capabilities.matter_clusters import door_lock_chip_tool
from gazoo_device.capabilities.matter_clusters import door_lock_pw_rpc
from gazoo_device.capabilities.matter_clusters import fan_control_pw_rpc
from gazoo_device.capabilities.matter_clusters import flow_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import flow_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import illuminance_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import illuminance_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import level_control_chip_tool
from gazoo_device.capabilities.matter_clusters import level_control_pw_rpc
from gazoo_device.capabilities.matter_clusters import occupancy_sensing_chip_tool
from gazoo_device.capabilities.matter_clusters import occupancy_sensing_pw_rpc
from gazoo_device.capabilities.matter_clusters import on_off_chip_tool
from gazoo_device.capabilities.matter_clusters import on_off_pw_rpc
from gazoo_device.capabilities.matter_clusters import pressure_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import pressure_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import relative_humidity_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import relative_humidity_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import switch_chip_tool
from gazoo_device.capabilities.matter_clusters import switch_pw_rpc
from gazoo_device.capabilities.matter_clusters import temperature_measurement_chip_tool
from gazoo_device.capabilities.matter_clusters import temperature_measurement_pw_rpc
from gazoo_device.capabilities.matter_clusters import thermostat_chip_tool
from gazoo_device.capabilities.matter_clusters import thermostat_pw_rpc
from gazoo_device.capabilities.matter_clusters import window_covering_pw_rpc
from gazoo_device.capabilities.matter_clusters.interfaces import basic_information_base
from gazoo_device.capabilities.matter_clusters.interfaces import boolean_state_base
from gazoo_device.capabilities.matter_clusters.interfaces import color_control_base
from gazoo_device.capabilities.matter_clusters.interfaces import door_lock_base
from gazoo_device.capabilities.matter_clusters.interfaces import fan_control_base
from gazoo_device.capabilities.matter_clusters.interfaces import level_control_base
from gazoo_device.capabilities.matter_clusters.interfaces import measurement_base
from gazoo_device.capabilities.matter_clusters.interfaces import occupancy_sensing_base
from gazoo_device.capabilities.matter_clusters.interfaces import on_off_base
from gazoo_device.capabilities.matter_clusters.interfaces import switch_base
from gazoo_device.capabilities.matter_clusters.interfaces import thermostat_base
from gazoo_device.capabilities.matter_clusters.interfaces import window_covering_base
from gazoo_device.capabilities.matter_endpoints import air_quality_sensor
from gazoo_device.capabilities.matter_endpoints import color_temperature_light
from gazoo_device.capabilities.matter_endpoints import contact_sensor
from gazoo_device.capabilities.matter_endpoints import dimmable_light
from gazoo_device.capabilities.matter_endpoints import door_lock
from gazoo_device.capabilities.matter_endpoints import extended_color_light
from gazoo_device.capabilities.matter_endpoints import fan
from gazoo_device.capabilities.matter_endpoints import flow_sensor
from gazoo_device.capabilities.matter_endpoints import heating_cooling_unit
from gazoo_device.capabilities.matter_endpoints import humidity_sensor
from gazoo_device.capabilities.matter_endpoints import light_sensor
from gazoo_device.capabilities.matter_endpoints import occupancy_sensor
from gazoo_device.capabilities.matter_endpoints import on_off_light
from gazoo_device.capabilities.matter_endpoints import on_off_light_switch
from gazoo_device.capabilities.matter_endpoints import on_off_plugin_unit
from gazoo_device.capabilities.matter_endpoints import pressure_sensor
from gazoo_device.capabilities.matter_endpoints import root_node
from gazoo_device.capabilities.matter_endpoints import speaker
from gazoo_device.capabilities.matter_endpoints import temperature_sensor
from gazoo_device.capabilities.matter_endpoints import thermostat
from gazoo_device.capabilities.matter_endpoints import unsupported_endpoint
from gazoo_device.capabilities.matter_endpoints import window_covering
from gazoo_device.capabilities.matter_endpoints.interfaces import air_quality_sensor_base
from gazoo_device.capabilities.matter_endpoints.interfaces import color_temperature_light_base
from gazoo_device.capabilities.matter_endpoints.interfaces import contact_sensor_base
from gazoo_device.capabilities.matter_endpoints.interfaces import dimmable_light_base
from gazoo_device.capabilities.matter_endpoints.interfaces import door_lock_base as door_lock_endpoint_base
from gazoo_device.capabilities.matter_endpoints.interfaces import endpoint_base
from gazoo_device.capabilities.matter_endpoints.interfaces import extended_color_light_base
from gazoo_device.capabilities.matter_endpoints.interfaces import fan_base
from gazoo_device.capabilities.matter_endpoints.interfaces import flow_sensor_base
from gazoo_device.capabilities.matter_endpoints.interfaces import heating_cooling_unit_base
from gazoo_device.capabilities.matter_endpoints.interfaces import humidity_sensor_base
from gazoo_device.capabilities.matter_endpoints.interfaces import light_sensor_base
from gazoo_device.capabilities.matter_endpoints.interfaces import occupancy_sensor_base
from gazoo_device.capabilities.matter_endpoints.interfaces import on_off_light_base
from gazoo_device.capabilities.matter_endpoints.interfaces import on_off_light_switch_base
from gazoo_device.capabilities.matter_endpoints.interfaces import on_off_plugin_unit_base
from gazoo_device.capabilities.matter_endpoints.interfaces import pressure_sensor_base
from gazoo_device.capabilities.matter_endpoints.interfaces import root_node_base
from gazoo_device.capabilities.matter_endpoints.interfaces import speaker_base
from gazoo_device.capabilities.matter_endpoints.interfaces import temperature_sensor_base
from gazoo_device.capabilities.matter_endpoints.interfaces import thermostat_base as thermostat_endpoint_base
from gazoo_device.capabilities.matter_endpoints.interfaces import unsupported_endpoint_base
from gazoo_device.capabilities.matter_endpoints.interfaces import window_covering_base as window_covering_endpoint_base
from gazoo_device.detect_criteria import adb_detect_criteria
from gazoo_device.detect_criteria import generic_detect_criteria
from gazoo_device.detect_criteria import host_shell_detect_criteria
from gazoo_device.detect_criteria import pigweed_detect_criteria
from gazoo_device.detect_criteria import serial_detect_criteria
from gazoo_device.detect_criteria import snmp_detect_criteria
from gazoo_device.detect_criteria import ssh_detect_criteria
from gazoo_device.detect_criteria import usb_detect_criteria
from gazoo_device.keys import raspberry_pi_key
from gazoo_device.keys import unifi_poe_switch_key
from gazoo_device.primary_devices import efr32_matter
from gazoo_device.primary_devices import esp32_matter
from gazoo_device.primary_devices import nrf_matter
from gazoo_device.primary_devices import raspberry_pi_matter
from gazoo_device.switchboard import switchboard
from gazoo_device.switchboard.communication_types import adb_comms
from gazoo_device.switchboard.communication_types import host_shell_comms
from gazoo_device.switchboard.communication_types import jlink_serial_comms
from gazoo_device.switchboard.communication_types import pigweed_serial_comms
from gazoo_device.switchboard.communication_types import pigweed_socket_comms
from gazoo_device.switchboard.communication_types import pty_process_comms
from gazoo_device.switchboard.communication_types import serial_comms
from gazoo_device.switchboard.communication_types import snmp_comms
from gazoo_device.switchboard.communication_types import ssh_comms
from gazoo_device.switchboard.communication_types import usb_comms
from gazoo_device.switchboard.communication_types import yepkit_comms
from gazoo_device.utility import key_utils
import immutabledict


__version__ = version.VERSION
download_key = key_utils.download_key


def export_extensions() -> dict[str, Any]:
  """Exports built-in device controllers, capabilities, communication types."""
  return {
      "primary_devices": [
          efr32_matter.Efr32Matter,
          esp32_matter.Esp32Matter,
          nrf_matter.NrfMatter,
          raspberry_pi_matter.RaspberryPiMatter,
      ],
      "auxiliary_devices": [
          cambrionix.Cambrionix,
          chip_tool.ChipTool,
          dc2200.DC2200,
          dli_powerswitch.DliPowerSwitch,
          dlink_switch.DLinkSwitch,
          efr32.EFR32,
          esp32.ESP32,
          m5stick.M5Stick,
          nrf52840.NRF52840,
          nrf_openthread.NrfOpenThread,
          raspberry_pi.RaspberryPi,
          raspberry_pi_matter_controller.RaspberryPiMatterController,
          unifi_poe_switch.UnifiPoeSwitch,
          yepkit.Yepkit,
      ],
      "virtual_devices": [],
      "communication_types": [
          adb_comms.AdbComms,
          host_shell_comms.HostShellComms,
          jlink_serial_comms.JlinkSerialComms,
          pigweed_serial_comms.PigweedSerialComms,
          pigweed_socket_comms.PigweedSocketComms,
          pty_process_comms.PtyProcessComms,
          serial_comms.SerialComms,
          snmp_comms.SnmpComms,
          ssh_comms.SshComms,
          usb_comms.UsbComms,
          yepkit_comms.YepkitComms,
      ],
      "detect_criteria": immutabledict.immutabledict({
          "AdbComms": adb_detect_criteria.ADB_QUERY_DICT,
          "HostShellComms": host_shell_detect_criteria.HOST_SHELL_QUERY_DICT,
          "JlinkSerialComms": serial_detect_criteria.SERIAL_QUERY_DICT,
          "PigweedSerialComms": pigweed_detect_criteria.PIGWEED_QUERY_DICT,
          "PigweedSocketComms": ssh_detect_criteria.SSH_QUERY_DICT,
          "PtyProcessComms": immutabledict.immutabledict(),
          "SerialComms": serial_detect_criteria.SERIAL_QUERY_DICT,
          "SnmpComms": snmp_detect_criteria.SNMP_QUERY_DICT,
          "SshComms": ssh_detect_criteria.SSH_QUERY_DICT,
          "UsbComms": usb_detect_criteria.USB_QUERY_DICT,
          "YepkitComms": generic_detect_criteria.GENERIC_QUERY_DICT,
      }),
      "capability_interfaces": [
          air_quality_sensor_base.AirQualitySensorBase,
          basic_information_base.BasicInformationClusterBase,
          bluetooth_service_base.BluetoothServiceBase,
          boolean_state_base.BooleanStateClusterBase,
          color_control_base.ColorControlClusterBase,
          color_temperature_light_base.ColorTemperatureLightBase,
          comm_power_base.CommPowerBase,
          contact_sensor_base.ContactSensorBase,
          device_power_base.DevicePowerBase,
          dimmable_light_base.DimmableLightBase,
          door_lock_base.DoorLockClusterBase,
          door_lock_endpoint_base.DoorLockBase,
          embedded_script_base.EmbeddedScriptBase,
          endpoint_base.EndpointBase,
          event_parser_base.EventParserBase,
          extended_color_light_base.ExtendedColorLightBase,
          fan_base.FanBase,
          fan_control_base.FanControlClusterBase,
          fastboot_base.FastbootBase,
          file_transfer_base.FileTransferBase,
          flash_build_base.FlashBuildBase,
          flow_sensor_base.FlowSensorBase,
          heating_cooling_unit_base.HeatingCoolingUnitBase,
          humidity_sensor_base.HumiditySensorBase,
          led_driver_base.LedDriverBase,
          level_control_base.LevelControlClusterBase,
          light_sensor_base.LightSensorBase,
          matter_controller_base.MatterControllerBase,
          matter_endpoints_base.MatterEndpointsBase,
          matter_sample_app_base.MatterSampleAppBase,
          measurement_base.MeasurementClusterBase,
          occupancy_sensing_base.OccupancySensingClusterBase,
          occupancy_sensor_base.OccupancySensorBase,
          on_off_base.OnOffClusterBase,
          on_off_light_base.OnOffLightBase,
          on_off_light_switch_base.OnOffLightSwitchBase,
          on_off_plugin_unit_base.OnOffPluginUnitBase,
          package_management_base.PackageManagementBase,
          pressure_sensor_base.PressureSensorBase,
          pwrpc_button_base.PwRPCButtonBase,
          pwrpc_common_base.PwRPCCommonBase,
          pwrpc_event_subscription_base.PwRpcEventSubscriptionBase,
          pwrpc_wifi_base.PwRPCWifiBase,
          root_node_base.RootNodeBase,
          shell_base.ShellBase,
          speaker_base.SpeakerBase,
          switch_base.SwitchClusterBase,
          switch_power_base.SwitchPowerBase,
          switchboard_base.SwitchboardBase,
          temperature_sensor_base.TemperatureSensorBase,
          thermostat_base.ThermostatClusterBase,
          thermostat_endpoint_base.ThermostatBase,
          unsupported_endpoint_base.UnsupportedBase,
          usb_hub_base.UsbHubBase,
          window_covering_base.WindowCoveringClusterBase,
          window_covering_endpoint_base.WindowCoveringBase,
          wpan_base.WpanBase,
      ],
      "capability_flavors": [
          air_quality_sensor.AirQualitySensorEndpoint,
          basic_information_chip_tool.BasicInformationClusterChipTool,
          basic_information_pw_rpc.BasicInformationClusterPwRpc,
          bluetooth_service_linux.BluetoothServiceLinux,
          boolean_state_pw_rpc.BooleanStateClusterPwRpc,
          color_control_pw_rpc.ColorControlClusterPwRpc,
          color_temperature_light.ColorTemperatureLightEndpoint,
          comm_power_default.CommPowerDefault,
          contact_sensor.ContactSensorEndpoint,
          device_power_default.DevicePowerDefault,
          dimmable_light.DimmableLightEndpoint,
          door_lock.DoorLockEndpoint,
          door_lock_chip_tool.DoorLockClusterChipTool,
          door_lock_pw_rpc.DoorLockClusterPwRpc,
          embedded_script_dli_powerswitch.EmbeddedScriptDliPowerswitch,
          event_parser_default.EventParserDefault,
          extended_color_light.ExtendedColorLightEndpoint,
          fan.FanEndpoint,
          fan_control_pw_rpc.FanControlClusterPwRpc,
          fastboot_default.FastbootDefault,
          file_transfer_adb.FileTransferAdb,
          file_transfer_scp.FileTransferScp,
          flash_build_commander.FlashBuildCommander,
          flash_build_esptool.FlashBuildEsptool,
          flash_build_nrfjprog.FlashBuildNrfjprog,
          flow_measurement_chip_tool.FlowMeasurementClusterChipTool,
          flow_measurement_pw_rpc.FlowMeasurementClusterPwRpc,
          flow_sensor.FlowSensorEndpoint,
          heating_cooling_unit.HeatingCoolingUnitEndpoint,
          humidity_sensor.HumiditySensorEndpoint,
          illuminance_measurement_chip_tool.IlluminanceMeasurementClusterChipTool,
          illuminance_measurement_pw_rpc.IlluminanceMeasurementClusterPwRpc,
          led_driver_default.LedDriverDefault,
          level_control_chip_tool.LevelControlClusterChipTool,
          level_control_pw_rpc.LevelControlClusterPwRpc,
          light_sensor.LightSensorEndpoint,
          matter_controller_chip_tool.MatterControllerChipTool,
          matter_endpoints_accessor_chip_tool.MatterEndpointsAccessorChipTool,
          matter_endpoints_accessor_pw_rpc.MatterEndpointsAccessorPwRpc,
          matter_sample_app_shell.MatterSampleAppShell,
          occupancy_sensing_chip_tool.OccupancySensingClusterChipTool,
          occupancy_sensing_pw_rpc.OccupancySensingClusterPwRpc,
          occupancy_sensor.OccupancySensorEndpoint,
          on_off_chip_tool.OnOffClusterChipTool,
          on_off_light.OnOffLightEndpoint,
          on_off_light_switch.OnOffLightSwitchEndpoint,
          on_off_plugin_unit.OnOffPluginUnitEndpoint,
          on_off_pw_rpc.OnOffClusterPwRpc,
          package_management_android.PackageManagementAndroid,
          pressure_measurement_chip_tool.PressureMeasurementClusterChipTool,
          pressure_measurement_pw_rpc.PressureMeasurementClusterPwRpc,
          pressure_sensor.PressureSensorEndpoint,
          pwrpc_button_default.PwRPCButtonDefault,
          pwrpc_common_default.PwRPCCommonDefault,
          pwrpc_event_subscription_default.PwRpcEventSubscriptionDefault,
          pwrpc_wifi_default.PwRPCWifiDefault,
          relative_humidity_measurement_chip_tool.RelativeHumidityMeasurementClusterChipTool,
          relative_humidity_measurement_pw_rpc.RelativeHumidityMeasurementClusterPwRpc,
          root_node.RootNodeEndpoint,
          shell_ssh.ShellSSH,
          speaker.SpeakerEndpoint,
          switch_chip_tool.SwitchClusterChipTool,
          switch_power_dli_powerswitch.SwitchPowerDliPowerswitch,
          switch_power_snmp.SwitchPowerSnmp,
          switch_power_unifi_switch.SwitchPowerUnifiSwitch,
          switch_power_usb_default.SwitchPowerUsbDefault,
          switch_power_usb_with_charge.SwitchPowerUsbWithCharge,
          switch_pw_rpc.SwitchClusterPwRpc,
          switchboard.SwitchboardDefault,
          temperature_measurement_chip_tool.TemperatureMeasurementClusterChipTool,
          temperature_measurement_pw_rpc.TemperatureMeasurementClusterPwRpc,
          temperature_sensor.TemperatureSensorEndpoint,
          thermostat.ThermostatEndpoint,
          thermostat_chip_tool.ThermostatClusterChipTool,
          thermostat_pw_rpc.ThermostatClusterPwRpc,
          unsupported_endpoint.UnsupportedEndpoint,
          usb_hub_default.UsbHubDefault,
          window_covering.WindowCoveringEndpoint,
          window_covering_pw_rpc.WindowCoveringClusterPwRpc,
          wpan_nrf_ot.WpanNrfOt,
      ],
      "keys": [
          raspberry_pi_key.SSH_KEY_PUBLIC,
          raspberry_pi_key.SSH_KEY_PRIVATE,
          unifi_poe_switch_key.SSH_KEY_PUBLIC,
          unifi_poe_switch_key.SSH_KEY_PRIVATE,
      ],
  }
