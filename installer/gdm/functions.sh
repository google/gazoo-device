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

# This script contains common functions shared by GDM installers. To use
# this add a symlink to this file in your installer and then add the following
# line to your installers setup.sh/cleanup.sh:
# source ./functions.sh


# Identify if the apt package specified is installed.
#
# Args:
#     $1 - apt package name to confirm is installed
# Returns:
#     0 if installed, 1 if missing
apt_package_found()
{
    local package="$1"
    # See the following SO question (especially the comments that dpkg-query
    # return codes can be unreliable and its better to grep the output instead):
    # https://stackoverflow.com/questions/1298066/check-if-a-package-is-installed-and-then-install-it-if-its-not
    if dpkg-query -W -f='${Status}' $package 2>/dev/null | grep -q "ok installed"; then
        return 0
    else
        return 1
    fi
}


# Perform apt-get command for package(s) specified, waiting if necessary.
#
# Args:
#     $1 - apt-get command to perform
#     $2 - (optional) package(s) to perform command for
#
# Returns:
#     Return value from apt-get command execution
apt_get_command()
{
    local command="$1"
    local packages="$2"
    # Code below from the following website:
    # https://askubuntu.com/questions/132059/how-to-make-a-package-manager-wait-if-another-instance-of-apt-is-running
    i=0
    tput sc
    while fuser /var/lib/dpkg/lock >/dev/null 2>&1; do
        case $(($i % 4)) in
            0 ) j="-" ;;
            1 ) j="\\" ;;
            2 ) j="|" ;;
            3 ) j="/" ;;
        esac
        tput rc
        echo -en "\r[$j] Waiting for other software managers to finish..."
        sleep 0.5
        ((i=i+1))
    done
    apt-get $command $packages
}


# Check user specified is a member of one of the valid groups specified.
#
# Note: If the username is not a member of one of the valid groups provided
# then exit 1 will be called after printing an error message.
#
# Args:
#     $1 - username to check group membership of
#     $2 - list of valid groups the user must be a member of
#
# Returns:
#     Returns 0 if success or calls exit 1 if not.
check_user_access()
{
    local username="$1"
    local valid_groups="$2"
    verify_user_is_in_valid_group "$username" "$valid_groups"
    if [ $? -ne 0 ]; then
        echo "User '$username' must be a member of one of these groups:" 1>&2
        echo "$valid_groups" 1>&2
        exit 1
    fi
}


# Remove apt packages specified
#
# Args:
#     $1 - apt packages to be uninstalled
#
# Returns:
#     Return value from apt-get command or 0 if no packages were uninstalled
cleanup_apt_packages()
{
    local these_packages=""
    local packages="$1"
    local result=0
    echo "Verifying apt packages uninstalled:"
    echo "$packages"
    for package in $packages; do
        if apt_package_found $package; then
            these_packages="$package $these_packages"
        fi
    done
    if [ -n "$these_packages" ]; then
        echo "Cleanup installed apt packages:"
        echo "$these_packages"
        apt_get_command "remove -y" "$these_packages"
        result=$?
    fi
    echo ""
    return $result
}


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
    if [ -d $directory ]; then
        echo "Cleanup directory: $directory"
        rm -rf $directory
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
    if [ -f $file ]; then
        echo "Cleanup file: $file"
        rm -f $file
    fi
}


# Uninstall pip packages specified if they exist
#
# Note: If the path to the pip executable is not specified the following paths
# to the pip executable will be tested and used:
# /usr/local/bin/pip
# /usr/bin/pip
# pip
#
# Args:
#     $1 - pip packages to be uninstalled
#     $2 - (optional) path to pip executable
#
# Returns:
#     Returns value from pip uninstall command or 0 if no pip packages
#     uninstalled.
cleanup_pip_packages()
{
    local these_packages=""
    local packages="$1"
    local pip="$2"
    local result=0
    if [ -z "$pip" ]; then
        if [ -x "/usr/local/bin/pip" ]; then
            pip=/usr/local/bin/pip
        elif [ -x "/usr/bin/pip" ]; then
            pip=/usr/bin/pip
        else
            pip="pip"
        fi
    fi

    echo "Verifying pip packages uninstalled:"
    echo "$packages"
    for package in $packages; do
        if pip_package_found $package $pip; then
            these_packages="$package $these_packages"
        fi
    done
    if [ -n "$these_packages" ]; then
        echo "Cleanup installed pip packages:"
        echo "$these_packages"
        $pip uninstall -y $these_packages
        result=$?
    fi
    echo ""
    return $result
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
    if [ -L $link ]; then
        echo "Cleanup installed symlink: $link"
        rm -f $link
    fi
}


