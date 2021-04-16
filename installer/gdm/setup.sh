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

# This script was written for installing all files, debian packages, and python
# modules needed for Python gazoo-device to work in a (shared) virtual
# environment. This script is not intended to be run directly but indirectly
# through the gdm-install.sh script created by running build.sh in the
# installers directory.
#
# NOTE: It is expected that people run gdm-install.sh without root privileges
# as we want to be able to install GDM in the virtual environment as we return
# from the "sudo ./$0" call in the rerun_self_using_sudo method. The reason is
# that some users may not have sudo privileges on their machine and installing
# additional Pip packages and upgrading GDM in the virtual machine might become
# difficult or impossible for them to do if GDM is installed as a root user.
#
# The script is intended to install the following:
# * debian and ubuntu packages in COMMON_REQUIRED_PKGS and UBUNTU_REQUIRED_PKGS listed below
# * python packages in PIP_REQUIRED_PKGS listed below
# * udev files into /etc/udev/rules.d
# * create link from /gazoo to /usr/local/gazoo
# * creation of /usr/local/gazoo/gdm shared directory
# * default configuration file in /usr/local/gazoo/gdm/conf
# * empty log file in /usr/local/gazoo/gdm/log
# * shared virtual environment at /usr/local/gazoo/gdm/virtual_env
# * gdm launcher script at /usr/local/bin/gdm
CONFIG_SRC_PATH="conf"

COMMON_REQUIRED_PKGS="libftdi-dev libffi-dev lrzsz python3-dev python3-pip android-sdk-platform-tools"
# udisks2 to get udisksctl
UBUNTU_REQUIRED_PKGS="${COMMON_REQUIRED_PKGS} udisks2 curl wget unzip"
BREW_PACKAGES="libftdi coreutils python"
BREW_CASK_PACKAGES="android-platform-tools"

GAZOO_LINK="/gazoo"
if [ "$(uname)" == "Darwin" ]; then
    GAZOO_PATH=$HOME
else
    GAZOO_PATH="/usr/local/gazoo"
fi
GAZOO_OPT_PATH="/opt/gazoo"
GAZOO_TESTBED_PATH="$GAZOO_OPT_PATH/testbeds"
GDM_PATH="$GAZOO_PATH/gdm"
GDM_VIRTUAL_ENV="$GDM_PATH/virtual_env"
GDM_WRAPPER_PATH="/usr/local/bin/gdm"
PIP_REQUIRED_PKGS="virtualenv"
UDEV_SRC_PATH="rules.d"
EXAMPLE_TESTBED="One-Exampledevice.yml"

source ./functions.sh

add_udisksctl_eject_suid_bit()
{
    local EJECT=$(which eject)
    local UDISKSCTL=$(which udisksctl)
    chmod u+s $EJECT
    chmod u+s $UDISKSCTL
}

install_gsutil()
{
    local GSUTIL=$(which gsutil)
    if [ -z "$GSUTIL" ]; then
        echo "Installing gsutil"
        curl --output /tmp/gsutil.zip https://storage.googleapis.com/pub/gsutil.zip
        sudo unzip -q -d /opt /tmp/gsutil.zip
        rm /tmp/gsutil.zip
        sudo ln -s /opt/gsutil/gsutil /usr/local/bin/gsutil
        if [ "$(uname)" == "Darwin" ]; then
            # On Macs /usr/local is chown'd to the current user, so chown the new link as well
            sudo chown -h $(whoami) /usr/local/bin/gsutil
        fi

        local python_path=$(which python)
        local python3_path=$(which python3)
        # gsutil runs itself as #!/usr/bin/env python.
        # If there's no Python on the machine, but it has Python 3, link Python to Python 3.
        if [ -z "$python_path" ]; then
            sudo ln -s "$python3_path" /usr/local/bin/python
            # Don't have to chown the symlink on Macs as Macs do have "python" by default.
        fi
    fi
}

install_common()
{
    install_gsutil
    make_gdm_paths_if_not_exist
    make_default_configs
    if [ "$(uname)" != "Darwin" ]; then  # "/" is mounted as read-only on Macs
        make_link_if_not_exists $GAZOO_LINK $GAZOO_PATH
    fi
    make_virtual_environment_if_not_exists "$GDM_VIRTUAL_ENV"
    copy_file_if_changed gdm $GDM_WRAPPER_PATH "" 777
    echo ""
}
install_packages_via_homebrew()
{
    echo "Verifying brew packages installed and up to date..."
    which brew >/dev/null
    exit_if_non_zero $? "Please install brew first: https://brew.sh"

    xcode-select -p > /dev/null
    exit_if_non_zero $? "Please install xcode command lines 'xcode-select --install'"
    HOMEBREW_NO_AUTO_UPDATE=1 brew install $BREW_PACKAGES
    HOMEBREW_NO_AUTO_UPDATE=1 brew cask install $BREW_CASK_PACKAGES
    echo "Brew installs completed"
    echo ""
}

