#!/usr/bin/env bash
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Install File Description:
#
# This is an init (install) script that first copies or updates the current
# directory to the path: /opt/[$PWD], which will be your installation
# Then, a sym link is created in the directory /usr/local/bin
# This directory is generally designated for user programs not managed
# by the distribution package manager.
# The link references the execution command in the install directory
# The default command will be `we`, but this can be customized to user
# preference

if [ "$(id -u)" != "0" ]; then
    echo "Usage: sudo ./install.sh (please use root privileges)"
    [[ "$0" = "$BASH_SOURCE" ]] && exit 1 || return 1
fi

THE_CWD="$(pwd)"
APP_DIR="$(pwd | grep -o '[^/]*$')"
BIN_PATH="/usr/local/bin"
APP_PATH="/opt"

echo "* *********************************************************** *"
echo "*                                                             *"
echo "*   installation steps:                                       *"
echo "*                                                             *"
echo "*   (1) copies (or updates) current directory to the path:    *"
echo "*       '/opt/[CURRENT DIRECTORY]' (likely '/opt/ci_edit')    *"
echo "*                                                             *"
echo "*   (2) creates (or updates) the execution command:           *"
echo "*       (a) this will be a sym link to the install directory  *"
echo "*           executable 'ci.py' copied to the path:            *"
echo "*           '/usr/local/bin' --> generally designated for     *"
echo "*           user programs.                                    *"
echo "*       (b) The command will be given the default:            *"
echo "*           command name of: 'we'                             *"
echo "*       (c) If you would like to specify the command name,    *"
echo "*           you will be prompted for an input name.           *"
echo "*           NOTE: Be sure to specify a UNIQUE name            *"
echo "*                                                             *"
echo "* *********************************************************** *"
echo ""
echo "Type 'y' or 'Y' to continue, or anything else to quit"
read -p "Continue ? " -n 1 -r INSTALL_REPLY
echo ""
if [[ ! "$INSTALL_REPLY" =~ ^[Yy]$ ]]; then
    echo "...Goodbye"
    [[ "$0" = "$BASH_SOURCE" ]] && exit 1 || return 1
else
    echo "To customize the ci_edit command for your CLI, please type:"
    echo "'y' or 'Y', or anything else to use the default command 'we'"
    read -p "Customize Command ? " -n 1 -r CMD_REPLY
    echo ""
    if [[ "$CMD_REPLY" =~ ^[Yy]$ ]]; then
	read -p "Your Custom Unique command: " -r THE_CMD
    else
	THE_CMD="we"
    fi
    echo "...installing"
    sleep 1
fi

rm -rf "${APP_PATH}/${APP_DIR}"
cp -Rv "$THE_CWD" "${APP_PATH}/${APP_DIR}"
ln -sf "${APP_PATH}/${APP_DIR}/ci.py" "${BIN_PATH}/${THE_CMD}"
echo "...Success! Enjoy."
