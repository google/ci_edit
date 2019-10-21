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

def checkRow(test, text_buffer, row, expected):
    text_buffer.parseDocument()
    if not (expected == text_buffer.parser.rowText(row)):
        test.fail("\n\nExpected these to match: "
            "row {}: expected {}, parser {}".format(
                row, repr(expected),
                repr(text_buffer.parser.data)))


class ActionsTestCase(unittest.TestCase):

    def currentRowText(self):
        return self.textBuffer.parser.rowText(self.textBuffer.penRow)

    def setMarkerPenRowCol(self, mRow, mCol, row, col):
        self.assertTrue(isinstance(mRow, int))
        self.assertTrue(isinstance(mCol, int))
        self.assertTrue(isinstance(row, int))
        self.assertTrue(isinstance(col, int))
        self.assertTrue(hasattr(self.textBuffer, "markerRow"))
        self.assertTrue(hasattr(self.textBuffer, "markerCol"))
        self.assertTrue(hasattr(self.textBuffer, "penRow"))
        self.assertTrue(hasattr(self.textBuffer, "penCol"))
        self.assertTrue(hasattr(self.textBuffer, "goalCol"))
        self.textBuffer.markerRow = mRow
        self.textBuffer.markerCol = mCol
        self.textBuffer.penRow = row
        self.textBuffer.penCol = col
        self.textBuffer.goalCol = col

    def markerPenRowCol(self):
        return (self.textBuffer.markerRow, self.textBuffer.markerCol,
                self.textBuffer.penRow, self.textBuffer.penCol)


class MouseTestCases(ActionsTestCase):

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
        self.textBuffer.parseDocument()
        #self.assertEqual(self.textBuffer.scrollRow, 0)
        #self.assertEqual(self.textBuffer.scrollCol, 0)
        self.assertEqual(self.textBuffer.parser.rowText(1), 'two')

    def tearDown(self):
        self.textBuffer = None

    def test_mouse_selection(self):
        self.textBuffer.mouseClick(3, 9, False, False, False)
        self.assertEqual(self.textBuffer.penRow, 3)
        self.assertEqual(self.textBuffer.penCol, 9)

        self.textBuffer.mouseClick(3, 8, True, False, False)
        self.assertEqual(self.markerPenRowCol(), (3, 9, 3, 8))

        self.textBuffer.mouseClick(4, 8, True, False, False)
        self.assertEqual(self.markerPenRowCol(), (3, 9, 4, 8))

        self.textBuffer.mouseClick(3, 8, True, False, False)
        self.assertEqual(self.markerPenRowCol(), (3, 9, 3, 8))

        self.textBuffer.mouseClick(4, 8, True, False, False)
        self.textBuffer.mouseClick(4, 9, True, False, False)
        self.assertEqual(self.markerPenRowCol(), (3, 9, 4, 9))

        self.textBuffer.mouseClick(4, 10, True, False, False)
        self.assertEqual(self.markerPenRowCol(), (3, 9, 4, 10))

        self.textBuffer.mouseClick(4, 11, True, False, False)
        self.assertEqual(self.markerPenRowCol(), (3, 9, 4, 11))

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



