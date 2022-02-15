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

# This script contains common functions shared by GDM installer scripts. To use
# this add a symlink to this file in your installer and then add the following
# line to your installers setup.sh/cleanup.sh:
# source ./functions.sh


# Remove directory if it exists and is a directory
#
# Args:
#     $1 - directory to remove
#
# Returns:
#     Return value from rm command or 0 if directory didn't exist
cleanup_directory_if_exists()
{
    local directory="$1"
    if [ -d "$directory" ]; then
        echo "Cleanup directory: $directory"
        rm -rf "$directory"
    fi
}


# Remove file if it exists and is a file
#
# Args:
#     $1 - file to remove
#
# Returns:
#     Return value from rm command or 0 if file didn't exist
cleanup_file_if_exists()
{
    local file="$1"
    if [ -f "$file" ]; then
        echo "Cleanup file: $file"
        rm -f "$file"
    fi
}


# Remove symlink if it exists and is of type symlink
#
# Args:
#     $1 - symlink to remove if it exists
#
# Returns:
#     Return value from rm command or 0 if symlink didn't exist
cleanup_symlink_if_exists()
{
    local link="$1"
    if [ -L "$link" ]; then
        echo "Cleanup installed symlink: $link"
        rm -f "$link"
    fi
}


# Remove each udev rule file found in source path at udev destination path.
#
# Note: The optional udev destination path should not include the "rules.d"
# portion of the path. If the udev destination path is not specified then the
# /etc/udev path will be used instead. If a udev rule was removed then the udev
# admin control program will be told to reload all rules and the udev daemon
# will be restarted.
#
# Args:
#     $1 - udev rule source path
#     $2 - (optional) udev destination path
#
# Returns:
#     Returns 0
cleanup_udev_rules()
{
    local reload_udev_rules=0
    local udev_src_path="$1"
    local udev_dst_path="$2"

    if [ -z "$udev_dst_path" ]; then
        udev_dst_path=/etc/udev
    fi

    echo "Verifying udev rules are uninstalled:"
    for file in $udev_src_path/*; do
        if [ -e "$udev_dst_path/$file" ]; then
            echo "Cleanup installed udev rule: $file"
            sudo rm "$udev_dst_path/$file"
            reload_udev_rules=1
        fi
    done
    if [ $reload_udev_rules -eq 1 ]; then
        reload_udev
    fi
    echo ""
}


# Copies source file to destination path and optionally changes file group
# owner and permissions.
#
# Args:
#     $1 - source file path to be copied
#     $2 - destination file path to copy file to
#     $3 - (optional) file permission to change destination file to
#     $4 - (optional) group to change file ownership to

#
# Returns:
#     Return value of last operation performed (e.g. chmod, chgrp, or cp if no
#     optional arguments were specified).
copy_file_if_not_exist()
{
    local src_file="$1"
    local dst_file="$2"
    local permissions="$3"
    local group_owner="$4"

    if [ ! -e "$dst_file" ]; then
        echo "Copying file $src_file to $dst_file"
        cp "$src_file" "$dst_file"
    fi
    if [ -n "$permissions" ]; then
        chmod "$permissions" "$dst_file"
    fi
    if [ -n "$group_owner" ]; then
        chgrp "$group_owner" "$dst_file"
    fi
}


# Exit with message specified (written to stderr) if result is non-zero.
#
# Example:
# exit_if_non_zero $? "Unable to install package foo" 25
# echo $?
# 25
#
# Args:
#     $1 - result to test if non-zero
#     $2 - message to write to stderr if result provided is non-zero
#     $3 - (optional) exit return value to use instead
#
# Returns:
#     Returns 0 if result is zero otherwise exit 1 is called
exit_if_non_zero()
{
    local result="$1"
    local msg="$2"
    local return_value="$3"
    if [ -z "$return_value" ]; then
        return_value=1
    fi
    if [ "$result" -ne 0 ]; then
        echo "$msg" 1>&2
        exit $return_value
    fi
}


# Installs each udev rule file found in source path at udev destination path.
#
# Note: If the udev rule file in the source path is different than the udev
# rule at the destination path then the udev rule will be copied again. The
# optional udev destination path should not include the "rules.d" portion of
# the path. If the udev destination path is not specified then the /etc/udev
# path will be used instead. If a udev rule was installed then the udev admin
# control program will be told to reload all rules and the udev daemon will be
# restarted.
#
# Args:
#     $1 - udev rule source path
#     $2 - (optional) udev destination path
#
# Returns:
#     Returns 0
install_udev_rules()
{
    local reload_udev_rules=0
    local udev_src_path="$1"
    local udev_dst_path="$2"

    if [ -z "$udev_dst_path" ]; then
        udev_dst_path=/etc/udev
    fi

    echo "Verifying udev rules are installed:"
    for file in $udev_src_path/*; do
        if [ ! -e "$udev_dst_path/$file" ]; then
            echo "Installing udev rule: $file"
            sudo cp "$file" "$udev_dst_path/$file"
            sudo chmod 644 "$udev_dst_path/$file"
            reload_udev_rules=1
        else
            if ! cmp -s "$file" "$udev_dst_path/$file"; then
                echo "Reinstalling udev rule: $file"
                sudo cp "$file" "$udev_dst_path/$file"
                sudo chmod 644 "$udev_dst_path/$file"
                reload_udev_rules=1
            fi
        fi
    done
    if [ $reload_udev_rules -eq 1 ]; then
        reload_udev
    fi
    echo ""
}


# Make directory path with owner, permissions, and ACL if it doesn't already
# exist.
#
# Note: The full directory path will be created in the process but only the
# final directories owner and permissions will be changed if the optional
# parameters are specified. Group ownership and permissions will always be
# applied regardless if the directory already exists.
#
#
# Args:
#     $1 - directory to be created
#     $2 - (optional) permissions to use for directory
#     $3 - (optional) group owner to change directory to
#     $4 - (optional) ACL permission to assign to directory
#
# Returns:
#     Return value of last operation performed (e.g. setfacl, chmod, chgrp, or
#     mkdir if no optional arguments were specified).
make_directory_if_not_exists()
{
    local directory="$1"
    local permissions="$2"
    local group_owner="$3"
    local acl="$4"
    if [ ! -d "$directory" ]; then
        echo "Creating directory $directory"
        mkdir -p "$directory"
    fi
    if [ -n "$permissions" ]; then
        echo "Changing permissions on $directory to $permissions"
        chmod "$permissions" "$directory"
    fi
    if [ -n "$group_owner" ]; then
        echo "Changing owner on $directory to $group_owner"
        chgrp "$group_owner" "$directory"
    fi
    if [ -n "$acl" ]; then
        echo "Setting ACL permissions on $directory to $acl"
        setfacl -R -dm "$acl" "$directory"
        setfacl -R -m "$acl" "$directory"
    fi
}


# Creates symlink from source to destination if it doesn't exist
#
# Args:
#     $1 - source symlink location
#     $2 - destination for symlink
#
# Returns:
#     Return value from ln command or 0 if symlink already exists
make_link_if_not_exists()
{
    local link="$1"
    local destination="$2"

    if [ ! -L "$link" ]; then
        echo "Installing symlink $link to $destination"
        ln -s "$destination" "$link"
    fi
}


# Reloads udev daemon after rules have changed
#
# Returns:
#    Return value from restarting udev daemon
reload_udev()
{
    local SYSTEMCTL
    SYSTEMCTL=$(which systemctl)

    if [ -e "$SYSTEMCTL" ]; then
        echo "Reloading systemd daemons"
        sudo "$SYSTEMCTL" daemon-reload
    fi
    echo "Reloading udev rules"
    sudo udevadm control --reload-rules
    sudo udevadm trigger --action=change
    sudo /etc/init.d/udev restart
}
