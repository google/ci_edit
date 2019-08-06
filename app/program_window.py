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

import curses
import os
import signal
import sys

import app.curses_util
import app.debug_window
import app.file_manager_window
import app.log
import app.prediction_window
import app.window


class ProgramWindow(app.window.ActiveWindow):
    """The outermost window. This window doesn't draw content itself. It is
    primarily a container the child windows that make up the UI. The program
    window is expected to be a singleton. The program window has no parent (the
    parent is None). Calls that propagate up the window tree stop here or jump
    over to the |program|."""

    def __init__(self, program):
        if app.config.strict_debug:
            assert issubclass(program.__class__, app.ci_program.CiProgram), self
        app.window.ActiveWindow.__init__(self, program, None)
        self.clicks = 0
        self.modalUi = None
        self.program = program
        self.priorClick = 0
        self.savedMouseButton1Down = False
        self.savedMouseWindow = None
        self.savedMouseX = -1
        self.savedMouseY = -1
        self.showLogWindow = self.program.prefs.startup['showLogWindow']
        self.debugWindow = app.debug_window.DebugWindow(self.program, self)
        self.debugUndoWindow = app.debug_window.DebugUndoWindow(
            self.program, self)
        self.logWindow = app.window.LogWindow(self.program, self)
        self.popupWindow = app.window.PopupWindow(self.program, self)
        self.paletteWindow = app.window.PaletteWindow(self.program, self)
        # The input window is the main document window.
        self.inputWindow = app.window.InputWindow(self.program, self)
        self.inputWindow.parent = self
        # Set up file manager.
        self.fileManagerWindow = app.file_manager_window.FileManagerWindow(
            self.program, self, self.inputWindow)
        self.fileManagerWindow.parent = self
        # Set up prediction.
        self.predictionWindow = app.prediction_window.PredictionWindow(
            self.program, self)
        self.predictionWindow.parent = self
        # Put the input window in front on startup.
        self.inputWindow.reattach()

    def changeFocusTo(self, changeTo):
        self.focusedWindow.controller.onChange()
        # Unfocus all the windows from the prior focused window to the common
        # root.
        commonRoot = self.findCommonRoot(self.focusedWindow, changeTo)
        current = self.focusedWindow
        while current != commonRoot:
            if current.isFocusable:
                current.unfocus()
            current = current.parent
        self.setFocusedWindow(changeTo)

    def debugDraw(self, win):
        if self.showLogWindow:
            self.debugWindow.debugDraw(self.program, win)
            self.debugUndoWindow.debugUndoDraw(win)

    def executeCommandList(self, cmdList):
        for cmd, eventInfo in cmdList:
            self.doPreCommand()
            if cmd == curses.KEY_RESIZE:
                self.handleScreenResize(self.focusedWindow)
                continue
            self.focusedWindow.controller.doCommand(cmd, eventInfo)
            if cmd == curses.KEY_MOUSE:
                self.handleMouse(eventInfo)
            self.focusedWindow.controller.onChange()

    def findCommonRoot(self, first, second):
        """Find the Window that is the parent of both |first| and |second|. If
        |first| is a (grand*)parent of |second|, return |first| (or vice versa).
        """
        # assert self.focusedWindow is not changeTo
        if first is second:
            return first
        firstPath = [first]
        while firstPath[-1].parent:
            firstPath.append(firstPath[-1].parent)
            if firstPath[-1] == second:
                return second
        secondPath = [second]
        while secondPath[-1].parent:
            secondPath.append(secondPath[-1].parent)
            if secondPath[-1] == first:
                return first
        # assert firstPath[-1] is secondPath[-1]
        # Assumptions: The first unequal match will never be found at [-1]. A
        # match will always be found before exhausting the lists. It doesn't
        # matter which list is longer.
        for i in range(len(firstPath)):
            if firstPath[-(i + 1)] is not secondPath[-(i + 1)]:
                root = firstPath[-i]
                break
        return root

    def focus(self):
        self.setFocusedWindow(self.zOrder[-1])

    def setFocusedWindow(self, window):
        # Depth-first search for focusable window.
        depth = [window]
        while len(depth):
            possibility = depth.pop()
            if possibility.isFocusable:
                if app.config.strict_debug:
                    assert issubclass(possibility.__class__,
                                      app.window.ActiveWindow)
                    assert possibility.controller
                self.focusedWindow = possibility
                self.focusedWindow.focus()
                self.focusedWindow.textBuffer.compoundChangePush()
                return
            depth += possibility.zOrder
            app.log.info(depth)
        app.log.error("focusable window not found")

    def doPreCommand(self):
        # Reset UI elements that adjust when new commands are issued.
        # E.g. setMessage()
        win = self.focusedWindow
        while win is not None and win is not self:
            win.doPreCommand()
            win = win.parent

    def longTimeSlice(self):
        """returns whether work is finished (no need to call again)."""
        win = self.focusedWindow
        while win is not None and win is not self:
            if not win.longTimeSlice():
                return False
            win = win.parent
        return True

    def shortTimeSlice(self):
        """returns whether work is finished (no need to call again)."""
        win = self.focusedWindow
        while win is not None and win is not self:
            if not win.shortTimeSlice():
                return False
            #assert win is not win.parent
            win = win.parent
        return True

    def clickedNearby(self, row, col):
        y, x = self.priorClickRowCol
        return y - 1 <= row <= y + 1 and x - 1 <= col <= x + 1

    def handleMouse(self, info):
        """Mouse handling is a special case. The getch() curses function will
        signal the existence of a mouse event, but the event must be fetched and
        parsed separately."""
        (_, mouseCol, mouseRow, _, bState) = info[0]
        app.log.mouse()
        eventTime = info[1]
        rapidClickTimeout = .5

        def findWindow(parent, mouseRow, mouseCol):
            for window in reversed(parent.zOrder):
                if window.contains(mouseRow, mouseCol):
                    return findWindow(window, mouseRow, mouseCol)
            return parent

        window = findWindow(self, mouseRow, mouseCol)
        if window == self:
            app.log.mouse('click landed on screen')
            return
        if self.focusedWindow != window and window.isFocusable:
            app.log.debug('before change focus')
            window.changeFocusTo(window)
            app.log.debug('after change focus')
        mouseRow -= window.top
        mouseCol -= window.left
        app.log.mouse(mouseRow, mouseCol)
        app.log.mouse("\n", window)
        button1WasDown = self.savedMouseButton1Down
        self.savedMouseButton1Down = False
        #app.log.info('bState', app.curses_util.mouseButtonName(bState))
        if bState & curses.BUTTON1_RELEASED:
            if button1WasDown:
                app.log.mouse(bState, curses.BUTTON1_RELEASED)
                if self.priorClick + rapidClickTimeout <= eventTime:
                    window.mouseRelease(
                        mouseRow, mouseCol, bState & curses.BUTTON_SHIFT,
                        bState & curses.BUTTON_CTRL, bState & curses.BUTTON_ALT)
                #else:
                #  signal.setitimer(signal.ITIMER_REAL, rapidClickTimeout)
            else:
                # Some terminals (linux?) send BUTTON1_RELEASED after moving the
                # mouse. Specifically if the terminal doesn't use button 4 for
                # mouse movement. Mouse drag or mouse wheel movement done.
                pass
        elif bState & curses.BUTTON1_PRESSED:
            self.savedMouseButton1Down = True
            if (self.priorClick + rapidClickTimeout > eventTime and
                    self.clickedNearby(mouseRow, mouseCol)):
                self.clicks += 1
                self.priorClick = eventTime
                if self.clicks == 2:
                    window.mouseDoubleClick(
                        mouseRow, mouseCol, bState & curses.BUTTON_SHIFT,
                        bState & curses.BUTTON_CTRL, bState & curses.BUTTON_ALT)
                else:
                    window.mouseTripleClick(
                        mouseRow, mouseCol, bState & curses.BUTTON_SHIFT,
                        bState & curses.BUTTON_CTRL, bState & curses.BUTTON_ALT)
                    self.clicks = 1
            else:
                self.clicks = 1
                self.priorClick = eventTime
                self.priorClickRowCol = (mouseRow, mouseCol)
                window.mouseClick(
                    mouseRow, mouseCol, bState & curses.BUTTON_SHIFT,
                    bState & curses.BUTTON_CTRL, bState & curses.BUTTON_ALT)
        elif bState & curses.BUTTON2_PRESSED:
            window.mouseWheelUp(bState & curses.BUTTON_SHIFT,
                                bState & curses.BUTTON_CTRL,
                                bState & curses.BUTTON_ALT)
        elif bState & (curses.BUTTON4_PRESSED | curses.REPORT_MOUSE_POSITION):
            # Notes from testing:
            # Mac seems to send BUTTON4_PRESSED during mouse move; followed by
            #   BUTTON4_RELEASED.
            # Linux seems to send REPORT_MOUSE_POSITION during mouse move;
            # followed by
            #   BUTTON1_RELEASED.
            if self.savedMouseX == mouseCol and self.savedMouseY == mouseRow:
                if bState & curses.REPORT_MOUSE_POSITION:
                    # This is a hack for dtterm mouse wheel on Mac OS X.
                    window.mouseWheelUp(bState & curses.BUTTON_SHIFT,
                                        bState & curses.BUTTON_CTRL,
                                        bState & curses.BUTTON_ALT)
                else:
                    # This is the normal case:
                    window.mouseWheelDown(bState & curses.BUTTON_SHIFT,
                                          bState & curses.BUTTON_CTRL,
                                          bState & curses.BUTTON_ALT)
            else:
                if (self.savedMouseWindow and
                        self.savedMouseWindow is not window):
                    mouseRow += window.top - self.savedMouseWindow.top
                    mouseCol += window.left - self.savedMouseWindow.left
                    window = self.savedMouseWindow
                window.mouseMoved(
                    mouseRow, mouseCol, bState & curses.BUTTON_SHIFT,
                    bState & curses.BUTTON_CTRL, bState & curses.BUTTON_ALT)
        elif bState & curses.BUTTON4_RELEASED:
            # Mouse drag or mouse wheel movement done.
            pass
        else:
            app.log.mouse('got bState', app.curses_util.mouseButtonName(bState),
                          bState)
        self.savedMouseWindow = window
        self.savedMouseX = mouseCol
        self.savedMouseY = mouseRow

    def handleScreenResize(self, window):
        #app.log.debug('handleScreenResize -----------------------')
        if sys.platform == 'darwin':
            # Some terminals seem to resize the terminal and others leave it
            # to the application to resize the curses terminal.
            rows, cols = app.curses_util.terminalSize()
            curses.resizeterm(rows, cols)
        self.top = self.left = 0
        self.rows, self.cols = app.window.mainCursesWindow.getmaxyx()
        self.layout()
        window.controller.onChange()
        self.render()

    def hide(self):
        pass

    def layout(self):
        """Arrange the debug, log, and input windows."""
        rows, cols = self.rows, self.cols
        #app.log.detail('layout', rows, cols)
        if self.showLogWindow:
            inputWidth = min(88, cols)
            debugWidth = max(cols - inputWidth - 1, 0)
            debugRows = 20
            self.debugWindow.reshape(0, inputWidth + 1, debugRows, debugWidth)
            self.debugUndoWindow.reshape(debugRows, inputWidth + 1,
                                         rows - debugRows, debugWidth)
            self.logWindow.reshape(debugRows, 0, rows - debugRows, inputWidth)
            rows = debugRows
        else:
            inputWidth = cols
        if 1:  # Full screen.
            for window in self.zOrder:
                window.reshape(0, 0, rows, inputWidth)
        else:  # Split horizontally.
            count = len(self.zOrder)
            eachRows = rows // count
            for i, window in enumerate(self.zOrder[:-1]):
                window.reshape(eachRows * i, 0, eachRows, inputWidth)
            self.zOrder[-1].reshape(eachRows * (count - 1), 0,
                                    rows - eachRows * (count - 1), inputWidth)

    def nextFocusableWindow(self, start, reverse=False):
        # Keep the tab focus in the child branch. (The child view will call
        # this, tell the child there is nothing to tab to up here).
        return None

    def normalize(self):
        self.presentModal(None)

    def onPrefChanged(self, category, name):
        pass

    def presentModal(self, changeTo, top=0, left=0):
        if self.modalUi is not None:
            #self.modalUi.controller.onChange()
            self.modalUi.hide()
        app.log.info('\n', changeTo)
        self.modalUi = changeTo
        if self.modalUi is not None:
            self.modalUi.moveSizeToFit(top, left)
            self.modalUi.bringToFront()

    def quitNow(self):
        self.program.quitNow()

    def render(self):
        if self.showLogWindow:
            self.logWindow.render()
        app.window.ActiveWindow.render(self)
        window = self.focusedWindow
        self.debugDraw(window)
        penRow = window.textBuffer.penRow
        penCol = window.textBuffer.penCol
        if (window.showCursor and penRow >= window.scrollRow and
                penRow < window.scrollRow + window.rows):
            self.program.backgroundFrame.setCursor(
                (window.top + penRow - window.scrollRow,
                 window.left + penCol - window.scrollCol))
        else:
            self.program.backgroundFrame.setCursor(None)

    def reshape(self, top, left, rows, cols):
        app.window.ActiveWindow.reshape(self, top, left, rows, cols)
        self.layout()

    def bringToFront(self):
        pass

    def unfocus(self):
        pass
