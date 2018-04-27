# -*- coding: latin-1 -*-

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

import curses
import sys

from app.curses_util import *
import app.fake_curses_testing


class FindWindowTestCases(app.fake_curses_testing.FakeCursesTestCase):
  def setUp(self):
    self.longMessage = True
    if True:
      # The buffer manager will retain the test file in RAM. Reset it.
      try:
        del sys.modules['app.buffer_manager']
        import app.buffer_manager
      except KeyError:
        pass
    app.fake_curses_testing.FakeCursesTestCase.setUp(self)

  def test_find(self):
    self.runWithFakeInputs([
        self.displayCheck(-1, 0, ["      "]),
        CTRL_F, self.displayCheck(-1, 0, ["Find: "]), CTRL_J,
        self.displayCheck(-1, 0, ["      "]),
        CTRL_F, self.displayCheck(-1, 0, ["Find: "]),
        CTRL_I, self.displayCheck(-3, 0, ["Find: ", "Replace: ", "["]),
        KEY_BTAB, KEY_BTAB, self.displayCheck(-1, 0, ["Find: "]),
        CTRL_Q])

  def test_find_esc_from_find(self):
    self.runWithFakeInputs([
        # Check initial state.
        self.displayCheck(-1, 0, ["      "]),
        self.displayCheckStyle(-2, 0, 1, 10, app.prefs.color['status_line']),

        # Basic open and close.
        CTRL_F, self.displayCheck(-1, 0, ["Find: "]),
        KEY_ESCAPE, curses.ERR, self.displayCheck(-3, 0, ["   ", "   ", "   "]),
        self.displayCheckStyle(-2, 0, 1, 10, app.prefs.color['status_line']),

        # Open, expand, and close.
        CTRL_F, self.displayCheck(-1, 0, ["Find: "]),
        CTRL_I, self.displayCheck(-3, 0, ["Find: ", "Replace: ", "["]),
        KEY_ESCAPE, curses.ERR, self.displayCheck(-3, 0, ["   ", "   ", "   "]),
        self.displayCheckStyle(-2, 0, 1, 10, app.prefs.color['status_line']),

        # Regression test one for https://github.com/google/ci_edit/issues/170.
        CTRL_F, self.displayCheck(-3, 0, ["Find: ", "Replace: ", "["]),
        CTRL_I, CTRL_I, self.displayCheck(-3, 0, ["Find: ", "Replace: ", "["]),
        KEY_ESCAPE, curses.ERR, self.displayCheck(-3, 0, ["   ", "   ", "   "]),
        self.displayCheckStyle(-2, 0, 1, 10, app.prefs.color['status_line']),

        # Regression test two for https://github.com/google/ci_edit/issues/170.
        CTRL_F, self.displayCheck(-3, 0, ["Find: ", "Replace: ", "["]),
        self.addMouseInfo(0, 2, 10, curses.BUTTON1_PRESSED),
        curses.KEY_MOUSE,
        #self.displayCheck(-3, 0, ["   ", "   ", "   "]),
        self.displayCheckStyle(-2, 0, 1, 10, app.prefs.color['status_line']),
        CTRL_Q])
