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
# This is an init (install) script that first copies or updates the editor
# code to the path: /opt/[$PWD], which will be your installation.
# Then, a symbolic link (sym-link) is created in the directory /usr/local/bin.
# This directory is generally designated for user programs not managed
# by the distribution package manager.
# The link references the execution command in the install directory.
# The default command will be `we`, but this can be customized to user
# preference during the install.

if [ "$(id -u)" != "0" ]; then
    echo "Usage: sudo ./install.sh (please use root privileges)"
    [[ "$0" = "$BASH_SOURCE" ]] && exit 1 || return 1
fi

# Split path to this install script into an array.
IFS='/' SRC_PATH=($0)
# Remove this file name.
unset SRC_PATH[-1]
# Grab the directory name.
APP_DIR="${SRC_PATH[-1]}"
# Joint path back together.
SRC_PATH="${SRC_PATH[*]}"
BIN_PATH="/usr/local/bin"
APP_PATH="/opt"
INSTALL_DIR="${APP_PATH}/${APP_DIR}"

echo "* *********************************************************** *"
echo "*                                                             *"
echo "*   installation steps:                                       *"
echo "*                                                             *"
echo "*   (1) copies (or updates) ci_edit directory to the path:    *"
echo "*       '$INSTALL_DIR'"
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

# Go over board to avoid "rm -rf /"; e.g. APP_PATH is set above, testing anyway.
if [[ -z "$APP_PATH" || -z "${APP_DIR}" || "$INSTALL_DIR" -eq "/" ]]; then
  echo "Something is incorrect about the install directory. Exiting."
  exit -1
fi
# Yes, this is redundant with the above. User safety is top priority.
if [[ -n "$APP_PATH" && -n "${APP_DIR}" && "$INSTALL_DIR" -ne "/" ]]; then
  rm -rf "$INSTALL_DIR"
fi

cp -Rv "$SRC_PATH" "$INSTALL_DIR"
# Make installed directories usable by all users.
find "$INSTALL_DIR" -type d -exec chmod +rx {} \;
# Make installed files readable by all users.
chmod -R +r "$INSTALL_DIR"
# Allow all users to execute the editor.
chmod +rx "$INSTALL_DIR/ci.py"
ln -sf "${APP_PATH}/${APP_DIR}/ci.py" "${BIN_PATH}/${THE_CMD}"
echo "...Success! Enjoy."
