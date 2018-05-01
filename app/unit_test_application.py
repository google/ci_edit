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

import curses
import os
import sys

from app.curses_util import *
import app.ci_program
import app.fake_curses_testing
import app.prefs


kTestFile = '#application_test_file_with_unlikely_file_name~'


class IntentionTestCases(app.fake_curses_testing.FakeCursesTestCase):
  def setUp(self):
    self.longMessage = True
    if True:
      # The buffer manager will retain the test file in RAM. Reset it.
      try:
        del sys.modules['app.buffer_manager']
        import app.buffer_manager
      except KeyError:
        pass
    if os.path.isfile(kTestFile):
      os.unlink(kTestFile)
    self.assertFalse(os.path.isfile(kTestFile))
    app.fake_curses_testing.FakeCursesTestCase.setUp(self)

  def test_open_and_quit(self):
    self.runWithTestFile(kTestFile, [CTRL_Q])

  def test_new_file_quit(self):
    self.runWithTestFile(kTestFile, [
        self.displayCheck(2, 7, ["        "]), CTRL_Q])

  def test_logo(self):
    self.runWithTestFile(kTestFile, [
        self.assertEqual(256, app.prefs.startup['numColors']),
        self.displayCheck(0, 0, [" ci "]),
        self.displayCheckStyle(0, 0, 1, len(" ci "), app.prefs.color['logo']),
        CTRL_Q])

  def test_whole_screen(self):
    #self.setMovieMode(True)
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
            "                                        ",
            ]), CTRL_Q])

  def test_resize_screen(self):
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
            "                                        ",
            ]),
        self.resizeScreen(10, 36),
        self.displayCheck(0, 0, [
            " ci     .                           ",
            "                                    ",
            "     1                              ",
            "                                    ",
            "                                    ",
            "                                    ",
            "                                    ",
            "                                    ",
            "                    1, 1 |   0%,  0%",
            "                                    ",
            ]),
            CTRL_Q])

  def test_prediction(self):
    #self.setMovieMode(True)
    self.runWithTestFile(kTestFile, [
        self.displayCheck(-1, 0, ["      "]),
        CTRL_P, self.displayCheck(-1, 0, ["p: "]), CTRL_J,
        self.displayCheck(-1, 0, ["      "]),
        CTRL_P, self.displayCheck(-1, 0, ["p: "]), CTRL_J,
        CTRL_Q])

  def test_text_contents(self):
    self.runWithTestFile(kTestFile, [
        self.displayCheck(2, 7, ["        "]), 't', 'e', 'x', 't',
        self.displayCheck(2, 7, ["text "]),  CTRL_Q, 'n'])

  def test_bracketed_paste(self):
    self.runWithTestFile(kTestFile, [
        self.displayCheck(2, 7, ["      "]),
        curses.ascii.ESC, app.curses_util.BRACKETED_PASTE_BEGIN,
        't', 'e', ord('\xc3'), ord('\xa9'), 't',
        curses.ascii.ESC, app.curses_util.BRACKETED_PASTE_END,
        self.displayCheck(2, 7, [unicode('te\xc3\xa9t ', 'utf-8')]),
        CTRL_Q, 'n'])

  def test_backspace(self):
    self.runWithTestFile(kTestFile, [
        self.displayCheck(2, 7, ["      "]), self.writeText('tex'),
        self.displayCheck(2, 7, ["tex "]), KEY_BACKSPACE1, 't',
        self.displayCheck(2, 7, ["tet "]), CTRL_Q, 'n'])

  def test_cursor_moves(self):
    self.runWithTestFile(kTestFile, [
        self.displayCheck(0, 0, [
            " ci     .                               ",
            "                                        ",
            "     1                                  "]),
        self.cursorCheck(2, 7),
        self.writeText('test\napple\norange'),
        self.cursorCheck(4, 13),
        self.selectionCheck(2, 6, 0, 0, 0),
        KEY_UP, self.cursorCheck(3, 12), self.selectionCheck(1, 5, 0, 0, 0),
        KEY_UP, self.cursorCheck(2, 11), self.selectionCheck(0, 4, 0, 0, 0),
        KEY_UP, self.cursorCheck(2, 7), self.selectionCheck(0, 0, 0, 0, 0),
        KEY_RIGHT, KEY_RIGHT, KEY_RIGHT, KEY_RIGHT,
        KEY_LEFT, self.cursorCheck(2, 10), self.selectionCheck(0, 3, 0, 0, 0),
        KEY_LEFT, self.cursorCheck(2, 9), self.selectionCheck(0, 2, 0, 0, 0),
        KEY_DOWN, self.cursorCheck(3, 9), self.selectionCheck(1, 2, 0, 0, 0),
        KEY_DOWN, self.cursorCheck(4, 9), self.selectionCheck(2, 2, 0, 0, 0),
        KEY_RIGHT, self.cursorCheck(4, 10), self.selectionCheck(2, 3, 0, 0, 0),
        KEY_DOWN, self.cursorCheck(4, 13), self.selectionCheck(2, 6, 0, 0, 0),
        KEY_HOME, self.cursorCheck(4, 7), self.selectionCheck(2, 0, 0, 0, 0),
        KEY_END, self.cursorCheck(4, 13), self.selectionCheck(2, 6, 0, 0, 0),
        KEY_SHIFT_UP, self.cursorCheck(3, 12), self.selectionCheck(1, 5, 2, 6, 3),
        KEY_SHIFT_LEFT, self.cursorCheck(3, 11), self.selectionCheck(1, 4, 2, 6, 3),
        KEY_SHIFT_RIGHT, self.cursorCheck(3, 12), self.selectionCheck(1, 5, 2, 6, 3),
        KEY_SHIFT_RIGHT, self.cursorCheck(4, 7), self.selectionCheck(2, 0, 2, 6, 3),
        KEY_SHIFT_RIGHT, self.cursorCheck(4, 8), self.selectionCheck(2, 1, 2, 6, 3),
        CTRL_Q, 'n']);

  def test_cursor_select_first_line(self):
    self.runWithTestFile(kTestFile, [
        self.cursorCheck(2, 7),
        self.writeText('test\napple\norange'),
        self.cursorCheck(4, 13), self.selectionCheck(2, 6, 0, 0, 0),
        KEY_SHIFT_UP,
        self.cursorCheck(3, 12), self.selectionCheck(1, 5, 2, 6, 3),
        KEY_SHIFT_UP,
        self.cursorCheck(2, 11), self.selectionCheck(0, 4, 2, 6, 3),
        # Regression test: shift down past the end of the document should select
        # to end of document (i.e. end of line).
        KEY_SHIFT_UP,
        self.cursorCheck(2, 7), self.selectionCheck(0, 0, 2, 6, 3),
        # Same for non-selection.
        KEY_DOWN, KEY_END,
        self.cursorCheck(3, 12), self.selectionCheck(1, 5, 0, 0, 0),
        KEY_UP,
        self.cursorCheck(2, 11), self.selectionCheck(0, 4, 0, 0, 0),
        KEY_UP,
        self.cursorCheck(2, 7), self.selectionCheck(0, 0, 0, 0, 0),
        CTRL_Q, 'n']);

  def test_cursor_select_last_line(self):
    self.runWithTestFile(kTestFile, [
        self.cursorCheck(2, 7),
        self.writeText('test\napple\norange'),
        self.cursorCheck(4, 13), self.selectionCheck(2, 6, 0, 0, 0),
        CTRL_G, ord('t'),
        self.cursorCheck(2, 7), self.selectionCheck(0, 0, 0, 0, 0),
        KEY_SHIFT_DOWN,
        self.cursorCheck(3, 7), self.selectionCheck(1, 0, 0, 0, 3),
        KEY_SHIFT_DOWN,
        self.cursorCheck(4, 7), self.selectionCheck(2, 0, 0, 0, 3),
        # Regression test: shift down past the end of the document should select
        # to end of document (i.e. end of line).
        KEY_SHIFT_DOWN,
        self.cursorCheck(4, 13), self.selectionCheck(2, 6, 0, 0, 3),
        # Same for non-selection.
        KEY_UP, KEY_HOME,
        self.cursorCheck(3, 7), self.selectionCheck(1, 0, 2, 6, 0),
        KEY_DOWN,
        self.cursorCheck(4, 7), self.selectionCheck(2, 0, 2, 6, 0),
        KEY_DOWN,
        self.cursorCheck(4, 13), self.selectionCheck(2, 6, 2, 6, 0),
        CTRL_Q, 'n']);

  def test_ctrl_cursor_moves(self):
    self.runWithTestFile(kTestFile, [
        self.displayCheck(0, 0, [
            " ci     .                               ",
            "                                        ",
            "     1                                  "]),
        self.cursorCheck(2, 7),
        self.writeText('test\napple bananaCarrot DogElephantFrog\norange'),
        self.cursorCheck(4, 13),
        self.selectionCheck(2, 6, 0, 0, 0),
        KEY_CTRL_LEFT, self.cursorCheck(4, 7), self.selectionCheck(2, 0, 0, 0, 0),
        KEY_CTRL_SHIFT_RIGHT, self.cursorCheck(4, 13), self.selectionCheck(2, 6, 2, 0, 3),
        KEY_CTRL_SHIFT_LEFT, self.cursorCheck(4, 7), self.selectionCheck(2, 0, 2, 0, 3),
        KEY_CTRL_SHIFT_LEFT, self.cursorCheck(3, 38), self.selectionCheck(1, 34, 2, 0, 3),
        KEY_CTRL_SHIFT_LEFT, self.cursorCheck(3, 23), self.selectionCheck(1, 19, 2, 0, 3),
        KEY_CTRL_SHIFT_LEFT, self.cursorCheck(3, 22), self.selectionCheck(1, 18, 2, 0, 3),
        KEY_CTRL_RIGHT, self.cursorCheck(3, 23), self.selectionCheck(1, 19, 1, 18, 0),
        CTRL_Q, 'n']);

  def test_select_line(self):
    self.runWithTestFile(kTestFile, [
        self.displayCheck(0, 0, [
            " ci     .                               ",
            "                                        ",
            "     1                                  "]),
        self.cursorCheck(2, 7),
        self.writeText('test\napple\norange'),
        self.cursorCheck(4, 13),
        self.selectionCheck(2, 6, 0, 0, 0),
        CTRL_L,
        self.selectionCheck(2, 6, 2, 0, 4),
        self.displayCheckStyle(0, 0, 1, len(" ci "), app.prefs.color['logo']),
        KEY_UP,
        self.selectionCheck(1, 5, 2, 6, 0),
        CTRL_L,
        self.selectionCheck(2, 0, 1, 0, 4),
        CTRL_L,
        self.selectionCheck(2, 6, 1, 0, 4),
        self.addMouseInfo(0, 2, 10, curses.BUTTON1_PRESSED),
        curses.KEY_MOUSE,
        self.selectionCheck(2, 6, 0, 3, 2),
        CTRL_Q, 'n']);

  def test_select_line_via_line_numbers(self):
    self.runWithTestFile(kTestFile, [
        self.displayCheck(0, 0, [
            " ci     .                               ",
            "                                        ",
            "     1                                  "]),
        self.cursorCheck(2, 7),
        'a', 'b', 'c', CTRL_J, 'd', 'e', CTRL_J, 'f', 'g', 'h', 'i',
        self.cursorCheck(4, 11),
        self.addMouseInfo(0, 3, 2, curses.BUTTON1_PRESSED),
        curses.KEY_MOUSE,
        CTRL_L,
        CTRL_Q, 'n']);

  def test_session(self):
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
        'H', 'e', 'l', 'l', 'o',
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 Hello                            ",
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
            "                        1, 6 |   0%,100%",
            "                                        "]),
        CTRL_Z,
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
            "                        1, 1 |   0%,  0%",
            "                                        "]),
        CTRL_Q])

  def test_quit_cancel(self):
    #self.setMovieMode(True)
    self.runWithFakeInputs([
        self.displayCheck(0, 0, [
            " ci     .                               ",]),
        'x',
        CTRL_Q,
        'c',
        self.writeText(' after cancel'),
        self.displayCheck(2, 7, [
            "x after cancel ",]),
        CTRL_Q,
        'n'
        ])

  def test_quit_save_as(self):
    #self.setMovieMode(True)
    self.assertFalse(os.path.isfile(kTestFile))
    self.runWithFakeInputs([
        self.displayCheck(0, 0, [
            " ci     .                               ",]),
        'x',
        CTRL_Q,
        'y',
        self.writeText(kTestFile),
        CTRL_J,
        CTRL_Q,
        ])
    self.assertTrue(os.path.isfile(kTestFile))
    os.unlink(kTestFile)
    self.assertFalse(os.path.isfile(kTestFile))
