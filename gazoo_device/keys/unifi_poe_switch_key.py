"""SSH keys for gazoo_device/auxiliary_devices/unifi_poe_switch.py."""
from gazoo_device import config
from gazoo_device import data_types

SSH_KEY_PRIVATE = data_types.KeyInfo(
    file_name="unifi_switch_ssh_key",
    type=data_types.KeyType.SSH,
    package=config.KEY_PACKAGE_NAME)

# Public SSH keys aren't used by GDM, but are needed during passwordless SSH
# setup via ssh-copy-id.
SSH_KEY_PUBLIC = data_types.KeyInfo(
    file_name="unifi_switch_ssh_key.pub",
    type=data_types.KeyType.SSH,
    package=config.KEY_PACKAGE_NAME)
