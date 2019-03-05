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
    unicode
except NameError:
    unicode = str
    unichr = chr

import curses

import app.curses_util
import app.log
import app.window


class DebugWindow(app.window.ActiveWindow):

    def __init__(self, program, host):
        app.window.ActiveWindow.__init__(self, program, host)

    def debugDraw(self, program, win):
        """Draw real-time debug information to the screen."""
        textBuffer = win.textBuffer
        self.writeLineRow = 0
        intent = u"noIntent"
        if hasattr(win, u"userIntent"):
            intent = win.userIntent
        color = program.color.get(u'debug_window')
        self.writeLine(
            u"   cRow %3d    cCol %2d goalCol %2d  %s" %
            (win.textBuffer.penRow, win.textBuffer.penCol,
             win.textBuffer.goalCol, intent), color)
        self.writeLine(
            u"   pRow %3d    pCol %2d chRow %4d" %
            (textBuffer.penRow, textBuffer.penCol,
             textBuffer.debugUpperChangedRow), color)
        self.writeLine(
            u" mkrRow %3d  mkrCol %2d sm %d" %
            (textBuffer.markerRow, textBuffer.markerCol,
             textBuffer.selectionMode), color)
        self.writeLine(
            u"scrlRow %3d scrlCol %2d lines %3d" % (win.scrollRow, win.scrollCol,
                                                   len(textBuffer.lines)),
            color)
        y, x = win.top, win.left
        maxRow, maxCol = win.rows, win.cols
        self.writeLine(
            u"y %2d x %2d maxRow %d maxCol %d baud %d color %d" %
            (y, x, maxRow, maxCol, curses.baudrate(),
             curses.can_change_color()), color)
        screenRows, screenCols = program.cursesScreen.getmaxyx()
        self.writeLine(
            u"scr rows %d cols %d mlt %f/%f pt %f" %
            (screenRows, screenCols, program.mainLoopTime,
             program.mainLoopTimePeak, textBuffer.parserTime), color)
        self.writeLine(
            u"ch %3s %s" % (program.ch, app.curses_util.cursesKeyName(program.ch)
                           or u'UNKNOWN'), color)
        self.writeLine(u"win %r" % (win,), color)
        self.writeLine(u"foc %r" % (program.programWindow.focusedWindow,), color)
        self.writeLine(u"tb %r" % (textBuffer,), color)
        (id, mouseCol, mouseRow, mouseZ, bState) = program.debugMouseEvent
        self.writeLine(
            u"mouse id %d, mouseCol %d, mouseRow %d, mouseZ %d" %
            (id, mouseCol, mouseRow, mouseZ), color)
        self.writeLine(
            u"bState %s %d" % (app.curses_util.mouseButtonName(bState), bState),
            color)
        self.writeLine(u"startAndEnd %r" % (textBuffer.startAndEnd(),), color)


class DebugUndoWindow(app.window.ActiveWindow):

    def __init__(self, program, host):
        app.window.ActiveWindow.__init__(self, program, host)

    def debugUndoDraw(self, win):
        """Draw real-time debug information to the screen."""
        textBuffer = win.textBuffer
        self.writeLineRow = 0
        # Display some of the redo chain.
        colorPrefs = win.program.color
        redoColorA = colorPrefs.get(100)
        self.writeLine(
            u"procTemp %d temp %r" % (
                textBuffer.processTempChange,
                textBuffer.tempChange,
            ), redoColorA)
        self.writeLine(
            u"redoIndex %3d savedAt %3d depth %3d" %
            (textBuffer.redoIndex, textBuffer.savedAtRedoIndex,
             len(textBuffer.redoChain)), redoColorA)
        redoColorB = colorPrefs.get(101)
        split = 8
        for i in range(textBuffer.redoIndex - split, textBuffer.redoIndex):
            text = i >= 0 and repr(textBuffer.redoChain[i]) or u''
            self.writeLine(unicode(text), redoColorB)
        redoColorC = colorPrefs.get(1)
        for i in range(textBuffer.redoIndex, textBuffer.redoIndex + split - 1):
            text = (i < len(textBuffer.redoChain) and textBuffer.redoChain[i] or
                    '')
            self.writeLine(unicode(text), redoColorC)
