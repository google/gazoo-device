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


MAKESELF_VER="2.3.0"
MAKESELF_FILE="makeself-$MAKESELF_VER.run"
MAKESELF_DIR="makeself-$MAKESELF_VER"
MAKESELF_URL="https://github.com/megastep/makeself/releases/download/"
MAKESELF=./$MAKESELF_DIR/makeself.sh

get_makeself()
{
    if [ ! -d $MAKESELF_DIR ]; then
        echo "Downloading $MAKESELF_FILE"
        curl -fsSLO $MAKESELF_URL/release-$MAKESELF_VER/$MAKESELF_FILE
        /bin/sh $MAKESELF_FILE
        rm -f $MAKESELF_FILE
    fi
}

create_installer()
{
    local archive_dir="$1"
    local file_name="$2"
    local label="$3"
    local start_script="$4"
    local start_args="$5"
    $MAKESELF --tar-extra -h $archive_dir $file_name "$label" $start_script $start_args
}

create_gdm_scripts()
{
    # Retrieve script version
    local dir=gdm
    local version="$(perl -lne 'print $1 if /LAUNCHER_VERSION=([\d.]+)/' $dir/gdm)"
    local installer_title="Gazoo Device Manager Installer $version"
    local cleanup_title="Gazoo Device Manager Cleanup $version"

    # Build install script
    create_installer gdm gdm-install.sh "$installer_title" ./setup.sh

    # Build cleanup script
    create_installer gdm gdm-cleanup.sh "$cleanup_title" ./cleanup.sh
}

# Retrieve makeself and extract it locally
get_makeself

# Create GDM installer and cleanup scripts
create_gdm_scripts
