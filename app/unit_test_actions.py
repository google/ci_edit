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

import os
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
        self.prg = app.ci_program.CiProgram()
        self.textBuffer = app.text_buffer.TextBuffer(self.prg)
        self.textBuffer.setView(FakeView())
        test = """/* first comment */
two
// second comment
apple banana carrot
#include "test.h"
void blah();
"""
        self.textBuffer.insertLines(tuple(test.split('\n')))
        #self.assertEqual(self.textBuffer.scrollRow, 0)
        #self.assertEqual(self.textBuffer.scrollCol, 0)
        self.assertEqual(self.textBuffer.lines[1], 'two')

    def tearDown(self):
        self.textBuffer = None

    def test_mouse_selection(self):
        self.textBuffer.mouseClick(3, 9, False, False, False)
        self.assertEqual(self.textBuffer.penRow, 3)
        self.assertEqual(self.textBuffer.penCol, 9)

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

        self.textBuffer.mouseDoubleClick(row, col - 1, False, False, False)
        self.assertEqual(self.textBuffer.markerRow, row)
        self.assertEqual(self.textBuffer.markerCol, wordBegin)
        self.assertEqual(self.textBuffer.penRow, row)
        self.assertEqual(self.textBuffer.penCol, wordEnd)

        self.textBuffer.mouseMoved(row, wordBegin, False, False, False)
        self.assertEqual(self.textBuffer.markerRow, row)
        self.assertEqual(self.textBuffer.markerCol, wordBegin)
        self.assertEqual(self.textBuffer.penRow, row)
        self.assertEqual(self.textBuffer.penCol, wordEnd)

        self.textBuffer.mouseMoved(row, wordBegin - 1, False, False, False)
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

        self.textBuffer.mouseMoved(row + 1, 0, False, False, False)
        self.assertEqual(self.textBuffer.markerRow, row)
        self.assertEqual(self.textBuffer.markerCol, wordBegin)
        self.assertEqual(self.textBuffer.penRow, row + 1)
        self.assertEqual(self.textBuffer.penCol, 1)

        self.textBuffer.mouseMoved(row + 1, 1, False, False, False)
        self.assertEqual(self.textBuffer.markerRow, row)
        self.assertEqual(self.textBuffer.markerCol, wordBegin)
        self.assertEqual(self.textBuffer.penRow, row + 1)
        self.assertEqual(self.textBuffer.penCol, 8)

        self.textBuffer.mouseMoved(row, 1, False, False, False)
        self.assertEqual(self.textBuffer.markerRow, row)
        self.assertEqual(self.textBuffer.markerCol, wordEnd)
        self.assertEqual(self.textBuffer.penRow, row)
        self.assertEqual(self.textBuffer.penCol, 0)


class TextIndentTestCases(unittest.TestCase):

    def setUp(self):
        app.log.shouldWritePrintLog = False
        self.prg = app.ci_program.CiProgram()
        self.textBuffer = app.text_buffer.TextBuffer(self.prg)
        self.textBuffer.setView(FakeView())
        #self.assertEqual(self.textBuffer.scrollRow, 0)
        #self.assertEqual(self.textBuffer.scrollCol, 0)

    def tearDown(self):
        self.textBuffer = None

    def test_auto_insert_pair_disable(self):

        class FakeParser:

            def grammarAt(self, row, col):
                return {'indent': '  '}

            def rowTextAndWidth(self, row):
                return (u"hello", len(u"hello"))

        self.prg.prefs.editor['autoInsertClosingCharacter'] = False
        tb = self.textBuffer
        insert = self.textBuffer.insertPrintableWithPairing
        self.assertEqual(len(tb.lines), 1)
        insert(ord('a'), None)
        insert(ord(':'), None)
        tb.carriageReturn()
        self.assertEqual(tb.lines[0], 'a:')
        self.assertEqual(tb.lines[1], '')
        tb.parser = FakeParser()
        tb.backspace()
        tb.carriageReturn()
        self.assertEqual(tb.lines[0], 'a:')
        self.assertEqual(tb.lines[1], '  ')
        insert(ord('b'), None)
        insert(ord(':'), None)
        tb.carriageReturn()
        insert(ord('c'), None)
        insert(ord(':'), None)
        tb.carriageReturn()
        self.assertEqual(tb.lines[0], 'a:')
        self.assertEqual(tb.lines[1], '  b:')
        self.assertEqual(tb.lines[2], '    c:')


class TextInsertTestCases(unittest.TestCase):

    def setUp(self):
        app.log.shouldWritePrintLog = False
        self.prg = app.ci_program.CiProgram()
        self.textBuffer = app.text_buffer.TextBuffer(self.prg)
        self.textBuffer.setView(FakeView())
        #self.assertEqual(self.textBuffer.scrollRow, 0)
        #self.assertEqual(self.textBuffer.scrollCol, 0)

    def tearDown(self):
        self.textBuffer = None

    def test_auto_insert_pair_disable(self):
        self.prg.prefs.editor['autoInsertClosingCharacter'] = False
        tb = self.textBuffer
        insert = self.textBuffer.insertPrintableWithPairing
        self.assertEqual(len(tb.lines), 1)
        insert(ord('o'), None)
        insert(ord('('), None)
        self.assertEqual(tb.lines[0], 'o(')
        insert(ord('a'), None)
        self.assertEqual(tb.lines[0], 'o(a')
        tb.editUndo()
        self.assertEqual(tb.lines[0], 'o(')
        tb.editUndo()
        self.assertEqual(tb.lines[0], 'o')
        tb.editUndo()
        self.assertEqual(tb.lines[0], '')
        # Don't insert pair if the next char is not whitespace.
        insert(ord('o'), None)
        self.assertEqual(tb.lines[0], 'o')
        tb.cursorLeft()
        self.assertEqual(tb.lines[0], 'o')
        insert(ord('('), None)
        self.assertEqual(tb.lines[0], '(o')

    def test_auto_insert_pair_enable(self):
        self.prg.prefs.editor['autoInsertClosingCharacter'] = True
        tb = self.textBuffer
        insert = self.textBuffer.insertPrintableWithPairing
        self.assertEqual(len(tb.lines), 1)
        insert(ord('o'), None)
        insert(ord('('), None)
        self.assertEqual(tb.lines[0], 'o()')
        insert(ord('a'), None)
        self.assertEqual(tb.lines[0], 'o(a)')
        tb.editUndo()
        self.assertEqual(tb.lines[0], 'o()')
        tb.editUndo()
        self.assertEqual(tb.lines[0], '')
        # Don't insert pair if the next char is not whitespace.
        insert(ord('o'), None)
        self.assertEqual(tb.lines[0], 'o')
        tb.cursorLeft()
        self.assertEqual(tb.lines[0], 'o')
        insert(ord('('), None)
        self.assertEqual(tb.lines[0], '(o')

class GrammarDeterminationTestCases(unittest.TestCase):

    def setUp(self):
        app.log.shouldWritePrintLog = False
        self.prg = app.ci_program.CiProgram()
        self.textBuffer = app.text_buffer.TextBuffer(self.prg)
        self.textBuffer.setView(FakeView())

    def tearDown(self):
        self.textBuffer = None

    def test_message_backspace(self):
        tb = self.textBuffer
        self.assertEqual(tb._determineRootGrammar(*os.path.splitext("test.cc")),
            self.prg.prefs.grammars.get(self.prg.prefs.extensions.get('.cc')))
