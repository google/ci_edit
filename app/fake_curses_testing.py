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


import app.ci_program
from app.curses_util import *
import curses
import inspect
import os
import sys
import third_party.pyperclip as clipboard
import unittest


class FakeCursesTestCase(unittest.TestCase):
  def setUp(self):
    self.cursesScreen = curses.StandardScreen()
    self.prg = app.ci_program.CiProgram(self.cursesScreen)

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
      return None
    return createEvent

  def displayCheck(self, *args):
    caller = inspect.stack()[1]
    callerText = "\n  %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def displayChecker(display, cmdIndex):
      result = display.checkText(*args)
      if result is not None:
        output = callerText + result + ' at index ' + str(cmdIndex)
        if self.cursesScreen.movie:
          print output
        else:
          self.fail(output)
      return None
    return displayChecker

  def displayCheckStyle(self, *args):
    caller = inspect.stack()[1]
    callerText = "\n  %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def displayStyleChecker(display, cmdIndex):
      result = display.checkStyle(*args)
      if result is not None:
        output = callerText + result + ' at index ' + str(cmdIndex)
        if self.cursesScreen.movie:
          print output
        else:
          self.fail(output)
      return None
    return displayStyleChecker

  def cursorCheck(self, expectedRow, expectedCol):
    caller = inspect.stack()[1]
    callerText = "in %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def cursorChecker(display, cmdIndex):
      penRow, penCol = self.cursesScreen.getyx()
      if self.cursesScreen.movie:
        return None
      self.assertEqual((expectedRow, expectedCol), (penRow, penCol), callerText)
      return None
    return cursorChecker

  def setClipboard(self, text):
    caller = inspect.stack()[1]
    callerText = "in %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def copyToClipboard(display, cmdIndex):
      self.assertTrue(clipboard.copy)  # Check that copy exists.
      clipboard.copy(text)
      return None
    return copyToClipboard

  def setMovieMode(self, enabled):
    self.cursesScreen.movie = enabled
    self.cursesScreen.fakeInput.isVerbose = enabled

  def writeText(self, text):
    caller = inspect.stack()[1]
    callerText = "in %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def copyToClipboard(display, cmdIndex):
      self.assertTrue(clipboard.copy)  # Check that copy exists.
      clipboard.copy(text)
      return CTRL_V
    return copyToClipboard

  def notReached(display):
    """Calling this will fail the test. It's expected that the code will not
    reach this function."""
    self.fail('Called notReached!')

  def runWithFakeInputs(self, fakeInputs):
    app.color.reset(),
    self.cursesScreen.setFakeInputs(fakeInputs + [self.notReached,])
    self.assertTrue(self.prg)
    self.assertFalse(self.prg.exiting)
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

  def tearDown(self):
    # Disable mouse tracking in xterm.
    sys.stdout.write('\033[?1002l\n')
    # Disable Bracketed Paste Mode.
    sys.stdout.write('\033[?2004l\n')
