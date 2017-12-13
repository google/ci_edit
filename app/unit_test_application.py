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


import os
os.environ['CI_EDIT_USE_FAKE_CURSES'] = '1'

import app.ci_program
from app.curses_util import *
import curses
import inspect
import re
import sys
import unittest


kTestFile = '#test_file_with_unlikely_file_name~'


class IntentionTestCases(unittest.TestCase):
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
    self.cursesScreen = curses.StandardScreen()
    self.prg = app.ci_program.CiProgram(self.cursesScreen)

  def tearDown(self):
    # Disable mouse tracking in xterm.
    sys.stdout.write('\033[?1002l\n')
    # Disable Bracketed Paste Mode.
    sys.stdout.write('\033[?2004l\n')

  def notReached(display):
    """Calling this will fail the test. It's expected that the code will not
    reach this function."""
    self.fail('Called notReached!')

  def displayCheck(self, *args):
    caller = inspect.stack()[1]
    callerText = "\n  %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def checker(display, cmdIndex):
      result = display.check(*args)
      if result is not None:
        self.fail(callerText + result + ' at index ' + str(cmdIndex))
    return checker

  def cursorCheck(self, expectedRow, expectedCol):
    caller = inspect.stack()[1]
    callerText = "in %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def checker(display, cmdIndex):
      penRow, penCol = self.cursesScreen.getyx()
      self.assertEqual((expectedRow, expectedCol), (penRow, penCol), callerText)
    return checker

  def selectionCheck(self, expectedPenRow, expectedPenCol, expectedMarkerRow,
      expectedMarkerCol, expectedMode):
    caller = inspect.stack()[1]
    callerText = "in %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def checker(display, cmdIndex):
      selection = self.prg.getSelection()
      self.assertEqual((expectedPenRow, expectedPenCol, expectedMarkerRow,
          expectedMarkerCol, expectedMode), selection, callerText)
    return checker

  def addMouseInfo(self, timeStamp, mouseRow, mouseCol, bState):
    """
    bState may be a logical or of:
      curses.BUTTON1_PRESSED;
      curses.BUTTON1_RELEASED;
      ...
      curses.BUTTON_SHIFT
      curses.BUTTON_CTRL
      curses.BUTTON_ALT
    """
    info = (timeStamp, mouseCol, mouseRow, 0, bState)
    def createEvent(display, cmdIndex):
      curses.addMouseEvent(info)
    return createEvent

  def runWithTestFile(self, fakeInputs):
    self.cursesScreen.setFakeInputs(fakeInputs + [self.notReached,])
    self.assertTrue(self.prg)
    self.assertFalse(self.prg.exiting)
    sys.argv = [kTestFile]
    self.assertFalse(os.path.isfile(kTestFile))
    self.prg.run()
    #curses.printFakeDisplay()
    if app.ci_program.userConsoleMessage:
      message = app.ci_program.userConsoleMessage
      app.ci_program.userConsoleMessage = None
      self.fail(message)
    # Check that the application is closed down (don't leave it running across
    # tests).
    self.assertTrue(self.prg.exiting)
    self.assertEqual(self.cursesScreen.fakeInput.inputsIndex,
        len(fakeInputs) - 1)
    # Handy for debugging.
    if 0:
      caller = inspect.stack()[1]
      callerText = "  %s:%s:%s(): " % (
          os.path.split(caller[1])[1], caller[2], caller[3])
      print '\n-------- finished', callerText

  def test_open_and_quit(self):
    self.runWithTestFile([CTRL_Q])

  def test_new_file_quit(self):
    self.runWithTestFile([
        self.displayCheck(2, 7, ["        "]), CTRL_Q])

  def test_logo(self):
    self.runWithTestFile([
        self.displayCheck(0, 0, [" ci "]), CTRL_Q])

  def test_whole_screen(self):
    self.runWithTestFile([
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
            "New buffer         |    1, 1 | 100%,100%",
            "                                        ",
            ]), CTRL_Q])

  def test_find(self):
    self.runWithTestFile([
        self.displayCheck(-1, 0, ["      "]),
        CTRL_F, self.displayCheck(-1, 0, ["find: "]),
        CTRL_Q])

  def test_text_contents(self):
    self.runWithTestFile([
        self.displayCheck(2, 7, ["        "]), 't', 'e', 'x', 't',
        self.displayCheck(2, 7, ["text "]),  CTRL_Q, 'n'])

  def test_bracketed_paste(self):
    self.runWithTestFile([
        self.displayCheck(2, 7, ["      "]),
        curses.ascii.ESC, app.curses_util.BRACKETED_PASTE_BEGIN,
        't', 'e', ord('\xc3'), ord('\xa9'), 't',
        curses.ascii.ESC, app.curses_util.BRACKETED_PASTE_END,
        self.displayCheck(2, 7, [unicode('te\xc3\xa9t ', 'utf-8')]),
        CTRL_Q, 'n'])

  def test_backspace(self):
    self.runWithTestFile([
        self.displayCheck(2, 7, ["      "]), 't', 'e', 'x',
        self.displayCheck(2, 7, ["tex "]), KEY_BACKSPACE1, 't',
        self.displayCheck(2, 7, ["tet "]), CTRL_Q, 'n'])

  def test_cursor_moves(self):
    self.runWithTestFile([
        self.displayCheck(0, 0, [
            " ci     .                               ",
            "                                        ",
            "     1                                  "]),
        self.cursorCheck(2, 7),
        't', 'e', 's', 't', CTRL_J,
        'a', 'p', 'p', 'l', 'e', CTRL_J,
        'o', 'r', 'a', 'n', 'g', 'e',
        self.cursorCheck(4, 13),
        self.selectionCheck(2, 6, 0, 0, 0),
        KEY_UP, self.cursorCheck(3, 12), self.selectionCheck(1, 5, 0, 0, 0),
        KEY_UP, self.cursorCheck(2, 11), self.selectionCheck(0, 4, 0, 0, 0),
        KEY_UP, self.cursorCheck(2, 11), self.selectionCheck(0, 4, 0, 0, 0),
        KEY_LEFT, self.cursorCheck(2, 10), self.selectionCheck(0, 3, 0, 0, 0),
        KEY_LEFT, self.cursorCheck(2, 9), self.selectionCheck(0, 2, 0, 0, 0),
        KEY_DOWN, self.cursorCheck(3, 9), self.selectionCheck(1, 2, 0, 0, 0),
        KEY_DOWN, self.cursorCheck(4, 9), self.selectionCheck(2, 2, 0, 0, 0),
        KEY_RIGHT, self.cursorCheck(4, 10), self.selectionCheck(2, 3, 0, 0, 0),
        KEY_DOWN, self.cursorCheck(4, 10), self.selectionCheck(2, 3, 0, 0, 0),
        KEY_HOME, self.cursorCheck(4, 7), self.selectionCheck(2, 0, 0, 0, 0),
        KEY_END, self.cursorCheck(4, 13), self.selectionCheck(2, 6, 0, 0, 0),
        KEY_SHIFT_UP, self.cursorCheck(3, 12), self.selectionCheck(1, 5, 2, 6, 3),
        KEY_SHIFT_LEFT, self.cursorCheck(3, 11), self.selectionCheck(1, 4, 2, 6, 3),
        KEY_SHIFT_RIGHT, self.cursorCheck(3, 12), self.selectionCheck(1, 5, 2, 6, 3),
        KEY_SHIFT_RIGHT, self.cursorCheck(4, 7), self.selectionCheck(2, 0, 2, 6, 3),
        KEY_SHIFT_RIGHT, self.cursorCheck(4, 8), self.selectionCheck(2, 1, 2, 6, 3),
        CTRL_Q, 'n']);

  def test_select_line(self):
    self.runWithTestFile([
        self.displayCheck(0, 0, [
            " ci     .                               ",
            "                                        ",
            "     1                                  "]),
        self.cursorCheck(2, 7),
        't', 'e', 's', 't', CTRL_J,
        'a', 'p', 'p', 'l', 'e', CTRL_J,
        'o', 'r', 'a', 'n', 'g', 'e',
        self.cursorCheck(4, 13),
        self.selectionCheck(2, 6, 0, 0, 0),
        CTRL_L,
        self.selectionCheck(2, 6, 2, 0, 4),
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
    self.runWithTestFile([
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
    self.runWithTestFile([
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
            "New buffer         |    1, 1 | 100%,100%",
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
            "                        1, 6 | 100%,100%",
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
            "                        1, 1 | 100%,100%",
            "                                        "]),
        CTRL_Q])
