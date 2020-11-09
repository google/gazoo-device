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
GDM_PATH="/usr/local/gazoo/gdm"
GDM_WRAPPER_PATH="/usr/local/bin/gdm"
PIP_REMOVE_PKGS="gazoo-device"
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
    cleanup_directory_if_exists "$GSUTIL_PATH"
    cleanup_file_if_exists "/usr/bin/local/gsutil"
}

cleanup_linux()
{
    rerun_self_using_sudo
    echo "Cleanup for Linux"
    cleanup_common
    cleanup_udev_rules "$UDEV_SRC_PATH"
    cleanup_pip_packages "$PIP_REMOVE_PKGS"
    cleanup_apt_packages "$LINUX_REMOVE_PKGS"
}

cleanup_unsupported()
{
    echo "Unsupported operating system. Please use Linux." 1>&2
    exit 1
}

# Check the lsb-release file for some variables that tell us what OS we're on.
# gLinux rodete, Ubuntu 16LTS and 18LTS have this file.
if [ -f /etc/lsb-release ]; then
    . /etc/lsb-release
else
    echo " /etc/lsb-release is not readable"
    exit 1
fi
# DISTRIB_ID is loaded into the env by sourcing /etc/lsb-release
case "$DISTRIB_ID" in
    Debian ) cleanup_linux  ;;
    Ubuntu ) cleanup_linux  ;;
    *      ) cleanup_unsupported "/etc/lsb-release $DISTRIB_ID says you are on an unsupported OS" ;;
esac

retval=$?

echo ""
echo "Cleanup done (exit $retval)"
exit $retval
