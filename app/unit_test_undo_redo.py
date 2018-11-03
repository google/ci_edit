# -*- coding: latin-1 -*-

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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses
import os
import sys

from app.curses_util import *
import app.ci_program
import app.fake_curses_testing
import app.prefs


kTestFile = u'#undo_redo_test_file_with_unlikely_file_name~'


class UndoRedoTestCases(app.fake_curses_testing.FakeCursesTestCase):
  def setUp(self):
    self.longMessage = True
    if os.path.isfile(kTestFile):
      os.unlink(kTestFile)
    self.assertFalse(os.path.isfile(kTestFile))
    app.fake_curses_testing.FakeCursesTestCase.setUp(self)

  def test_undo_bracketed_paste(self):
    #self.setMovieMode(True)
    self.runWithTestFile(kTestFile, [
        self.displayCheck(2, 7, [u"      "]),
        curses.ascii.ESC, app.curses_util.BRACKETED_PASTE_BEGIN,
        u'a', u'b', u'c',
        curses.ascii.ESC, app.curses_util.BRACKETED_PASTE_END,
        self.displayCheck(2, 7, [u'abc ']),
        CTRL_Z,
        self.displayCheck(2, 7, [u"                "]),
        CTRL_Q])

  def test_basic_undo(self):
    #self.setMovieMode(True)
    self.runWithTestFile(kTestFile, [
        self.displayCheck(2, 7, [u"      "]), self.writeText(u"sand"),
        self.displayCheck(2, 7, [u"sand "]),
        KEY_BACKSPACE1, u"s", self.displayCheck(2, 7, [u"sans "]),
        CTRL_Z, self.displayCheck(2, 7, [u"san "]),
        CTRL_Z, self.displayCheck(2, 7, [u"sand "]),
        CTRL_Z, self.displayCheck(2, 7, [u"     "]),
        # Don't go past first change.
        CTRL_Z, self.displayCheck(2, 7, [u"     "]),
        CTRL_Y, self.displayCheck(2, 7, [u"sand "]),
        CTRL_Y, self.displayCheck(2, 7, [u"san "]),
        CTRL_Y, self.displayCheck(2, 7, [u"sans "]),
        # Don't go past last change.
        CTRL_Y, self.displayCheck(2, 7, [u"sans "]),
        CTRL_Z, self.displayCheck(2, 7, [u"san "]),
        CTRL_Z, self.displayCheck(2, 7, [u"sand "]),
        CTRL_Z, self.displayCheck(2, 7, [u"     "]),
        CTRL_Q])

  def test_undo_words(self):
    #self.setMovieMode(True)
    self.runWithTestFile(kTestFile, [
        self.displayCheck(2, 7, [u"      "]),
        self.writeText(u"one two "), self.displayCheck(2, 7, [u"one two "]),
        self.writeText(u"three four "),
        self.displayCheck(2, 7, [u"one two three four", "     "]),
        KEY_SHIFT_LEFT, KEY_SHIFT_LEFT, KEY_SHIFT_LEFT, KEY_SHIFT_LEFT,
        KEY_SHIFT_LEFT, KEY_SHIFT_LEFT, KEY_SHIFT_LEFT, KEY_SHIFT_LEFT,
        KEY_SHIFT_LEFT, KEY_SHIFT_LEFT, KEY_SHIFT_LEFT, KEY_SHIFT_LEFT,
        KEY_SHIFT_LEFT, KEY_SHIFT_LEFT, KEY_SHIFT_LEFT,
        self.writeText(u"five "),
        self.displayCheck(2, 7, [u"one five"]),
        CTRL_Z, self.displayCheck(2, 7, [u"one two three four        "]),
        CTRL_Z, self.displayCheck(2, 7, [u"one two        "]),
        CTRL_Y, self.displayCheck(2, 7, [u"one two three four        "]),
        CTRL_Y, self.displayCheck(2, 7, [u"one five        "]),
        CTRL_Q, u"n"])
