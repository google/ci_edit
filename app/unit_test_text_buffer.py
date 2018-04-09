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

import unittest

import app.log
import app.text_buffer


class FakeCursorWindow:
  def getmaxyx(self):
    return (100, 100)


class FakeView:
  def __init__(self):
    self.cursorWindow = FakeCursorWindow()
    self.top = 0
    self.left = 0
    self.rows = 10
    self.cols = 100
    self.scrollRow = 0
    self.scrollCol = 0


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
    #self.assertEqual(self.textBuffer.scrollRow, 0)
    #self.assertEqual(self.textBuffer.scrollCol, 0)
    self.assertEqual(self.textBuffer.lines[1], 'two')

  def tearDown(self):
    self.textBuffer = None

  def test_mouse_selection(self):
    self.textBuffer.mouseClick(3, 9, False, False, False)
    self.assertEqual(self.textBuffer.penRow, 3)
    self.assertEqual(self.textBuffer.penCol, 9)
    #assert(self.textBuffer.markerRow == 3)

    self.textBuffer.mouseClick(3, 8, True, False, False)
    self.assertEqual(self.textBuffer.markerRow, 3)
    self.assertEqual(self.textBuffer.markerCol, 9)
    self.assertEqual(self.textBuffer.penRow, 3)
    self.assertEqual(self.textBuffer.penCol, 8)

    self.textBuffer.mouseClick(4, 8, True, False, False)
    self.assertEqual(self.textBuffer.markerRow, 3)
    self.assertEqual(self.textBuffer.markerCol, 9)
    self.assertEqual(self.textBuffer.penRow, 4)
    self.assertEqual(self.textBuffer.penCol, 8)

    self.textBuffer.mouseClick(3, 8, True, False, False)
    self.assertEqual(self.textBuffer.markerRow, 3)
    self.assertEqual(self.textBuffer.markerCol, 9)
    self.assertEqual(self.textBuffer.penRow, 3)
    self.assertEqual(self.textBuffer.penCol, 8)

    self.textBuffer.mouseClick(4, 8, True, False, False)
    self.textBuffer.mouseClick(4, 9, True, False, False)
    self.assertEqual(self.textBuffer.markerRow, 3)
    self.assertEqual(self.textBuffer.markerCol, 9)
    self.assertEqual(self.textBuffer.penRow, 4)
    self.assertEqual(self.textBuffer.penCol, 9)

    self.textBuffer.mouseClick(4, 10, True, False, False)
    self.assertEqual(self.textBuffer.markerRow, 3)
    self.assertEqual(self.textBuffer.markerCol, 9)
    self.assertEqual(self.textBuffer.penRow, 4)
    self.assertEqual(self.textBuffer.penCol, 10)

    self.textBuffer.mouseClick(4, 11, True, False, False)
    self.assertEqual(self.textBuffer.markerRow, 3)
    self.assertEqual(self.textBuffer.markerCol, 9)
    self.assertEqual(self.textBuffer.penRow, 4)
    #self.assertEqual(self.textBuffer.penCol, 11)
    #self.assertEqual(self.textBuffer.scrollCol, 0)

  def test_mouse_word_selection(self):
    #self.assertEqual(self.textBuffer.scrollCol, 0)
    self.textBuffer.selectionWord()
    #self.assertEqual(self.textBuffer.scrollCol, 0)
    row = 3
    col = 9
    wordBegin = 6
    wordEnd = 12
    self.textBuffer.mouseClick(row, col, False, False, False)
    self.assertEqual(self.textBuffer.penRow, row)
    self.assertEqual(self.textBuffer.penCol, col)

    self.textBuffer.mouseDoubleClick(row, col-1, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.markerCol, wordBegin)
    self.assertEqual(self.textBuffer.penRow, row)
    self.assertEqual(self.textBuffer.penCol, wordEnd)

    self.textBuffer.mouseMoved(row, wordBegin, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.markerCol, wordBegin)
    self.assertEqual(self.textBuffer.penRow, row)
    self.assertEqual(self.textBuffer.penCol, wordEnd)

    self.textBuffer.mouseMoved(row, wordBegin-1, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.penCol, 0)
    self.assertEqual(self.textBuffer.markerCol, wordEnd)
    self.assertEqual(self.textBuffer.penRow, row)
    self.assertEqual(self.textBuffer.penCol, 0)

    self.textBuffer.mouseMoved(row, 1, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.markerCol, wordEnd)
    self.assertEqual(self.textBuffer.penRow, row)
    self.assertEqual(self.textBuffer.penCol, 0)

    self.textBuffer.mouseMoved(row+1, 0, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.markerCol, wordBegin)
    self.assertEqual(self.textBuffer.penRow, row+1)
    self.assertEqual(self.textBuffer.penCol, 1)

    self.textBuffer.mouseMoved(row+1, 1, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.markerCol, wordBegin)
    self.assertEqual(self.textBuffer.penRow, row+1)
    self.assertEqual(self.textBuffer.penCol, 8)

    self.textBuffer.mouseMoved(row, 1, False, False, False)
    self.assertEqual(self.textBuffer.markerRow, row)
    self.assertEqual(self.textBuffer.markerCol, wordEnd)
    self.assertEqual(self.textBuffer.penRow, row)
    self.assertEqual(self.textBuffer.penCol, 0)
