# Copyright 2016 Google Inc.
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import third_party.pyperclip as clipboard


class Clipboard():

    def __init__(self):
        self._clipList = []
        self.setOsHandlers(clipboard.copy, clipboard.paste)

    def copy(self, text):
        """Add text onto clipList. Empty |text| is not stored."""
        if text and len(text):
            self._clipList.append(text)
            if self._copy:
                self._copy(text)

    def paste(self, clipIndex=None):
        """Fetch top of clipList; or clip at index |clipIndex|. The |clipIndex|
        will wrap around if it's larger than the clipList length."""
        if clipIndex is None:
            osClip = self._paste and self._paste()
            if osClip:
                return osClip
            # Get the top of the clipList instead.
            clipIndex = -1
        if len(self._clipList):
            return self._clipList[clipIndex % len(self._clipList)]
        return None

    def setOsHandlers(self, copy, paste):
        self._copy = copy
        self._paste = paste
