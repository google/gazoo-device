#!/bin/bash
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

# This script was written for testing gdm-install.sh and is only suppose to be
# used to try and remove (nearly) everything gdm-install.sh installs.

# It is NOT intended to be run directly but rather indirectly through the
# gdm-cleanup.sh that is created when running build.sh in the installers
# directory.
#
# The script is intended to remove the following:
# * debian packages in LINUX_REMOVE_PKGS listed below
# * python packages in PIP_REMOVE_PKGS listed below
# * udev files from /etc/udev/rules.d whose filenames match those in rules.d
#   directory here
# * gdm directory at /usr/local/gazoo/gdm
# * gdm wrapper script at /usr/local/bin/gdm
LINUX_REMOVE_PKGS="libftdi-dev libffi-dev lrzsz python3-dev android-sdk-platform-tools"
BREW_UNINSTALL_PACKAGES="libftdi coreutils android-platform-tools"
GDM_PATH="/usr/local/gazoo/gdm"
GDM_PATH_MAC="$HOME/gdm"
GDM_WRAPPER_PATH="/usr/local/bin/gdm"
GSUTIL_PATH="/opt/gsutil"
GSUTIL_ALIAS_PATH="/usr/local/bin/gsutil"
UDEV_SRC_PATH="rules.d"

source ./functions.sh

cleanup_common()
{
    cleanup_file_if_exists "$GDM_WRAPPER_PATH"
    cleanup_directory_if_exists "$GDM_PATH"
    cleanup_gsutil
}

cleanup_gsutil()
{
    [ -d "$GSUTIL_PATH" ] && sudo rm -rf $GSUTIL_PATH
    [ -h "$GSUTIL_ALIAS_PATH" ] && sudo rm $GSUTIL_ALIAS_PATH
}

cleanup_linux()
{
    rerun_self_using_sudo
    echo "Cleanup for Linux"
    cleanup_common
    cleanup_udev_rules "$UDEV_SRC_PATH"
    cleanup_apt_packages "$LINUX_REMOVE_PKGS"
    sudo apt -y autoremove
}

cleanup_mac()
{
    remove_homebrew_packages
    cleanup_gsutil
    [ -d "$GDM_PATH_MAC" ] && sudo rm -rf $GDM_PATH_MAC
    [ -f "$GDM_WRAPPER_PATH" ] && sudo rm $GDM_WRAPPER_PATH
}

remove_homebrew_packages()
{
    echo "chown'ing /usr/local/ to the current user to uninstall Brew packages"
    sudo chown -R $(whoami) /usr/local/bin /usr/local/etc /usr/local/sbin /usr/local/share /usr/local/share/doc
    HOMEBREW_NO_AUTO_UPDATE=1 brew uninstall $BREW_UNINSTALL_PACKAGES
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
    Debian ) cleanup_linux ;;
    Ubuntu ) cleanup_linux ;;
    Linux ) cleanup_linux ;;
    Darwin ) cleanup_mac ;;
    *      ) cleanup_unsupported ;;
esac

retval=$?

echo ""
echo "Cleanup done (exit $retval)"
exit $retval