class SelectionTestCases(ActionsTestCase):

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
\ta\t
a\twith tab
\t\t
\twhile
{
"""
        self.textBuffer.setFileType(u"text")
        self.textBuffer.insertLines(tuple(test.split('\n')))
        self.textBuffer.parseDocument()
        #self.textBuffer.parser.debugLog(print, test)
        #self.assertEqual(self.textBuffer.scrollRow, 0)
        #self.assertEqual(self.textBuffer.scrollCol, 0)
        self.assertEqual(self.textBuffer.parser.rowText(1), 'two')
        self.assertEqual(self.textBuffer.parser.rowTextAndWidth(8),
                ('\t\t', 16))

    def test_cursor_col_delta(self):
        self.setMarkerPenRowCol(0, 0, 0, 2)
        self.assertEqual(self.textBuffer.cursorColDelta(4), 0)
        self.assertEqual(self.textBuffer.cursorColDelta(6), -2)
        self.setMarkerPenRowCol(0, 0, 0, 12)
        self.assertEqual(self.textBuffer.cursorColDelta(4), 0)
        self.assertEqual(self.textBuffer.cursorColDelta(6), -3)

    def test_cursor_move(self):
        self.setMarkerPenRowCol(0, 0, 2, 5)
        self.assertEqual(self.currentRowText(), u"// second comment")
        self.textBuffer.cursorMoveLeft()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 2, 4))
        self.textBuffer.cursorMoveRight()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 2, 5))

        self.setMarkerPenRowCol(0, 0, 8, 16)
        self.assertEqual(self.currentRowText(), u"\t\t")
        self.textBuffer.cursorMoveLeft()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 8, 8))
        self.textBuffer.cursorMoveLeft()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 8, 0))
        self.textBuffer.cursorMoveLeft()
        self.assertEqual(self.currentRowText(), u"a\twith tab")
        self.assertEqual(self.markerPenRowCol(), (0, 0, 7, 16))
        self.textBuffer.cursorMoveRight()
        self.assertEqual(self.currentRowText(), u"\t\t")
        self.assertEqual(self.markerPenRowCol(), (0, 0, 8, 0))
        self.textBuffer.cursorMoveRight()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 8, 8))
        self.textBuffer.cursorMoveRight()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 8, 16))
        self.textBuffer.cursorMoveRight()
        self.assertEqual(self.currentRowText(), u"\twhile")
        self.assertEqual(self.markerPenRowCol(), (0, 0, 9, 0))
        self.textBuffer.cursorMoveRight()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 9, 8))
        self.textBuffer.cursorMoveRight()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 9, 9))
        self.textBuffer.cursorMoveRight()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 9, 10))
        self.textBuffer.cursorMoveUpOrBegin()
        self.assertEqual(self.currentRowText(), u"\t\t")
        self.assertEqual(self.markerPenRowCol(), (0, 0, 8, 8))
        self.textBuffer.cursorMoveUpOrBegin()
        self.assertEqual(self.currentRowText(), u"a\twith tab")
        # The column is 10 because of the prior move right which set goalCol.
        self.assertEqual(self.markerPenRowCol(), (0, 0, 7, 10))
        self.textBuffer.cursorMoveLeft()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 7, 9))
        self.textBuffer.cursorMoveLeft()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 7, 8))
        self.textBuffer.cursorMoveLeft()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 7, 1))
        self.textBuffer.cursorMoveDownOrEnd()
        self.assertEqual(self.currentRowText(), u"\t\t")
        self.assertEqual(self.markerPenRowCol(), (0, 0, 8, 0))

    def test_backspace(self):
        self.setMarkerPenRowCol(0, 0, 6, 8)
        self.assertEqual(self.currentRowText(), u"\ta\t")
        self.textBuffer.backspace()
        self.textBuffer.parseDocument()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 6, 0))
        self.assertEqual(self.currentRowText(), u"a\t")
        self.textBuffer.cursorMoveRight()
        self.assertEqual(self.markerPenRowCol(), (0, 0, 6, 1))

    def test_cursor_select_word_left(self):
        tb = self.textBuffer
        self.setMarkerPenRowCol(0, 0, 2, 5)

        self.assertEqual(self.currentRowText(), u"// second comment")
        self.textBuffer.cursorSelectWordLeft()
        self.assertEqual(self.markerPenRowCol(), (2, 5, 2, 3))

        self.textBuffer.cursorSelectWordLeft()
        self.assertEqual(self.markerPenRowCol(), (2, 5, 2, 0))

        self.textBuffer.cursorSelectWordLeft()
        self.assertEqual(self.markerPenRowCol(), (2, 5, 1, 3))

        self.textBuffer.cursorSelectWordLeft()
        self.assertEqual(self.markerPenRowCol(), (2, 5, 1, 0))

        self.textBuffer.cursorSelectWordLeft()
        self.assertEqual(self.markerPenRowCol(), (2, 5, 0, 19))

        self.textBuffer.cursorSelectWordLeft()
        self.assertEqual(self.markerPenRowCol(), (2, 5, 0, 16))

        self.textBuffer.cursorSelectWordLeft()
        self.assertEqual(self.markerPenRowCol(), (2, 5, 0, 9))

        self.textBuffer.cursorSelectWordLeft()
        self.assertEqual(self.markerPenRowCol(), (2, 5, 0, 8))

        self.textBuffer.cursorSelectWordLeft()
        self.assertEqual(self.markerPenRowCol(), (2, 5, 0, 3))

        self.textBuffer.cursorSelectWordLeft()
        self.assertEqual(self.markerPenRowCol(), (2, 5, 0, 0))

        # Top of document. This call should have no effect (and not crash).
        self.textBuffer.cursorSelectWordLeft()
        self.assertEqual(self.markerPenRowCol(), (2, 5, 0, 0))


class TextIndentTestCases(ActionsTestCase):

    def setUp(self):
        app.log.shouldWritePrintLog = False
        self.prg = app.ci_program.CiProgram()
        self.textBuffer = app.text_buffer.TextBuffer(self.prg)
        self.textBuffer.setView(FakeView())
        #self.assertEqual(self.textBuffer.scrollRow, 0)
        #self.assertEqual(self.textBuffer.scrollCol, 0)

    def tearDown(self):
        self.textBuffer = None

    def test_auto_indent(self):
        self.prg.prefs.editor['autoInsertClosingCharacter'] = False
        def insert(*args):
            self.textBuffer.insertPrintableWithPairing(*args)
            self.textBuffer.parseDocument()
        tb = self.textBuffer
        self.assertEqual(tb.parser.rowCount(), 1)
        insert(ord('a'), None)
        insert(ord(':'), None)
        self.assertEqual(tb.penRow, 0)
        tb.carriageReturn()
        self.assertEqual(tb.penRow, 1)
        checkRow(self, tb, 0, 'a:')
        checkRow(self, tb, 1, '')

        # Replace member function to return a grammar with and indent.
        def grammarAt(row, col):
            return {'indent': '  '}

        tb.parser.grammarAt = grammarAt
        tb.backspace()
        tb.carriageReturn()
        checkRow(self, tb, 0, 'a:')
        checkRow(self, tb, 1, '  ')
        insert(ord('b'), None)
        insert(ord(':'), None)
        tb.carriageReturn()
        insert(ord('c'), None)
        insert(ord(':'), None)
        tb.carriageReturn()
        checkRow(self, tb, 0, 'a:')
        checkRow(self, tb, 1, '  b:')
        checkRow(self, tb, 2, '    c:')

    def test_indent_unindent_lines(self):
        def insert(*args):
            self.textBuffer.insertPrintableWithPairing(*args)
            self.textBuffer.parseDocument()
        tb = self.textBuffer
        self.assertEqual(tb.parser.rowCount(), 1)
        insert(ord('a'), None)
        tb.carriageReturn()
        insert(ord('b'), None)
        tb.carriageReturn()
        insert(ord('c'), None)
        tb.carriageReturn()
        insert(ord('d'), None)
        tb.carriageReturn()
        checkRow(self, tb, 0, 'a')
        checkRow(self, tb, 1, 'b')
        checkRow(self, tb, 2, 'c')
        checkRow(self, tb, 3, 'd')
        tb.penRow = 1
        tb.markerRow = 2
        tb.indentLines()
        checkRow(self, tb, 0, 'a')
        checkRow(self, tb, 1, '  b')
        checkRow(self, tb, 2, '  c')
        checkRow(self, tb, 3, 'd')
        tb.penRow = 0
        tb.markerRow = 3
        tb.indentLines()
        checkRow(self, tb, 0, '  a')
        checkRow(self, tb, 1, '    b')
        checkRow(self, tb, 2, '    c')
        checkRow(self, tb, 3, '  d')
        tb.unindentLines()
        checkRow(self, tb, 0, 'a')
        checkRow(self, tb, 1, '  b')
        checkRow(self, tb, 2, '  c')
        checkRow(self, tb, 3, 'd')
        tb.unindentLines()
        checkRow(self, tb, 0, 'a')
        checkRow(self, tb, 1, 'b')
        checkRow(self, tb, 2, 'c')
        checkRow(self, tb, 3, 'd')
        tb.penRow = 1
        tb.markerRow = 1
        tb.indentLines()
        checkRow(self, tb, 0, 'a')
        checkRow(self, tb, 1, '  b')
        checkRow(self, tb, 2, 'c')
        checkRow(self, tb, 3, 'd')
        tb.indentLines()
        checkRow(self, tb, 0, 'a')
        checkRow(self, tb, 1, '    b')
        checkRow(self, tb, 2, 'c')
        checkRow(self, tb, 3, 'd')
        tb.unindentLines()
        checkRow(self, tb, 0, 'a')
        checkRow(self, tb, 1, '  b')
        checkRow(self, tb, 2, 'c')
        checkRow(self, tb, 3, 'd')
        tb.penRow = 3
        tb.markerRow = 3
        tb.indentLines()
        checkRow(self, tb, 0, 'a')
        checkRow(self, tb, 1, '  b')
        checkRow(self, tb, 2, 'c')
        checkRow(self, tb, 3, '  d')
        tb.penRow = 0
        tb.markerRow = 3
        tb.indentLines()
        checkRow(self, tb, 0, '  a')
        checkRow(self, tb, 1, '    b')
        checkRow(self, tb, 2, '  c')
        checkRow(self, tb, 3, '    d')
        tb.penRow = 3
        tb.markerRow = 3
        tb.unindentLines()
        checkRow(self, tb, 0, '  a')
        checkRow(self, tb, 1, '    b')
        checkRow(self, tb, 2, '  c')
        checkRow(self, tb, 3, '  d')
        tb.unindentLines()
        checkRow(self, tb, 0, '  a')
        checkRow(self, tb, 1, '    b')
        checkRow(self, tb, 2, '  c')
        checkRow(self, tb, 3, 'd')
        tb.unindentLines()
        checkRow(self, tb, 0, '  a')
        checkRow(self, tb, 1, '    b')
        checkRow(self, tb, 2, '  c')
        checkRow(self, tb, 3, 'd')
        tb.penRow = 0
        tb.markerRow = 0
        tb.unindentLines()
        checkRow(self, tb, 0, 'a')
        checkRow(self, tb, 1, '    b')
        checkRow(self, tb, 2, '  c')
        checkRow(self, tb, 3, 'd')
        tb.unindentLines()
        checkRow(self, tb, 0, 'a')
        checkRow(self, tb, 1, '    b')
        checkRow(self, tb, 2, '  c')
        checkRow(self, tb, 3, 'd')

    def test_indent_unindent_lines2(self):

        def insert(input):
            for i in input:
                if i == u"\n":
                    self.textBuffer.carriageReturn()
                else:
                    self.textBuffer.insertPrintableWithPairing(ord(i), None)
                    self.textBuffer.parseDocument()
            self.assertEqual(self.textBuffer.parser.data, input)

        def checkPenMarker(penRow, penCol, markerRow, markerCol):
            self.assertEqual((penRow, penCol, markerRow, markerCol), (
                    tb.penRow, tb.penCol, tb.markerRow, tb.markerCol))

        def selectChar(penRow, penCol, markerRow, markerCol):
            self.textBuffer.penRow = penRow
            self.textBuffer.penCol = penCol
            self.textBuffer.markerRow = markerRow
            self.textBuffer.markerCol = markerCol
            self.textBuffer.selectionMode = app.selectable.kSelectionCharacter

        tb = self.textBuffer
        self.assertEqual(tb.parser.rowCount(), 1)
        checkPenMarker(0, 0, 0, 0)
        insert(u"apple\nbanana\ncarrot\ndate\neggplant\n")
        checkRow(self, tb, 0, 'apple')
        checkRow(self, tb, 1, 'banana')
        checkRow(self, tb, 2, 'carrot')
        checkRow(self, tb, 3, 'date')
        checkRow(self, tb, 4, 'eggplant')
        selectChar(0, 3, 2, 2)
        checkPenMarker(0, 3, 2, 2)
        tb.indent()
        checkRow(self, tb, 0, '  apple')
        checkRow(self, tb, 1, '  banana')
        checkRow(self, tb, 2, '  carrot')
        checkRow(self, tb, 3, 'date')
        checkRow(self, tb, 4, 'eggplant')
        checkPenMarker(0, 5, 2, 4)
        tb.indent()
        checkRow(self, tb, 0, '    apple')
        checkRow(self, tb, 1, '    banana')
        checkRow(self, tb, 2, '    carrot')
        checkRow(self, tb, 3, 'date')
        checkRow(self, tb, 4, 'eggplant')
        checkPenMarker(0, 7, 2, 6)

        selectChar(0, 3, 0, 2)
        tb.unindent()
        checkRow(self, tb, 0, '  apple')
        checkRow(self, tb, 1, '    banana')
        checkRow(self, tb, 2, '    carrot')
        checkRow(self, tb, 3, 'date')
        checkRow(self, tb, 4, 'eggplant')
        checkPenMarker(0, 1, 0, 0)

        selectChar(0, 3, 2, 2)
        tb.indent()
        checkRow(self, tb, 0, '    apple')
        checkRow(self, tb, 1, '      banana')
        checkRow(self, tb, 2, '      carrot')
        checkRow(self, tb, 3, 'date')
        checkRow(self, tb, 4, 'eggplant')
        checkPenMarker(0, 5, 2, 4)
        tb.indent()
        checkPenMarker(0, 7, 2, 6)
        tb.indent()
        checkPenMarker(0, 9, 2, 8)

class TextInsertTestCases(ActionsTestCase):

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
        def insert(*args):
            self.textBuffer.insertPrintableWithPairing(*args)
            self.textBuffer.parseDocument()
        tb = self.textBuffer
        insert(ord('o'), None)
        insert(ord('('), None)
        checkRow(self, tb, 0, 'o(')
        insert(ord('a'), None)
        checkRow(self, tb, 0, 'o(a')
        tb.editUndo()
        checkRow(self, tb, 0, 'o(')
        tb.editUndo()
        checkRow(self, tb, 0, 'o')
        tb.editUndo()
        checkRow(self, tb, 0, '')
        # Don't insert pair if the next char is not whitespace.
        insert(ord('o'), None)
        checkRow(self, tb, 0, 'o')
        tb.cursorLeft()
        checkRow(self, tb, 0, 'o')
        insert(ord('('), None)
        checkRow(self, tb, 0, '(o')

    def test_auto_insert_pair_enable(self):
        self.prg.prefs.editor['autoInsertClosingCharacter'] = True
        def insert(*args):
            self.textBuffer.insertPrintableWithPairing(*args)
            self.textBuffer.parseDocument()
        tb = self.textBuffer
        insert(ord('o'), None)
        insert(ord('('), None)
        checkRow(self, tb, 0, 'o()')
        insert(ord('a'), None)
        checkRow(self, tb, 0, 'o(a)')
        tb.editUndo()
        checkRow(self, tb, 0, 'o()')
        tb.editUndo()
        checkRow(self, tb, 0, '')
        # Don't insert pair if the next char is not whitespace.
        insert(ord('o'), None)
        checkRow(self, tb, 0, 'o')
        tb.cursorLeft()
        checkRow(self, tb, 0, 'o')
        insert(ord('('), None)
        checkRow(self, tb, 0, '(o')

class GrammarDeterminationTestCases(ActionsTestCase):

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
