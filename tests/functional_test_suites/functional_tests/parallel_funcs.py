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

"""
Concurrent functions on Gazoo devices
This is a common functionality used across Gazoo devices. This will create multiple processes
that will upgrade, factory_reset, or reboot all the devices in their own process.
It will log all of the device interactions to the logger given
Raises an error if any device method fails


Common apis
 # Converts typical setup in user_settings to usable info dictionary
 build_info_dicts =
     parallel_funcs.get_parameter_dicts(self.devices, self.user_settings, 'upgrade')

 # Parallel upgrade of all devices
 parallel_funcs.upgrade(self.devices, build_info_dicts, self.logger)

 #Parallel factory_reset of all devices
 parallel_funcs.factory_reset(self.devices, self.logger)

 #To add your own parallel_func
   You need:
     1) a publicly available method (ex: def upgrade)
             Required args: list of devices, logger
             Optional args: dictionary of key (device_type): params_dict for method
     2) a private method (ex def _upgrade_device
             Required args: logger, device, params_dict

See Example3 for use of parallel_funcs in a test.
"""
from __future__ import absolute_import
import logging
import inspect
import multiprocessing as mp


def get_parameter_dicts(devices, user_settings, method_name):
    """Returns a parameter dictionary keyed by device types
       from user_settings config

    Args:
        devices: list of Gazoo device objects
        user_settings: flat dictionary of key (<device_type>_param): value
        method_name: Gazoo device method
    Returns:
        a dictionary of key <device_type>: value dictionary of params

    Note:
        Example input:
           user_settings = {'device_type_a_build_num': '123',
            'device_type_b_build_url': 'XXXX',
            'device_type_a_method': 'service'
           }
          Example output if method_name is 'reboot':
            {'device_type_a': {"method": "service"}}

          Example output if method_name is upgrade:
             {'device_type_a': {'build_num':'123'},
            'device_type_b':{build_url': 'XXXX'}}
        """

    parameter_dicts = {}

    for device in devices:
        device_type = device.device_type
        if device_type in parameter_dicts:
            continue  # device parameters already parsed
        try:
            method = getattr(device, method_name)
        except Exception:
            raise RuntimeError(
                "Device {} does not have a method {}".format(
                    device.name, method_name))
        method_arg_names = inspect.getargspec(method).args

        for key in user_settings:
            device_type_suffix = device_type + "_"  # device_type_build_url
            if key.startswith(device_type_suffix):
                # remove the device_type_prefix from the parameter
                arg_name = key.split(device_type_suffix)[1]
                if arg_name in method_arg_names:
                    try:
                        parameter_dicts[device_type][arg_name] = user_settings[key]
                    except KeyError:
                        parameter_dicts[device_type] = {arg_name: user_settings[key]}

    return parameter_dicts


def factory_reset(devices, logger=None):
    """Concurrently Factory reset devices.

    Args:
        devices: [] - list of Gazoo devices
        logger: None or logger object
    """
    parallel_process(action_name="factory_reset",
                     fcn=_factory_reset_device,
                     devices=devices,
                     logger=logger,
                     parameter_dicts=None,
                     timeout=300)


def upgrade(devices, parameter_dicts=None, logger=None):
    """Concurrently upgrade devices using param.

    Args:
        devices: [] - list of Gazoo devices
        parameter_dicts: None or dictionary of param_info by device_type
           {'device_type_a': {'build_num':'123', 'build_job': 'antares'},
            'device_type_b':{build_url': 'XXXX'}}
        logger: logging object

    Note:
      If device_type entry doesn't exist or is empty, device upgrades to default build
      The params match the args of device method 'upgrade'
    """
    parallel_process(action_name="upgrade",
                     fcn=_upgrade_device,
                     devices=devices,
                     logger=logger,
                     parameter_dicts=parameter_dicts,
                     timeout=600)


def upgrade_ota(devices, parameter_dicts=None, logger=None):
    """Concurrently upgrade devices over-the-air using params

    Args:
        devices: [] - list of Gazoo devices
        parameter_dicts: None or dictionary of param_info by device_type
          {'device_type_c':{'build_url':'XXXX', 'tier':'XX'},
          'device_type_b':{build_url':'XXXX', 'tier':'XX'}}
        logger: logging object

    Note:
      if device_type entry doesn't exits or is empty, device OTA upgrades using default
      parameters.
      The params match the args of the device method 'upgrade_ota'
    """
    parallel_process(action_name="upgrade_ota",
                     fcn=_upgrade_ota_device,
                     devices=devices,
                     parameter_dicts=parameter_dicts,
                     timeout=200)