# Remove udev daemon config at /etc/systemd/system path.
#
# Note: This removes the udev daemon service configuration file that was copied
# to the /etc/systemd/system destination path restoring the offending
# MountFlags=slave option that prevented the USB mount udev rule from working.
#
# Returns:
#     Returns 0 if udevd config was removed, 1 otherwise
cleanup_udev_config()
{
    local udevd_config=systemd-udevd.service
    local udevd_destination=/etc/systemd/system/$udevd_config
    if [ -e "$udevd_destination" ]; then
        echo "Cleanup installed udevd config: $udevd_destination"
        rm -f $udevd_destination
        return 0
    fi
    return 1
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
        if [ -e $udev_dst_path/$file ]; then
            echo "Cleanup installed udev rule: $file"
            rm $udev_dst_path/$file
            reload_udev_rules=1
        fi
    done
    if cleanup_udev_config; then
        reload_udev_rules=1
    fi
    if [ $reload_udev_rules -eq 1 ]; then
        reload_udev
    fi
    echo ""
}


# Copies source directory to destination directory and optionally changes
# destination directory owner and permissions.
#
# Args:
#     $1 - source directory to be copied
#     $2 - destination directory to copy to
#     $2 - (optional) group owner to change directory to
#     $4 - (optional) permission to change directory to
#     $5 - (optional) ACL permission to assign to directory
#
# Returns:
#     Return value of last operation performed (e.g. chmod, chgrp, or cp if no
#     optional arguments were specified).
copy_directory()
{
    local src_dir="$1"
    local dst_dir="$2"
    local group_owner="$3"
    local permissions="$4"
    local acl="$5"

    echo "Copying directory $src_dir to $dst_dir:"
    cp -r "$src_dir" "$dst_dir"

    # Enforce group owner and directory permissions
    if [[ -n "$group_owner" ]]; then
        chgrp --recursive $group_owner $dst_dir
        if [[ -n "$permissions" ]]; then
            chmod --recursive $permissions $dst_dir
            if [[ -n "$acl" ]]; then
                setfacl -R -dm $acl $dst_dir
                setfacl -R -m $acl $dst_dir
            fi
        fi
    fi
}


# Copies source directory to destination directory and optionally changes
# destination directory owner and permissions.
#
# Note: Group ownership and permissions will always be applied regardless if
# the directory already exists.
#
# Args:
#     $1 - source directory to be copied
#     $2 - destination directory to copy to
#     $2 - (optional) group owner to change directory to
#     $4 - (optional) permission to change directory to
#     $5 - (optional) ACL permission to assign to directory
#
# Returns:
#     Return value of last operation performed (e.g. chmod, chgrp, or cp if no
#     optional arguments were specified).
copy_directory_if_not_exist()
{
    local src_dir="$1"
    local dst_dir="$2"
    local group_owner="$3"
    local permissions="$4"
    local acl="$5"

    if [ ! -d $dst_dir ]; then
        echo "Copying directory $src_dir to $dst_dir:"
        cp -r $src_dir $dst_dir
    fi
    # Enforce group owner and directory permissions
    if [ -n "$group_owner" ]; then
        chgrp $group_owner $dst_dir
        if [ -n "$permissions" ]; then
            chmod $permissions $dst_dir
            if [ -n "$acl" ]; then
                setfacl -R -dm $acl $dst_dir
                setfacl -R -m $acl $dst_dir
            fi
        fi
    fi
}