install_for_debian()
{
    get_us_into_sudo
    apt_get_command "--fix-broken install"
    architecture=$(uname -m)
    if [ "$architecture" != "aarch64" ]; then  # Not ARM64
        dpkg --add-architecture i386
    fi
    install_for_both_debian_ubuntu "$UBUNTU_REQUIRED_PKGS"
}
install_for_ubuntu()
{
    get_us_into_sudo
    dpkg --add-architecture i386
    if [ "$architecture" != "aarch64" ]; then  # Not ARM64
        dpkg --add-architecture i386
    fi
    install_for_both_debian_ubuntu "$UBUNTU_REQUIRED_PKGS"
}

install_for_mac()
{
    echo "Installing on mac"
    echo "Need sudo to enable installs to /usr/local/bin"
    sudo chown -R $(whoami) /usr/local/bin /usr/local/etc /usr/local/sbin /usr/local/share /usr/local/share/doc
    install_packages_via_homebrew
    pip3 install virtualenv
    install_common
    install_gdm_in_virtual_env
    print_user_info_and_exit $?
}

get_us_into_sudo()
{
    if [ ! -z "$SUDO_USER" ]; then
        username="$SUDO_USER"
    else
        username="$USER"
    fi
    rerun_self_using_sudo
}

install_for_both_debian_ubuntu()
{
    local required_apt_packages="$1"
    echo "Installing for Linux for user '$username'"
    install_apt_packages "$required_apt_packages"
    install_pip_packages "$PIP_REQUIRED_PKGS"
    install_udev_rules "$UDEV_SRC_PATH"
    install_common
    add_udisksctl_eject_suid_bit
    install_gdm_in_virtual_env
    print_user_info_and_exit $?
}

install_gdm_in_virtual_env()
{
    echo "Installing GDM in shared virtual environment"
    if [ -x $GDM_WRAPPER_PATH ]; then
        $GDM_WRAPPER_PATH update-gdm
        exit_if_non_zero $? "Error installing GDM in virtual environment"
    else
        echo "GDM wrapper executable missing or failed to install earlier" 1>&2
        return 1
    fi
}

install_unsupported()
{
    echo "Unsupported operating system. Please use Linux or MacOS." 1>&2
    echo $1
    exit 1
}

make_default_configs()
{
    for file in $CONFIG_SRC_PATH/*.json; do
        copy_file_if_not_exist $file $GDM_PATH/$file "" 777
    done
    copy_file_if_not_exist $CONFIG_SRC_PATH/$EXAMPLE_TESTBED \
                           $GAZOO_TESTBED_PATH/$EXAMPLE_TESTBED "" 777
}

make_gdm_paths_if_not_exist()
{
    if [ "$(uname)" != "Darwin" ]; then
        # On Macs, $GAZOO_PATH is $HOME, which already exists with "correct" permissions
        make_directory_if_not_exists $GAZOO_PATH "" 777
        chmod -R 0777 $GAZOO_PATH
    fi
    if [ ! -d "$GAZOO_OPT_PATH" ]; then
        sudo mkdir "$GAZOO_OPT_PATH"
    fi
    sudo chmod -R 0777 $GAZOO_OPT_PATH
    make_directory_if_not_exists $GAZOO_TESTBED_PATH "" 777
    make_directory_if_not_exists $GDM_PATH "" 777
    make_directory_if_not_exists $GDM_PATH/conf "" 777
    make_directory_if_not_exists $GDM_PATH/conf/backup "" 777
    make_directory_if_not_exists $GDM_PATH/log "" 777
    make_directory_if_not_exists $GDM_PATH/tty "" 777
    make_directory_if_not_exists $GDM_PATH/detok "" 777
    make_directory_if_not_exists $GDM_PATH/bin "" 777
}


print_user_info_and_exit()
{
    local retval="$1"
    if [ $retval -ne 0 ]; then
        echo "Installation failed (exit $retval)"
    fi
    return $retval
}


# Check the lsb-release file for some variables that tell us what OS we're on.
if [ -f /etc/lsb-release ]; then
    . /etc/lsb-release
else
    DISTRIB_ID=$(uname)
fi
# DISTRIB_ID is loaded into the env by sourcing /etc/lsb-release
case "$DISTRIB_ID" in
    Debian ) install_for_debian ;;
    Ubuntu ) install_for_ubuntu ;;
    Linux ) install_for_debian ;;
    Darwin ) install_for_mac ;;
    *      ) install_unsupported "/etc/lsb-release $DISTRIB_ID says you are on an unsupported OS" ;;
esac

retval=$?

echo ""
echo "Be sure to read the documentation for further setup:"
echo "https://github.com/google/gazoo-device/README.md"
echo ""
echo "Install done (exit $retval)"
exit $retval
