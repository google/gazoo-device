# GDM device setup: Raspberry Pi passwordless SSH key setup

Supported models: Raspberry Pi 3 and 4.

Supported kernel images: `Raspbian` and `Ubuntu`

## Setup passwordless SSH key

1.  Configure GDM SSH keys: run `gdm download-keys` (on the host):

    If you don't have a key in
    `~/gazoo/gdm/keys/gazoo_device_controllers/raspberrypi3_ssh_key`, you'll see
    an error prompting you to generate a key. Follow the prompt to generate all
    required keys.

    Alternatively, you can copy an existing private/public SSH key pair to
    `~/gazoo/gdm/keys/gazoo_device_controllers/raspberrypi3_ssh_key` and
    `~/gazoo/gdm/keys/gazoo_device_controllers/raspberrypi3_ssh_key.pub`.

2.  Set up passwordless SSH with RPi using the GDM key (on the host):

    Running on `Raspbian` image (default user is `pi`):

    ```shell
    ssh-copy-id -i ~/gazoo/gdm/keys/gazoo_device_controllers/raspberrypi3_ssh_key.pub pi@<IP_ADDRESS>
    ```

    Running on `Ubuntu` image (default user is `ubuntu`):

    ```shell
    ssh-copy-id -i ~/gazoo/gdm/keys/gazoo_device_controllers/raspberrypi3_ssh_key.pub ubuntu@<IP_ADDRESS>
    ```

3.  Check that the RPi is accessible from the host:

    Running on `Raspbian`:

    ```shell
    ping <IP_ADDRESS>
    ssh -i ~/gazoo/gdm/keys/gazoo_device_controllers/raspberrypi3_ssh_key pi@<IP_ADDRESS>
    ```

    Running on `Ubuntu`:

    ```shell
    ping <IP_ADDRESS>
    ssh -i ~/gazoo/gdm/keys/gazoo_device_controllers/raspberrypi3_ssh_key ubuntu@<IP_ADDRESS>
    ```