# Copies source file to destination path if changed and optionally changes
# file group owner and permissions.
#
# Args:
#     $1 - source file path to be copied
#     $2 - destination file path to copy file to
#     $3 - (optional) group to change file ownership to
#     $4 - (optional) file permission to change destination file to
#
# Returns:
#     Return value of last operation performed (e.g. chmod, chgrp, or cp if no
#     optional arguments were specified).
copy_file_if_changed()
{
    local src_file="$1"
    local dst_file="$2"
    local group_owner="$3"
    local permissions="$4"

    if [ ! -e $dst_file ]; then
        echo "Copying file $src_file to $dst_file:"
        cp $src_file $dst_file
    else
        if ! cmp -s $src_file $dst_file; then
            echo "Reinstalling file $src_file to $dst_file:"
            cp $src_file $dst_file
        fi
    fi
    if [ -e $dst_file ]; then
        if [ -n "$group_owner" ]; then
            chgrp $group_owner $dst_file
        fi
        if [ -n "$permissions" ]; then
            chmod $permissions $dst_file
        fi
    fi
}


# Copies source file to destination path and optionally changes file group
# owner and permissions.
#
# Args:
#     $1 - source file path to be copied
#     $2 - destination file path to copy file to
#     $3 - (optional) group to change file ownership to
#     $4 - (optional) file permission to change destination file to
#
# Returns:
#     Return value of last operation performed (e.g. chmod, chgrp, or cp if no
#     optional arguments were specified).
copy_file_if_not_exist()
{
    local src_file="$1"
    local dst_file="$2"
    local group_owner="$3"
    local permissions="$4"

    if [ ! -e $dst_file ]; then
        echo "Copying file $src_file to $dst_file:"
        cp $src_file $dst_file
    fi
    if [ -e $dst_file ]; then
        if [ -n "$group_owner" ]; then
            chgrp $group_owner $dst_file
            if [ -n "$permissions" ]; then
                chmod $permissions $dst_file
            fi
        fi
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
    if [ $result -ne 0 ]; then
        echo "$msg" 1>&2
        exit $return_value
    fi
}


# Install apt packages specified
#
# Args:
#     $1 - apt packages to be installed
#
# Returns:
#     Returns 0 if no packages were installed or exits with message if install
#     failed.
install_apt_packages()
{
    local these_packages=""
    local packages="$1"
    echo "Verifying apt packages are installed:"
    echo "$packages"
    for package in $packages; do
        if ! apt_package_found $package; then
            these_packages="$package $these_packages"
        fi
    done
    if [ -n "$these_packages" ]; then
        echo "Installing missing apt packages:"
        echo "$these_packages"
        apt_get_command "install -y" "$these_packages"
        exit_if_non_zero $? "Failed to install apt packages: $these_packages"
    fi
    echo ""
}


# Install pip packages specified if they exist
#
# Note: If the path to the pip executable is not specified the following paths
# to the pip executable will be tested and used:
# /usr/local/bin/pip
# /usr/bin/pip
# pip
#
# Args:
#     $1 - pip packages to be installed
#     $2 - (optional) path to pip executable
#
# Returns:
#     Returns 0 if no packages were installed or exits with message if install
#     failed.
install_pip_packages()
{
    local these_packages=""
    local packages="$1"
    local pip="$2"
    if [ -z "$pip" ]; then
        if [ -x "/usr/local/bin/pip3" ]; then
            pip=/usr/local/bin/pip3
        elif [ -x "/usr/bin/pip3" ]; then
            pip=/usr/bin/pip3
        else
            pip="pip3"
        fi
    fi

    echo "Verifying pip packages are installed:"
    echo "$packages"
    for package in $packages; do
        if ! pip_package_found $package $pip; then
            these_packages="$package $these_packages"
        fi
    done
    if [ -n "$these_packages" ]; then
        echo "Installing missing pip packages:"
        echo "$these_packages"
        $pip install $these_packages
        exit_if_non_zero $? "Failed to install pip packages: $these_packages"
    fi
    echo ""
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
        if [ ! -e $udev_dst_path/$file ]; then
            echo "Installing udev rule: $file"
            cp $file $udev_dst_path/$file
            chmod 644 $udev_dst_path/$file
            reload_udev_rules=1
        else
            if ! cmp -s $file $udev_dst_path/$file; then
                echo "Reinstalling udev rule: $file"
                cp $file $udev_dst_path/$file
                chmod 644 $udev_dst_path/$file
                reload_udev_rules=1
            fi
        fi
    done
    if [ $reload_udev_rules -eq 1 ]; then
        reload_udev
    fi
    echo ""
}


