# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.log
import app.text_buffer
import unittest

class FakeCursorWindow:
  def getmaxyx(self):
    return (100, 100)


class FakeView:
  def __init__(self):
    self.cursorWindow = FakeCursorWindow()


class MouseTestCases(unittest.TestCase):
  def setUp(self):
    app.log.shouldWritePrintLog = False
    self.textBuffer = app.text_buffer.TextBuffer()
    self.textBuffer.setView(FakeView())
    test = """/* first comment */
two
// second comment
apple banana carrot
#include "test.h"
void blah();
"""
    self.textBuffer.insertLines(test.split('\n'))
    self.assertEqual(self.textBuffer.scrollRow, 0)
    self.assertEqual(self.textBuffer.scrollCol, 0)
    self.assertEqual(self.textBuffer.lines[1], 'two')

  def tearDown(self):
    self.textBuffer = None

  def test_mouse_selection(self):
    self.textBuffer.mouseClick(3, 9, False, False, False)
    self.assertEqual(self.textBuffer.cursorRow, 3)
    self.assertEqual(self.textBuffer.cursorCol, 9)
    #assert(self.textBuffer.markerRow == 3)

    self.textBuffer.mouseClick(3, 8, True, False, False)
    self.assertEqual(self.textBuffer.markerRow, 3)
    self.assertEqual(self.textBuffer.markerCol, 9)
    self.assertEqual(self.textBuffer.cursorRow, 3)
    self.assertEqual(self.textBuffer.cursorCol, 8)

    self.textBuffer.mouseClick(4, 8, True, False, False)
    self.assertEqual(self.textBuffer.markerRow, 3)
    self.assertEqual(self.textBuffer.markerCol, 9)
    self.assertEqual(self.textBuffer.cursorRow, 4)
    self.assertEqual(self.textBuffer.cursorCol, 8)

    self.textBuffer.mouseClick(3, 8, True, False, False)
    self.assertEqual(self.textBuffer.markerRow, 3)
    self.assertEqual(self.textBuffer.markerCol, 9)
    self.assertEqual(self.textBuffer.cursorRow, 3)
    self.assertEqual(self.textBuffer.cursorCol, 8)

    self.textBuffer.mouseClick(4, 8, True, False, False)
    self.textBuffer.mouseClick(4, 9, True, False, False)
    self.assertEqual(self.textBuffer.markerRow, 3)
    self.assertEqual(self.textBuffer.markerCol, 9)
    self.assertEqual(self.textBuffer.cursorRow, 4)
    self.assertEqual(self.textBuffer.cursorCol, 9)

    self.textBuffer.mouseClick(4, 10, True, False, False)
    self.assertEqual(self.textBuffer.markerRow, 3)
    self.assertEqual(self.textBuffer.markerCol, 9)
    self.assertEqual(self.textBuffer.cursorRow, 4)
    self.assertEqual(self.textBuffer.cursorCol, 10)

    self.textBuffer.mouseClick(4, 11, True, False, False)
    self.assertEqual(self.textBuffer.markerRow, 3)
    self.assertEqual(self.textBuffer.markerCol, 9)
    self.assertEqual(self.textBuffer.cursorRow, 4)
    #self.assertEqual(self.textBuffer.cursorCol, 11)
    self.assertEqual(self.textBuffer.scrollCol, 0)

  def test_mouse_word_selection(self):
    self.assertEqual(self.textBuffer.scrollCol, 0)
    self.textBuffer.selectionWord()
    self.assertEqual(self.textBuffer.scrollCol, 0)
    row = 3
    col = 9
    wordBegin = 6
    wordEnd = 12
    self.textBuffer.mouseClick(row, col, False, False, False)
    self.assertEqual(self.textBuffer.cursorRow, row)
    self.assertEqual(self.textBuffer.cursorCol, col)

    self.textBuffer.mouseDoubleClick(row, col-1, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.markerCol, wordBegin)
    self.assertEqual(self.textBuffer.cursorRow, row)
    self.assertEqual(self.textBuffer.cursorCol, wordEnd)

    self.textBuffer.mouseMoved(row, wordBegin, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.markerCol, wordBegin)
    self.assertEqual(self.textBuffer.cursorRow, row)
    self.assertEqual(self.textBuffer.cursorCol, wordEnd)

    self.textBuffer.mouseMoved(row, wordBegin-1, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.cursorCol, 0)
    self.assertEqual(self.textBuffer.markerCol, wordEnd)
    self.assertEqual(self.textBuffer.cursorRow, row)
    self.assertEqual(self.textBuffer.cursorCol, 0)

    self.textBuffer.mouseMoved(row, 1, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.markerCol, wordEnd)
    self.assertEqual(self.textBuffer.cursorRow, row)
    self.assertEqual(self.textBuffer.cursorCol, 0)

    self.textBuffer.mouseMoved(row+1, 0, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.markerCol, wordBegin)
    self.assertEqual(self.textBuffer.cursorRow, row+1)
    self.assertEqual(self.textBuffer.cursorCol, 1)

    self.textBuffer.mouseMoved(row+1, 1, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.markerCol, wordBegin)
    self.assertEqual(self.textBuffer.cursorRow, row+1)
    self.assertEqual(self.textBuffer.cursorCol, 8)

    self.textBuffer.mouseMoved(row, 1, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.markerCol, wordBegin)
    self.assertEqual(self.textBuffer.cursorRow, row)
    self.assertEqual(self.textBuffer.cursorCol, 0)
