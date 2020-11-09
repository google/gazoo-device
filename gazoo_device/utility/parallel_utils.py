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

"""Reusable utility functions for executing methods in parallel.

This will create multiple processes to execute device operations on multiple devices. Device
interactions will be logged to the provided logger. Errors can optionally be raised if device
methods fail.

Example usage:
    sample_function_results = parallel_utils.parallel_process(
        "sample_function",
        self._sample_function,
        device_instances)

    for result in sample_function_results:
        do_something(result)
"""
import multiprocessing
import time
from gazoo_device import gdm_logger
from gazoo_device.utility import common_utils
from six.moves import queue

logger_gdm = gdm_logger.get_gdm_logger()

TIMEOUT_PROCESS = 600.0
TIMEOUT_TERMINATE_PROCESS = 5
REQUIRED_PROPS = ["name", "DEVICE_TYPE"]


def parallel_process(action_name,
                     fcn,
                     devices,
                     logger=None,
                     parameter_dicts=None,
                     timeout=TIMEOUT_PROCESS):
    """Concurrently apply function to each device.

    TODO(b/152442892): Increase the flexibility of this function.

    Args:
        action_name (str): terse description of the function
        fcn (function): function to execute in parallel
        devices (list): list of Gazoo device objects
        logger (logger): logger object that will be passed to fcn
        parameter_dicts (dict): of arguments to send to the fcn by device_type
        timeout (int): seconds before terminating all the parallel processes

    Returns:
        list: results from parallel functions if return_results flag is specified. this will be
            a list of either an exception raised while running the function or data added
            manually to the multiprocessing queue.

    Raises:
        RuntimeError: if any of the parallel functions raise error or timeouts and
            return_results flag is not true
        AttributeError: if provided devices are missing required props.
    """
    if not parameter_dicts:
        parameter_dicts = {}

    # verify list of devices was recieved
    if not isinstance(devices, list):
        raise RuntimeError(
            "Devices should be a list. Instead its a {}. Devices: {}".format(
                type(devices), devices))

    # verify devices have required properties
    for prop in REQUIRED_PROPS:
        if not all(hasattr(device, prop) for device in devices):
            raise AttributeError(
                "Devices must have {} property. Devices: {}".format(prop, devices))

    device_names = [device.name for device in devices]
    logger_gdm.info(
        "Executing {} concurrently for {}s on devices {}".format(action_name,
                                                                 timeout,
                                                                 ",".join(device_names)))

    # create queues to manage parallel processes
    return_queue = multiprocessing.Queue()
    error_queue = multiprocessing.Queue()
    processes = []

    # initiate new process for each device with provided arguments
    for device in devices:
        device_type = device.DEVICE_TYPE
        args = [fcn, return_queue, error_queue]
        kwargs = {"device": device}
        if logger:
            kwargs["logger"] = logger
        if device_type in parameter_dicts:
            kwargs["parameter_dict"] = parameter_dicts[device_type]
        process = multiprocessing.Process(target=_sub_process, args=args, kwargs=kwargs)
        processes.append(process)

    # run each process in parallel
    deadline = time.time() + timeout
    for process in processes:
        common_utils.run_before_fork()
        process.start()
        common_utils.run_after_fork_in_parent()

    for process in processes:
        remaining_timeout = max(0, deadline - time.time())  # ensure timeout >= 0
        process.join(timeout=remaining_timeout)
        if process.is_alive():
            process.terminate()
            process.join(timeout=TIMEOUT_TERMINATE_PROCESS)

    # handle results from queue
    errors = get_messages_from_queue(error_queue)
    if errors:
        raise RuntimeError(", ".join(errors))
    return get_messages_from_queue(return_queue)


def issue_devices_parallel(method_name, devices, parameter_dicts=None, timeout=TIMEOUT_PROCESS):
    """Concurrently issue a device command to multiple devices.

    Args:
        method_name (str): device method to call in parallel.
        devices (list): list of Gazoo Device objects.
        parameter_dicts (dict): of arguments to send to the method by device_type.
        timeout (int): seconds before terminating all the parallel processes.

    Returns:
        list: results of parallel method calls.

    Note:
        The nested function _issue_devices_parallel will be the function executed in separate
        processes for each device.
    """
    def _issue_devices_parallel(device, parameter_dict=None):
        """Execute device method."""
        parameter_dict = parameter_dict or {}
        method = getattr(device, method_name)
        return method(**parameter_dict)

    return parallel_process(method_name,
                            _issue_devices_parallel,
                            devices,
                            parameter_dicts=parameter_dicts,
                            timeout=timeout)


def get_messages_from_queue(mp_queue, timeout=0.01):
    """Safely get all messages from a multiprocessing queue.

    Args:
        mp_queue (queue): a multiprocess Queue instance
        timeout (float): seconds to block other processes out from the queue

    Returns:
        list: List of messages or an empty list if there weren't any
    """
    msgs = []
    # According to the python docs https://docs.python.org/2/library/multiprocessing.html
    # after putting an object on an empty queue there may be an
    #  infinitesimal delay before the queue's empty() method returns False
    #
    # We've actually run into this (SPT-1354) so we'll first kick the
    # tires with a get() and then see if there are more using empty()
    try:
        msgs.append(mp_queue.get(True, timeout))
    except queue.Empty:
        pass
    else:
        while not mp_queue.empty():
            msgs.append(mp_queue.get_nowait())
    return msgs


def _sub_process(fcn, return_queue, error_queue, **kwargs):
    """Helper function for calling methods in parallel.

    Args:
        fcn (function): function to execute
        return_queue (queue): a multiprocess Queue instance for results
        error_queue (queue): a multiprocess Queue instance for exceptions
        **kwargs (dict): other keyworded arguments to pass to the function
    """
    try:
        result = fcn(**kwargs)
        if result is not None:
            return_queue.put_nowait(result)
    except Exception as err:
        error_queue.put_nowait(repr(err))