# Identify if group specified is a group in the list of valid groups provided.
#
# Args:
#     $1 - user group to check
#     $2 - list of valid groups
#
# Returns:
#     0 - if user group is in the list of valid groups
#     1 - if user group is NOT in the list of valid groups
is_group_in_valid_group()
{
    local user_group="$1"
    local valid_groups="$2"
    for valid_group in $valid_groups; do
        if [ $user_group == $valid_group ]; then
            return 0
        fi
    done
    return 1
}


# Makes an empty file at destination path specified and optionally changes file
# group owner and permissions.
#
# Note: Group ownership and permissions will always be applied regardless if
# the file already exists.
#
# Args:
#     $1 - destination file path to make if not exists
#     $2 - (optional) group to change file ownership to
#     $3 - (optional) file permission to change destination file to
#
# Returns:
#     Return value of last operation performed (e.g. chmod, chgrp, or cp if no
#     optional arguments were specified).
make_file_if_not_exist()
{
    local dst_file="$1"
    local group_owner="$2"
    local permissions="$3"

    if [ ! -e $dst_file ]; then
        echo "Creating file $dst_file:"
        touch $dst_file
    fi
    # Enforce group owner and directory permissions
    if [ -n "$group_owner" ]; then
        chgrp $group_owner $dst_file
        if [ -n "$permissions" ]; then
            chmod $permissions $dst_file
        fi
    fi
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
#     $2 - (optional) group owner to change directory to
#     $3 - (optional) permissions to use for directory
#     $4 - (optional) ACL permission to assign to directory
#
# Returns:
#     Return value of last operation performed (e.g. setfacl, chmod, chgrp, or
#     mkdir if no optional arguments were specified).
make_directory_if_not_exists()
{
    local directory="$1"
    local group_owner="$2"
    local permissions="$3"
    local acl="$4"
    if [ ! -d $directory ]; then
        echo "Creating directory $directory:"
        mkdir -p $directory
    fi
    # Enforce group owner and directory permissions
    if [ -n "$group_owner" ]; then
        chgrp $group_owner $directory
    fi
    if [ -n "$permissions" ]; then
        echo "Changing permissions on $directory to $permissions"
        chmod $permissions $directory
    fi
    if [ -n "$acl" ]; then
        setfacl -R -dm $acl $directory
        setfacl -R -m $acl $directory
    fi

}


# Make group if it doesn't already exist
#
# Args:
#     $1 - group to create if it doesn't exist
#
# Returns:
#     Returns value returned from groupadd if group was added or 0 if group
#     already exists.
make_group_if_not_exists()
{
    local new_group="$1"
    if ! getent group $new_group > /dev/null; then
        echo "Creating group $new_group:"
        groupadd $new_group
    fi
}


# Make all groups if they don't already exist
#
# Args:
#     $1 - list of groups to create if they don't exist
#
# Returns:
#     Returns 0
make_groups_if_not_exist()
{
    local new_groups="$1"
    for new_group in $new_groups; do
        make_group_if_not_exists $new_group
    done
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

    if [ ! -L $link ]; then
        echo "Installing symlink $link to $destination"
        ln -s $destination $link
    fi
}


# Move directory from original path to new path if it exists
#
# Note: If a directory exists at the new path specified it will be removed
# first before the move occurs.
#
# Args:
#     $1 - original path to move directory from
#     $2 - new path to move directory to
#
# Returns:
#     Return value from mv command or 0 if no move occurred.
move_directory_if_exists()
{
    local old_path="$1"
    local new_path="$2"
    if [ -d $old_path ]; then
        echo "Moving $old_path to $new_path"
        rm -rf $new_path
        mv $old_path $new_path
    fi
}


# Make python3 virtual environment at the destination path provided using the
# username specified if it doesn't already exist
#
# Note: If a virtual environment exists at the destination path but the
# python version is python2, then it will be removed and a new virtual
# environment will be created in python3.
# If the optional path to virtualenv executable is not specified the
# first of the following executable paths will be used:
# /usr/local/bin/virtualenv
# /usr/bin/virtualenv
# virtualenv
#
# Args:
#     $1 - destination path for virtual environment
#
# Returns:
#     Returns 0 if virtual environment was created or exits with message if
#     virtual environment creation failed.
make_virtual_environment_if_not_exists()
{
    local destination="$1"

    echo "Verifying GDM virtual environment exists at:"
    echo "$destination"
    if [ ! -x $destination/bin/python ]; then
        echo "It doesn't exist. Installing virtual environment:"
        python3 -m virtualenv $destination
        exit_if_non_zero $? "Failed to create virtual environment at: $destination"
    else
        # Use regex matching to check existing virtual environment's python version
        # Remove virtual environment if version is python2 and re-create in python3
        python_version=$($destination/bin/python -V 2>&1)
        is_python_3=$(echo $python_version | sed -n "/Python 3.*.*/p")
        if [ -z "$is_python_3" ]; then
            echo "It exists but version is:"
            echo "$python_version"
            echo "Removing virtual environment and re-creating in Python3."
            rm -rf $destination
            exit_if_non_zero $? "Failed to remove Python2 virtual environment at: $destination"
            python3 -m virtualenv $destination
            exit_if_non_zero $? "Failed to create Python3 virtual environment at: $destination"
        fi
    fi
    echo ""
}


# Identify if pip package is installed.
#
# Args:
#     $1 - package to determine is installed
#     $2 - path to pip executable to use for test
#
# Returns:
#     0 - if pip package is installed
#     1 - if pip package is NOT installed
pip_package_found()
{
    local package="$1"
    local pip="$2"
    # Use pip list instead of pip show since older versions of pip don't
    # return 1 when the package is missing for pip show
    if $pip list 2>&1 | grep "^$package " > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}


# Reloads udev daemon after rules have changed
#
# Returns:
#    Return value from restarting udev daemon
reload_udev()
{
    local SYSTEMCTL=$(which systemctl)

    if [ -e "$SYSTEMCTL" ]; then
        echo "Reloading systemd daemons"
        $SYSTEMCTL daemon-reload
    fi
    echo "Reloading udev rules"
    udevadm control --reload-rules
    udevadm trigger --action=change
    /etc/init.d/udev restart
}


# Rerun self using sudo
#
# Note: This method will call exit 0 if sudo run of this script succeeded and
# exit with the same return code from sudo if the script returned a non-zero
# result. The umask will be set to 0022 when running this script to prevent
# restricted file permissions for files created when running the script under
# sudo which inherits the current user umask (typically 0077).
rerun_self_using_sudo()
{
    if [ $(id -u) -ne 0 ]; then
        echo "Rerunning $0 under sudo (please enter password or press CTRL-C)" 1>&2
        sudo ./$0
        result=$?
        if [ $result -ne 0 ]; then
            echo "Script $0 failed with return result: $result" 1>&2
        fi
        exit $result
    fi
    umask 0022
}


# Identify if user is a member of one of the valid groups provided.
#
# Args:
#     $1 - username to check for membership
#     $2 - list of valid groups to check for
#
# Returns:
#     0 - if user is a member of one of the valid groups provided
#     1 - if user is NOT a member of one of the valid groups provided
verify_user_is_in_valid_group()
{
    local username="$1"
    local valid_groups="$2"
    for group in $(groups $username); do
        if is_group_in_valid_group $group "$valid_groups"; then
            return 0
        fi
    done
    return 1
}