def reboot(devices, parameter_dicts=None, logger=None):
    """Concurrently reboot devices according to reboot info dict.

    Args:
        devices: [] - list of Gazoo devices
        user_settings: {} - dictionary of device_type, reboot_info
           {'device_type_d_no_wait' : 1}
        logger: logging object

    Note: if user_settings is None, devices reboot with default no_wait = False
    """
    parallel_process(action_name="reboot",
                     fcn=_reboot_device,
                     devices=devices,
                     logger=logger,
                     parameter_dicts=parameter_dicts,
                     timeout=300)


def parallel_process(action_name, fcn, devices, logger=None, parameter_dicts=None, timeout=600):
    """Concurrently apply function to each device

    Args:
      action: (str) terse description of the function
      fcn: (function) that takes a logger, Gazoo device object and the 'args'
          Example: upgrade_device(logger, device, args)
      devices: list of Gazoo device objects
      parameter_dicts: (dict) of arguments to send to the fcn by device_type

      timeout: (int) seconds before terminating all the parallel processes

    Note: raises RuntimeError if any of the parallel functions raise error or timeouts
    """
    if not logger:
        logger = logging.getLogger()

    if not parameter_dicts:
        parameter_dicts = {}

    # Verify is list of devices
    if not isinstance(devices, list):
        raise RuntimeError(
            "Devices should be a list. Instead its a {}. Devices: {}".format(
                type(devices), devices))
    if isinstance(devices[0], str):
        raise RuntimeError(
            "Devices should be a list of device objects. Instead its a list of string. Devices: {}"
            .format(devices))
    try:
        device_names = [device.name for device in devices]
    except:
        raise RuntimeError(
            "Unable to obtain the device name from devices. Are all devices Gazoo device objects?")
    logger.info("Concurrently {} the following for {}s: {}".format(action_name,
                                                                   timeout,
                                                                   ",".join(device_names)))

    error_message_queue = mp.Queue()
    error_message_queue.cancel_join_thread()

    processes = []
    if not logger:
        logger = logging.getLogger()
    for device in devices:
        device_type = device.device_type
        args = {}
        if device_type in parameter_dicts:
            args = parameter_dicts[device_type]

        process = mp.Process(target=_sub_process,
                             args=(error_message_queue,
                                   fcn,
                                   logger,
                                   device,
                                   args))
        processes.append(process)

    for process in processes:
        process.start()

    for process in processes:
        process.join(timeout=timeout)
        if process.is_alive():
            process.terminate()
            process.join()

    error_msgs = []
    while not error_message_queue.empty():
        error_msgs.append(error_message_queue.get())
    if error_msgs:
        raise RuntimeError(", ".join(error_msgs))


def _sub_process(error_message_queue, fcn, logger, device, args=None):
    """Factory reset device.

    Args:
        device: Gazoo device object
        exception_queue: multiprocess queue for exception logs
    """
    try:
        fcn(logger, device, args)
    except Exception as error:
        error_message_queue.put_nowait(repr(error))


def _upgrade_device(logger, device, upgrade_params_dict=None):
    """Upgrade device.

    Args:
       logger: logger object
       device: Gazoo device object
       upgrade_params_dict: {} or dictionary of build information
          {'build_num': '123'}
    """
    if upgrade_params_dict:
        logger.info("{} upgrading with parameters: {}".format(device.name, upgrade_params_dict))
        device.upgrade(**upgrade_params_dict)
    else:
        logger.info("{} upgrading to default build".format(device.name))
        device.upgrade()


def _upgrade_ota_device(logger, device, upgrade_ota_params_dict=None):
    """Upgrade device over-the-air(OTA).

    Args:
        logger: logger object
        device: Gazoo device object
        upgrade_ota_params_dicts: {} or dictionary of build and services information
        {'device_type_a':{'build_url':'XXXX','service_tier':'XX'},
        'device_type_b':{build_url':'XXXX'}}
    """
    if upgrade_ota_params_dict:
      logger.info("{} OTA upgrading with parameters: {}".format(device.name, upgrade_ota_params_dict))
      device.upgrade_ota(**upgrade_ota_params_dict)
    else:
      logger.info("{} OTA upgrading with default parameters.".format(device.name))
      device.upgrade_ota()


def _factory_reset_device(logger, device, args=None):
    """Factory reset device
    Args:
       logger: logger object
       device: Gazoo device object
       args: None
    """
    device.factory_reset()


def _reboot_device(logger, device, reboot_params_dict=None):
    """Reboot  device

    Args:
           logger: logger object
           device: Gazoo device object
           reboot_params_dict: None or dictionary of reboot information
              Ex: {'method': 'service'}
    """
    if reboot_params_dict:
        device.reboot(**reboot_params_dict)
    else:
        device.reboot()
