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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
try:
  unicode('')
except:
  unicode = str
  unichr = chr

import curses
import inspect
import os
import sys
import tempfile
import unittest

import third_party.pyperclip as clipboard

import app.ci_program
from app.curses_util import *
import app.prefs


def debug_print_stack(*args):
  stack = inspect.stack()[1:]
  stack.reverse()
  lines = []
  for i,frame in enumerate(stack):
    lines.append(u"stack %2d %14s %4s %s" % (i, os.path.split(frame[1])[1],
        frame[2], frame[3]))
  print(u"\n".join(lines))


class FakeCursesTestCase(unittest.TestCase):
  def setUp(self):
    if True:
      # The buffer manager will retain the test file in RAM. Reset it.
      try:
        del sys.modules['app.buffer_manager']
        import app.buffer_manager
      except KeyError:
        pass
    if True:
      # The prefs may contain old test settings in RAM. Reset it.
      try:
        del sys.modules['app.prefs']
        import app.prefs
        app.prefs.prefsDirectory = tempfile.mkdtemp()
        #print(u"\nPrefs from this test are at:\n", app.prefs.prefsDirectory)
      except KeyError:
        pass
    self.cursesScreen = curses.StandardScreen()
    self.prg = app.ci_program.CiProgram(self.cursesScreen)

  def addClickInfo(self, timeStamp, screenText, bState):
    caller = inspect.stack()[1]
    callerText = u"\n  %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def createEvent(display, cmdIndex):
      row, col = self.findText(screenText)
      if row < 0:
        output = u"%s at index %d, did not find %r" % (callerText, cmdIndex,
            screenText)
        if self.cursesScreen.movie:
          print(output)
        else:
          self.fail(output)
      # Note that the mouse info is x,y (col, row).
      info = (timeStamp, col, row, 0, bState)
      curses.addMouseEvent(info)
      return None
    return createEvent

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
    assert type(timeStamp) is int
    assert type(mouseRow) is int
    assert type(mouseCol) is int
    assert type(bState) is int
    # Note that the mouse info is x,y (col, row).
    info = (timeStamp, mouseCol, mouseRow, 0, bState)
    def createEvent(display, cmdIndex):
      curses.addMouseEvent(info)
      return None
    return createEvent

  def displayCheck(self, *args):
    assert type(args[0]) is int
    caller = inspect.stack()[1]
    callerText = u"\n  %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def displayChecker(display, cmdIndex):
      result = display.checkText(*args)
      if result is not None:
        output = callerText + u' at index ' + str(cmdIndex) + result
        if self.cursesScreen.movie:
          print(output)
        else:
          self.fail(output)
      return None
    return displayChecker

  def displayCheckNot(self, *args):
    """
    Verify that the display does not match.
    """
    assert type(args[0]) is int
    caller = inspect.stack()[1]
    callerText = "\n  %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def displayCheckerNot(display, cmdIndex):
      result = display.checkText(*args)
      if result is None:
        output = callerText + u' at index ' + str(cmdIndex)
        if self.cursesScreen.movie:
          print(output)
        else:
          self.fail(output)
      return None
    return displayCheckerNot

  def displayCheckStyle(self, *args):
    caller = inspect.stack()[1]
    callerText = u"\n  %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def displayStyleChecker(display, cmdIndex):
      result = display.checkStyle(*args)
      if result is not None:
        output = callerText + u' at index ' + str(cmdIndex) + result
        if self.cursesScreen.movie:
          print(output)
        else:
          self.fail(output)
      return None
    return displayStyleChecker

  def findText(self, screenText):
    """Locate |screenText| on the display, returning row, col.
    """
    return self.cursesScreen.test_find_text(screenText)

  def cursorCheck(self, expectedRow, expectedCol):
    assert type(expectedRow) is int
    assert type(expectedCol) is int
    caller = inspect.stack()[1]
    callerText = u"in %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def cursorChecker(display, cmdIndex):
      penRow, penCol = self.cursesScreen.getyx()
      if self.cursesScreen.movie:
        return None
      self.assertEqual((expectedRow, expectedCol), (penRow, penCol), callerText)
      return None
    return cursorChecker

  def resizeScreen(self, rows, cols):
    assert type(rows) is int
    assert type(cols) is int
    caller = inspect.stack()[1]
    callerText = u"in %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def setScreenSize(display, cmdIndex):
      self.cursesScreen.fakeDisplay.setScreenSize(rows, cols)
      return curses.KEY_RESIZE
    return setScreenSize

  def setClipboard(self, text):
    assert type(text) is str
    caller = inspect.stack()[1]
    callerText = u"in %s:%s:%s(): " % (
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
    assert type(text) is unicode, type(text)
    caller = inspect.stack()[1]
    callerText = u"in %s:%s:%s(): " % (
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
    assert hasattr(fakeInputs, "__getitem__") or hasattr(fakeInputs, "__iter__")
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
      callerText = u"  %s:%s:%s(): " % (
          os.path.split(caller[1])[1], caller[2], caller[3])
      print(u'\n-------- finished', callerText)

  def runWithTestFile(self, kTestFile, fakeInputs):
    sys.argv = [kTestFile]
    self.assertFalse(os.path.isfile(kTestFile))
    self.runWithFakeInputs(fakeInputs)

  def selectionDocumentCheck(self, expectedPenRow, expectedPenCol, expectedMarkerRow,
      expectedMarkerCol, expectedMode):
    caller = inspect.stack()[1]
    callerText = u"in %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def checker(display, cmdIndex):
      selection = self.prg.getDocumentSelection()
      self.assertEqual((expectedPenRow, expectedPenCol, expectedMarkerRow,
          expectedMarkerCol, expectedMode), selection, callerText)
    return checker

  def selectionCheck(self, expectedPenRow, expectedPenCol, expectedMarkerRow,
      expectedMarkerCol, expectedMode):
    caller = inspect.stack()[1]
    callerText = u"in %s:%s:%s(): " % (
        os.path.split(caller[1])[1], caller[2], caller[3])
    def checker(display, cmdIndex):
      selection = self.prg.getSelection()
      self.assertEqual((expectedPenRow, expectedPenCol, expectedMarkerRow,
          expectedMarkerCol, expectedMode), selection, callerText)
    return checker

  def tearDown(self):
    # Disable mouse tracking in xterm.
    sys.stdout.write(u"\033[?1002l\n")
    # Disable Bracketed Paste Mode.
    sys.stdout.write(u"\033[?2004l\n")
