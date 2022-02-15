# GDM device setup: Matter(CHIP) locking sample app on EFR32 dev board

Manufacturer: https://www.silabs.com/

Supported models: EFR32MG

## Setup

**1. Clone**

Clone the source (master) from the Matter repository
https://github.com/project-chip/connectedhomeip and do submodule update.

Inside your own `${project}` directory:

```
git clone https://github.com/project-chip/connectedhomeip.git
cd connectedhomeip
git submodule update --init
```

**2. Build**

Build the Matter lighting sample app image with Pigweed RPC debug interface for
EFR32 with `gn` command line tool. Follow the instruction on
https://github.com/project-chip/connectedhomeip/tree/master/examples/lock-app/efr32#building.

**3. Flash**

Flash the image (`.s37`) to the EFR32 board by using
[Simplicity Commander](https://community.silabs.com/s/article/simplicity-commander?language=en_US).
Follow the instructions on
https://github.com/project-chip/connectedhomeip/tree/master/examples/lock-app/efr32#flashing-the-application.

You may also use GDM for flashing. You'll need to download the `.hex` image from
the above build bot, or manually convert the image from `.s37` to `.hex`
following the
[commander instruction](https://www.silabs.com/documents/public/user-guides/ug162-simplicity-commander-reference-guide.pdf).
Then use GDM python interpreter to flash:

```
>>> from gazoo_device import Manager
>>> m = Manager()
>>> efr = m.create_device('efr32-3453')
>>> efr.flash_build.flash_device(['/path/to/efr32_lock.hex'])
```

Or using GDM CLI:

```
gdm issue efr32-3453 - flash_build - upgrade --build_file=/path/to/efr32_lock.hex
```

**4. Device detection**

Detect the EFR32 locking app: `gdm detect`

```
Device                         Alias           Type                     Model                Connected
------------------------------ --------------- ------------------------ -------------------- ----------
efr32matterlocking-3453        <undefined>     efr32matterlocking       PROTO                connected

Other Devices                  Alias           Type                     Model                Available
------------------------------ --------------- ------------------------ -------------------- ----------
```

## Usage

Using GDM CLI

```
gdm issue efr32matterlocking-3453 - door_lock - door_lock - lock_door  # Lock the device
gdm issue efr32matterlocking-3453 - door_lock - door_lock - lock_state  # Get locked state
gdm issue efr32matterlocking-3453 - door_lock - door_lock - unlock_door  # Unlock the device
gdm issue efr32matterlocking-3453 - factory_reset
gdm issue efr32matterlocking-3453 - reboot
gdm issue efr32matterlocking-3453 - pw_rpc_common - vendor_id
gdm issue efr32matterlocking-3453 - pw_rpc_common - product_id
gdm issue efr32matterlocking-3453 - pw_rpc_common - software_version
gdm man efr32matterlocking  # To see all supported functionality
```

Or inside the python console:

Activate GDM virtual env and open the console:

```
source ~/gazoo/gdm/virtual_env/bin/activate
python
```

Inside python console:

```
>>> from gazoo_device import Manager
>>> m = Manager()
>>> efr = m.create_device('efr32matterlocking-3453')
>>> efr.door_lock.door_lock.lock_door()
>>> efr.door_lock.door_lock.lock_state
>>> efr.close()
```

## Supported endpoints

The latest supported locking endpoints in GDM based on the Matter
[locking proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/locking_service.proto)
and
[device proto](https://github.com/project-chip/connectedhomeip/blob/master/examples/common/pigweed/protos/device_service.proto).

**1. Lock/unlock and get locked state**

```
>>> efr.door_lock.door_lock.lock_door()
>>> efr.door_lock.door_lock.unlock_door()
>>> efr.door_lock.door_lock.lock_state
```

**2. Reboot and factory reset**

```
>>> efr.reboot()
>>> efr.factory_reset()
```
