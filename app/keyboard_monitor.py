# Copyright 2019 Google Inc.
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

import app.log
from pynput import keyboard


class KeyboardMonitor:
    """
  This class is used to listen to the user's inputs in order to detect any
  modifier keys being used. Due to limitations of this library, errors may occur
  when running over ssh, since an X server is required. This will also not be
  able to detect most keys on macOS unless run as root. See more details at
  https://pynput.readthedocs.io/en/latest/limitations.html.
  """

    def __init__(self):
        self.listener = keyboard.Listener(
            on_press=self.__onPress, on_release=self.__onRelease)
        self.keys_pressed = set()
        self.keys_to_check = {keyboard.Key.ctrl, keyboard.Key.backspace}

    def __onPress(self, key):
        if key in self.keys_to_check:
            self.keys_pressed.add(key)
            app.log.info(key, "has been inserted into KeyboardMonitor.")

    def __onRelease(self, key):
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)
            app.log.info(key, "has been released from KeyboardMonitor.")

    def start(self):
        self.listener.start()

    def stop(self):
        self.listener.stop()

    def getKeysPressed(self):
        return self.keys_pressed
