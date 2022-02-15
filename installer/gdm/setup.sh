#!/bin/bash
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

# This script installs GDM host dependencies and installs GDM under ~/gazoo.
#
# It is NOT intended to be run directly but rather indirectly through the
# gdm-install.sh archive that is created when running build.sh in the installer
# directory.
#
# Do not run gdm-install.sh as root.

LINUX_PACKAGES="libftdi-dev libffi-dev lrzsz python3-dev python3-pip android-sdk-platform-tools udisks2 curl wget unzip snmp"
# udisks2 to get udisksctl
declare -a MAC_PACKAGES
MAC_PACKAGES=("libftdi" "coreutils" "android-platform-tools")

GAZOO_DIR="$HOME/gazoo"
GAZOO_BIN_DIR="$GAZOO_DIR/bin"
GAZOO_TESTBEDS_DIR="$GAZOO_DIR/testbeds"
GDM_DIR="$GAZOO_DIR/gdm"

GDM_VIRTUAL_ENV="$GDM_DIR/virtual_env"
GDM_LAUNCHER="$GAZOO_BIN_DIR/gdm"

CONFIG_SRC_PATH="conf"
UDEV_SRC_PATH="rules.d"
EXAMPLE_TESTBED_MOBLY="One-Exampledevice.yml"

source ./functions.sh


install_common()
# Installation steps common to both Linux and Mac hosts.
{
  create_gazoo_paths_if_missing
  create_default_configs
  python3 -m pip install virtualenv

  copy_file_if_not_exist gdm "$GDM_LAUNCHER" 744
  echo "Installing GDM in virtual environment $GDM_VIRTUAL_ENV"
  "$GDM_LAUNCHER" update-gdm
  exit_if_non_zero $? "Error installing GDM in virtual environment"
}


install_for_linux()
# Installation steps specific to Linux hosts.
{
  echo "Installing apt packages $LINUX_PACKAGES"
  sudo apt-get --fix-broken install
  # Avoid quoting $LINUX_PACKAGES as it contains a list of strings.
  sudo apt-get install -y $LINUX_PACKAGES
  install_udev_rules "$UDEV_SRC_PATH"

  local eject_path
  eject_path=$(which eject)
  local udisksctl_path
  udisksctl_path=$(which udisksctl)
  echo "Executing chmod u+s on $eject_path and $udisksctl_path"
  sudo chmod u+s "$eject_path" "$udisksctl_path"

  install_common
}


install_for_mac()
# Installation steps specific to Mac hosts.
{
  which brew > /dev/null
  exit_if_non_zero $? "Brew package manager is missing. Please install Brew: https://brew.sh"

  local dirs
  dirs="/usr/local/bin /usr/local/etc /usr/local/sbin /usr/local/share /usr/local/share/doc"
  echo "Changing ownership of $dirs to $(whoami) to install Brew packages"
  # Avoid quoting $dirs as it contains a list of strings.
  sudo chown -R "$(whoami)" $dirs

  xcode-select -p > /dev/null
  exit_if_non_zero $? "'xcode-select' CLI is missing. Please install it: 'xcode-select --install'"

  echo "Installing Brew packages" "${MAC_PACKAGES[@]}"
  for brew_package in "${MAC_PACKAGES[@]}"
  do
    HOMEBREW_NO_AUTO_UPDATE=1 brew install "$brew_package"
  done
  echo "Brew installs completed"

  install_common
}


install_unsupported()
{
  echo "Unsupported operating system $DISTRIB_ID. Please use Linux or MacOS." 1>&2
  exit 1
}


create_default_configs()
# Creates default GDM config files and example testbed files.
{
  echo "Creating default GDM config files in $GDM_DIR/conf"
  for file in $CONFIG_SRC_PATH/*.json; do
      copy_file_if_not_exist "$file" "$GDM_DIR/$file" 644
  done
  copy_file_if_not_exist "$CONFIG_SRC_PATH/$EXAMPLE_TESTBED_MOBLY" \
                         "$GAZOO_TESTBEDS_DIR/$EXAMPLE_TESTBED_MOBLY" 644
}


create_gazoo_paths_if_missing()
# Creates directory paths under ~/gazoo.
{
  echo "Creating GDM directories"
  make_directory_if_not_exists "$GAZOO_DIR" 755
  make_directory_if_not_exists "$GAZOO_BIN_DIR" 755
  make_directory_if_not_exists "$GAZOO_TESTBEDS_DIR" 755
  make_directory_if_not_exists "$GDM_DIR" 755

  make_directory_if_not_exists "$GDM_DIR/conf" 755
  make_directory_if_not_exists "$GDM_DIR/conf/backup" 755
  make_directory_if_not_exists "$GDM_DIR/data" 755
  make_directory_if_not_exists "$GDM_DIR/log" 755
  make_directory_if_not_exists "$GDM_DIR/tty" 755
  make_directory_if_not_exists "$GDM_DIR/detok" 755
  make_directory_if_not_exists "$GDM_DIR/bin" 755
}


which python3 > /dev/null
exit_if_non_zero $? "Python 3 is missing. Please install Python 3."

# Check the lsb-release file for some variables that tell us what OS we're on.
if [ -f /etc/lsb-release ]; then
  . /etc/lsb-release
else
  DISTRIB_ID=$(uname)
fi
# DISTRIB_ID is loaded into the env by sourcing /etc/lsb-release
case "$DISTRIB_ID" in
  Debian) install_for_linux ;;
  Ubuntu) install_for_linux ;;
  Linux) install_for_linux ;;
  Darwin) install_for_mac ;;
  *) install_unsupported ;;
esac

echo
echo "Installation complete! Installed gdm to $GDM_LAUNCHER."
echo "Add the following to your ~/.bashrc or ~/.bash_profile:"
echo "export PATH=\"$GAZOO_BIN_DIR:\$PATH\""
echo
echo "Be sure to read the documentation for further setup:"
echo "https://github.com/google/gazoo-device/README.md"
