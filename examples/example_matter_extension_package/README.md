# Codelab: Extension Matter controller packages in GDM

GDM (Gazoo Device Manager) provides an extensible architecture upon which users can
build their own Matter device controllers. For the purposes of this codelab,
we've created an example Matter extension package which defines a new device type, `examplematterlighting`.
This codelab will walk you through the process of building the package,
registering it with GDM, and using it within a Python environment.

## Prerequisites

1. If you haven't installed GDM yet, follow
   [the installation steps](https://github.com/google/gazoo-device#install).
2. We'll try using the example Matter device controller with a real device.\
   The example Matter controller should work with any NRF Matter devices with
   lighting RPC endpoints.
   You can choose to build the Matter NRF sample lighting app on a dev board,
   or use your own Matter lighting device.

## Set up a NRF Matter lighting sample application

If you want to use your own Matter device, you can skip this section. \
Otherwise, simply follow the the instructions here to build a Nordic nRF lighting sample app:
https://github.com/google/gazoo-device/blob/master/docs/device_setup/Matter_NRF_lighting_sample_app.md

### Verify device connection

Make sure the [Pigweed](https://pigweed.googlesource.com/pigweed/pigweed/) RPC interface is enabled on your device.
You can try the lighting endpoint by following the step 4 (Try RPC) of the [lighting app setup](https://github.com/google/gazoo-device/blob/master/docs/device_setup/Matter_NRF_lighting_sample_app.md).

## Set up the extension package

### Check out the source code

Check out the gazoo-device repository:

```shell
git clone https://github.com/google/gazoo-device.git
cd gazoo-device
```

### Build and install the Matter extension package

Go to the example Matter extension package directory and build the package:

```shell
cd examples/example_matter_extension_package
python3 setup.py clean
python3 setup.py -v build sdist
```

This will build a distributable version of the package in `dist/`.

```shell
$ ls dist/
example_matter_extension_package-0.0.1.tar.gz
```

Install the example Matter extension package in your virtual environment:

```shell
{path-to-venv}/bin/pip install dist/example_extension_package-0.0.1.tar.gz
```

## Using the example Matter controller

### Register the extension and Detect the device

Register and detect your device from the Python interpreter:

```python
>>> import gazoo_device
>>> import example_matter_extension_package
>>> gazoo_device.register(example_matter_extension_package)
>>> m = gazoo_device.Manager()
>>> m.detect()
```

Your output will look like this:

```shell
>>> m.detect()

##### Step 1/3: Detecting potential new communication addresses. #####

   detecting potential AdbComms communication addresses
   detecting potential DockerComms communication addresses
   detecting potential JlinkSerialComms communication addresses
   detecting potential PtyProcessComms communication addresses
   detecting potential SshComms communication addresses
   detecting potential SerialComms communication addresses
No read/write permission for these serial address(es): ['/dev/bus/usb/001/001', '/dev/bus/usb/001/003', '/dev/bus/usb/001/124', '/dev/bus/usb/001/002', '/dev/bus/usb/001/126', '/dev/bus/usb/001/007', '/dev/bus/usb/001/009', '/dev/bus/usb/002/001', '/dev/bus/usb/002/002', '/dev/bus/usb/002/003', '/dev/disk/by-id/usb-Generic-_SD_MMC_CRW_28203008282014000-0:0', '/dev/bus/usb/003/001', '/dev/bus/usb/004/001', '/dev/bus/usb/004/002']
   detecting potential YepkitComms communication addresses
   detecting potential PigweedSerialComms communication addresses
Found 2 possible serialcomms connections:
   /dev/bus/usb/001/114
   /dev/bus/usb/001/006
Found 1 possible pigweedserialcomms connections:
   /dev/serial/by-id/usb-SEGGER_J-Link_000683094585-if00

##### Step 2/3 Identify Device Type of Connections. #####

Identifying pigweedserialcomms devices..
_dev_serial_by-id_usb-SEGGER_J-Link_000683094585-if00_detect.txt logging to file /home/chingtzuchen/gazoo/gdm/log/_dev_serial_by-id_usb-SEGGER_J-Link_000683094585-if00_detect.txt
_dev_serial_by-id_usb-SEGGER_J-Link_000683094585-if00_detect.txt closing switchboard processes
   /dev/serial/by-id/usb-SEGGER_J-Link_000683094585-if00 is a examplematterlighting.
   pigweedserialcomms device_type detection complete.
Identifying serialcomms devices..
   /dev/bus/usb/001/114 responses did not match a known device type.
   /dev/bus/usb/001/006 responses did not match a known device type.
   serialcomms device_type detection complete.

##### Step 3/3: Extract Persistent Info from Detected Devices. #####

Getting info from communication port /dev/serial/by-id/usb-SEGGER_J-Link_000683094585-if00 for examplematterlighting
Device type 'examplematterlighting' has no default event filters defined.
   examplematterlighting_detect checking device readiness: attempt 1 of 1
   examplematterlighting_detect starting GazooDeviceBase.check_device_ready
Power cycling properties not yet detected.
   examplematterlighting_detect health check 1/3 succeeded: Check power cycling ready.
   examplematterlighting_detect waiting up to 3s for device to be connected.
   examplematterlighting_detect health check 2/3 succeeded: Check device connected.
   examplematterlighting_detect logging to file /home/chingtzuchen/gazoo/gdm/log/_dev_serial_by-id_usb-SEGGER_J-Link_000683094585-if00_detect.txt
   examplematterlighting_detect health check 3/3 succeeded: Check create switchboard.
   examplematterlighting_detect GazooDeviceBase.check_device_ready successful. It took 0s.
   examplematterlighting_detect starting NrfMatterDevice.get_detection_info
   examplematterlighting_detect NrfMatterDevice.get_detection_info successful. It took 0s.
   examplematterlighting_detect closing switchboard processes

##### Detection Summary #####

   1 new devices detected:
      examplematterlighting-4585

   2 connections found but not detected:
      /dev/bus/usb/001/114
      /dev/bus/usb/001/006

If a connection failed detection, check https://github.com/google/gazoo-device/blob/master/docs/device_setup for tips

Device                     Alias           Type                 Model                Connected
>>> -------------------------- --------------- -------------------- -------------------- ----------
examplematterlighting-4585 <undefined>     examplematterlighting PROTO                connected

Other Devices              Alias           Type                 Model                Available
-------------------------- --------------- -------------------- -------------------- ----------

1 total Gazoo device(s) available.
```

### Control and command the device

You can also try sending RPCs to the device once it's detected. Follow the
instructions in the README:

1. [Create and control the device](https://github.com/google/gazoo-device/blob/master/docs/device_setup/Matter_NRF_lighting_sample_app.md#usage)

2. [Supported endpoints for the lighting app](https://github.com/google/gazoo-device/blob/master/docs/device_setup/Matter_NRF_lighting_sample_app.md#supported-endpoints)

### Device logs

GDM prints the name of the device log file whenever it starts device communication.

```python
>>> from gazoo_device import Manager
>>> m = Manager()
>>> example = m.create_device('examplematterlighting-4585')
Creating examplematterlighting-4585
Device type 'examplematterlighting' has no default event filters defined.
examplematterlighting-4585 checking device readiness: attempt 1 of 1
examplematterlighting-4585 starting GazooDeviceBase.check_device_ready
examplematterlighting-4585 health check 1/3 succeeded: Check power cycling ready.
examplematterlighting-4585 waiting up to 3s for device to be connected.
examplematterlighting-4585 health check 2/3 succeeded: Check device connected.
examplematterlighting-4585 logging to file /home/user/gazoo/gdm/log/examplematterlighting-4585-20211108-172121.txt
>>> examplematterlighting-4585 health check 3/3 succeeded: Check create switchboard.
examplematterlighting-4585 GazooDeviceBase.check_device_ready successful. It took 0s.
```

The log file can be accessed easily: ```/home/user/gazoo/gdm/log/examplematterlighting-4585-20211108-172121.txt```


## (Optional) Update example controller to fit your Matter devices

If you want to build Matter controller for your own Matter device, you'll need
to update the following context in the example Matter controller.


### Update detect criteria

GDM uses detection criteria to match controllers during device detection. To
update the detect criteria in example controller, simply check the [product name](https://github.com/google/gazoo-device/blob/master/examples/example_matter_extension_package/example_matter_device.py#L43)
and the [manufacturer name](https://github.com/google/gazoo-device/blob/master/examples/example_matter_extension_package/example_matter_device.py#L46) of your devices and change them accordingly.

```python
>>> from gazoo_device.utility import usb_utils
>>> device_addr = '/dev/serial/by-id/usb-SEGGER_J-Link_000683094585-if00'
>>> usb_utils.get_product_name_from_path(device_addr)
'J-Link'
>>> usb_utils.get_device_info(device_addr).manufacturer
'SEGGER'
>>>
```

Also, you can use ```gdm print-usb-info``` to show all connected devices USB information.

```shell
$ gdm print-usb-info
30 USB connections found.
Connection 0:
	address         /dev/bus/usb/001/001
	child_addresses []
	disk            None
	ftdi_interface  0
	manufacturer    Linux_5.10.46-5rodete1-amd64_xhci-hcd
	product_id      0002
	product_name    xHCI Host Controller
	serial_number   0000:00:14.0
	usb_hub_address None
	usb_hub_port    None
	vendor_id       1d6b
Connection 1:
	address         /dev/bus/usb/001/007
        < ... continued ... >
```

### Update vendor platform

If your Matter device is running on a EFR32 Silabs or ESP32 Espressif platform,
simply inherit the device class from [efr32_matter_device.Efr32MatterDevice](https://github.com/google/gazoo-device/blob/master/gazoo_device/base_classes/efr32_matter_device.py) or
[esp32_matter_device.Esp32MatterDevice](https://github.com/google/gazoo-device/blob/master/gazoo_device/base_classes/esp32_matter_device.py) respectively.

```python
from gazoo_device.base_classes import efr32_matter_device

class MyMatterDevice(efr32_matter_device.Efr32MatterDevice):
  ...
```

The current available vendor platforms for Matter in GDM are: NRF, EFR32 and ESP32.
