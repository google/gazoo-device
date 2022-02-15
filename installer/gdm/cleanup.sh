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

# This script uninstalls GDM dependencies and removes the ~/gazoo directory.
#
# It is NOT intended to be run directly but rather indirectly through the
# gdm-cleanup.sh archive that is created when running build.sh in the installer
# directory.
#
# Do not run gdm-cleanup.sh as root.

LINUX_PACKAGES="libftdi-dev libffi-dev lrzsz python3-dev android-sdk-platform-tools"
declare -a MAC_PACKAGES
MAC_PACKAGES=("libftdi" "coreutils" "android-platform-tools")
GAZOO_DIR="$HOME/gazoo/"
UDEV_SRC_PATH="rules.d"

source ./functions.sh

cleanup_common()
{
  echo "Removing Gazoo directory $GAZOO_DIR"
  rm -rf "$GAZOO_DIR"
}

cleanup_linux()
{
  cleanup_udev_rules "$UDEV_SRC_PATH"

  echo "Removing apt packages $LINUX_PACKAGES"
  # Avoid quoting $LINUX_PACKAGES as it contains a list of strings.
  sudo apt-get remove -y $LINUX_PACKAGES
  sudo apt -y autoremove

  cleanup_common
}

cleanup_mac()
{
  remove_homebrew_packages
  cleanup_common
}

remove_homebrew_packages()
{
  local dirs
  dirs="/usr/local/bin /usr/local/etc /usr/local/sbin /usr/local/share /usr/local/share/doc"
  echo "Changing ownership of $dirs to $(whoami) to uninstall Brew packages"
  # Avoid quoting $dirs as it contains a list of strings.
  sudo chown -R "$(whoami)" $dirs

  echo "Uninstalling Brew packages" "${MAC_PACKAGES[@]}"
  for brew_package in "${MAC_PACKAGES[@]}"
  do
    HOMEBREW_NO_AUTO_UPDATE=1 brew uninstall "$brew_package"
  done
  echo "Brew uninstalls completed"
}

cleanup_unsupported()
{
  echo "Unsupported operating system. Please use Linux or MacOS." 1>&2
  exit 1
}

# Check the lsb-release file for some variables that tell us what OS we're on.
if [ -f /etc/lsb-release ]; then
  . /etc/lsb-release
else
  DISTRIB_ID=$(uname)
fi
# DISTRIB_ID is loaded into the env by sourcing /etc/lsb-release
case "$DISTRIB_ID" in
  Debian) cleanup_linux ;;
  Ubuntu) cleanup_linux ;;
  Linux) cleanup_linux ;;
  Darwin) cleanup_mac ;;
  *) cleanup_unsupported ;;
esac

echo
echo "GDM has been uninstalled."
