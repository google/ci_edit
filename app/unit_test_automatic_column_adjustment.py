# Copyright 2018 Google Inc.
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

import os
import sys

from app.curses_util import *
import app.fake_curses_testing


kTestFile = u'#automatic_column_adjustment_test_file_with_unlikely_file_name~'


class AutomaticColumnAdjustmentCases(app.fake_curses_testing.FakeCursesTestCase):
  def setUp(self):
    if os.path.isfile(kTestFile):
      os.unlink(kTestFile)
    self.assertFalse(os.path.isfile(kTestFile))
    app.fake_curses_testing.FakeCursesTestCase.setUp(self)

  def tearDown(self):
    app.fake_curses_testing.FakeCursesTestCase.tearDown(self)

  def test_column_adjustment_on_moving_by_one_line(self):
    # self.setMovieMode(True)
    self.runWithTestFile(kTestFile, [
        self.displayCheck(0, 0, [
            u" ci     .                               ",
            u"                                        ",
            u"     1                                  ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"New buffer         |    1, 1 |   0%,  0%",
            u"                                        "]),
        self.writeText(u"short line"), CTRL_J,
        self.writeText(u"super long line that should go past the screen"),
        CTRL_J,
        self.writeText(u"line that slightly goes off screen"),
        self.displayCheck(0, 0, [
            u" ci     *                               ",
            u"                                        ",
            u"     1 rt line                          ",
            u"     2 er long line that should go past ",
            u"     3 e that slightly goes off screen  ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                        3,35 |  66%,100%",
            u"                                        "]),
        KEY_UP, KEY_END, # Place cursor at the end of the second line.
        self.displayCheck(0, 0, [
            u" ci     *                               ",
            u"                                        ",
            u"     1                                  ",
            u"     2  that should go past the screen  ",
            u"     3 tly goes off screen              ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                        2,47 |  33%,100%",
            u"                                        "]),
        KEY_UP, # scrollCol should be set to 0 since line 1 fits on screen.
        self.displayCheck(0, 0, [
            u" ci     *                               ",
            u"                                        ",
            u"     1 short line                       ",
            u"     2 super long line that should go p ",
            u"     3 line that slightly goes off scre ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                        1,11 |   0%,100%",
            u"                                        "]),
        KEY_DOWN, # cursor should snap back to the end of the second line.
        self.displayCheck(0, 0, [
            u" ci     *                               ",
            u"                                        ",
            u"     1                                  ",
            u"     2  that should go past the screen  ",
            u"     3 tly goes off screen              ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                        2,47 |  33%,100%",
            u"                                        "]),
        KEY_DOWN, # scrollCol should not change since line 1 doesn't fit on screen.
        self.displayCheck(0, 0, [
            u" ci     *                               ",
            u"                                        ",
            u"     1                                  ",
            u"     2  that should go past the screen  ",
            u"     3 tly goes off screen              ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                        3,35 |  66%,100%",
            u"                                        "]),
        KEY_UP, # cursor moves back to original position.
        self.displayCheck(0, 0, [
            u" ci     *                               ",
            u"                                        ",
            u"     1                                  ",
            u"     2  that should go past the screen  ",
            u"     3 tly goes off screen              ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                        2,47 |  33%,100%",
            u"                                        "]),
         # Make line 3 fit on screen. This includes making room for the cursor.
        KEY_DOWN, KEY_BACKSPACE1, KEY_BACKSPACE1, KEY_BACKSPACE1,
        KEY_UP, KEY_DOWN, # Since line 3 now fits on screen, this should set scrollCol to 0.
        self.displayCheck(0, 0, [
            u" ci     *                               ",
            u"                                        ",
            u"     1 short line                       ",
            u"     2 super long line that should go p ",
            u"     3 line that slightly goes off scr  ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                                        ",
            u"                        3,32 |  66%,100%",
            u"                                        "]),
        CTRL_Q, u'n',
      ])

  def test_column_adjustment_on_moving_multiple_lines(self):
    """
    A test to check that the cursor column is stored properly and that
    after using a series of up/down arrow keys, when we end up back at the
    same line, the cursor should also be at the same position as when
    it first arrived on that line.
    """
    # self.setMovieMode(True)
    self.runWithTestFile(kTestFile, [
        self.displayCheck(0, 0, [
            " ci     .                               ",
            "                                        ",
            "     1                                  ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "New buffer         |    1, 1 |   0%,  0%",
            "                                        "]),
        self.writeText(u"short line"), CTRL_J,
        self.writeText(u"super long line that should go past the screen"),
        CTRL_J,
        self.writeText(u"line that slightly goes off screen"), CTRL_J,
        self.writeText(u"short line"), CTRL_J,
        self.writeText(u"medium-short line"), CTRL_J,
        self.writeText(u"medium-long line that can fit"),
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 short line                       ",
            "     2 super long line that should go p ",
            "     3 line that slightly goes off scre ",
            "     4 short line                       ",
            "     5 medium-short line                ",
            "     6 medium-long line that can fit    ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                        6,30 |  83%,100%",
            "                                        "]),
        KEY_UP, # Goes to end of 5th line.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 short line                       ",
            "     2 super long line that should go p ",
            "     3 line that slightly goes off scre ",
            "     4 short line                       ",
            "     5 medium-short line                ",
            "     6 medium-long line that can fit    ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                        5,18 |  66%,100%",
            "                                        "]),
        KEY_UP, # Goes to end of 4th line.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 short line                       ",
            "     2 super long line that should go p ",
            "     3 line that slightly goes off scre ",
            "     4 short line                       ",
            "     5 medium-short line                ",
            "     6 medium-long line that can fit    ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                        4,11 |  50%,100%",
            "                                        "]),
        KEY_UP, # Should go to column 30 of line 3 since we started at column 30.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 short line                       ",
            "     2 super long line that should go p ",
            "     3 line that slightly goes off scre ",
            "     4 short line                       ",
            "     5 medium-short line                ",
            "     6 medium-long line that can fit    ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                        3,30 |  33%, 85%",
            "                                        "]),
        KEY_UP, # Goes to column 30 of line 2.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 short line                       ",
            "     2 super long line that should go p ",
            "     3 line that slightly goes off scre ",
            "     4 short line                       ",
            "     5 medium-short line                ",
            "     6 medium-long line that can fit    ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                        2,30 |  16%, 63%",
            "                                        "]),
        KEY_UP, # Goes to end of line 1.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 short line                       ",
            "     2 super long line that should go p ",
            "     3 line that slightly goes off scre ",
            "     4 short line                       ",
            "     5 medium-short line                ",
            "     6 medium-long line that can fit    ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                        1,11 |   0%,100%",
            "                                        "]),
        KEY_DOWN, # All subsequent KEY_DOWNs should mirror the previous displays.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 short line                       ",
            "     2 super long line that should go p ",
            "     3 line that slightly goes off scre ",
            "     4 short line                       ",
            "     5 medium-short line                ",
            "     6 medium-long line that can fit    ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                        2,30 |  16%, 63%",
            "                                        "]),
        KEY_DOWN,
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 short line                       ",
            "     2 super long line that should go p ",
            "     3 line that slightly goes off scre ",
            "     4 short line                       ",
            "     5 medium-short line                ",
            "     6 medium-long line that can fit    ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                        3,30 |  33%, 85%",
            "                                        "]),
        KEY_DOWN,
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 short line                       ",
            "     2 super long line that should go p ",
            "     3 line that slightly goes off scre ",
            "     4 short line                       ",
            "     5 medium-short line                ",
            "     6 medium-long line that can fit    ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                        4,11 |  50%,100%",
            "                                        "]),
        KEY_DOWN,
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 short line                       ",
            "     2 super long line that should go p ",
            "     3 line that slightly goes off scre ",
            "     4 short line                       ",
            "     5 medium-short line                ",
            "     6 medium-long line that can fit    ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                        5,18 |  66%,100%",
            "                                        "]),
        KEY_DOWN,
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 short line                       ",
            "     2 super long line that should go p ",
            "     3 line that slightly goes off scre ",
            "     4 short line                       ",
            "     5 medium-short line                ",
            "     6 medium-long line that can fit    ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                        6,30 |  83%,100%",
            "                                        "]),
        CTRL_Q, u'n',
      ])