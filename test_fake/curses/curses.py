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
"""A fake curses api intended for making tests. By creating a fake version of
the curses API the ci_edit code can be tested for various inputs and outputs.

The values of constants and function calls are bogus. This was created based on
what ci_edit uses, without regard or reference to the internals of the curses
library."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
try:
    unicode
except NameError:
    unicode = str
    unichr = chr

import inspect
import os
import signal
import sys
import time
import traceback
import types

from . import ascii
from . import constants

DEBUG_COLOR_PAIR_BASE = 256
DEBUG_COLOR_PAIR_MASK = (DEBUG_COLOR_PAIR_BASE * 2) - 1


def isStringType(value):
    if sys.version_info[0] == 2:
        return type(value) in types.StringTypes
    return type(value) is str


# Avoiding importing app.curses_util.
# Tuple events are preceded by an escape (27).
BRACKETED_PASTE_BEGIN = (91, 50, 48, 48, 126)  # i.e. "[200~"
BRACKETED_PASTE_END = (91, 50, 48, 49, 126)  # i.e. "[201~"
BRACKETED_PASTE = ("terminal_paste",)  # Pseudo event type.
MIN_DOUBLE_WIDE_CHARACTER = u"\u3000"
def columnWidth(string):
    """When rendering |string| how many character cells will be used? For ASCII
    characters this will equal len(string). For many Chinese characters and
    emoji the value will be greater than len(string), since many of them use two
    cells.
    """
    assert isinstance(string, unicode), repr(string)
    width = 0
    for i in string:
        if i > MIN_DOUBLE_WIDE_CHARACTER:
            width += 2
        else:
            width += 1
    return width


class error(BaseException):

    def __init__(self):
        BaseException.__init__(self)


class FakeInput:

    def __init__(self, display):
        self.fakeDisplay = display
        self.setInputs([])

    def setInputs(self, cmdList):
        self.inputs = cmdList
        self.inputsIndex = -1
        self.inBracketedPaste = False
        self.tupleIndex = -1
        self.waitingForRefresh = True
        self.isVerbose = False
        self.bgCounter = 1
        if self.isVerbose:
            print("")

    def log(self, *msg):
        if not self.isVerbose:
            return
        functionLine = inspect.stack()[1][2]
        function = inspect.stack()[1][3]
        frame = inspect.stack()[3]
        callingFile = os.path.split(frame[1])[1]
        callingLine = frame[2]
        caller = "%16s %5s %3s %s " % (callingFile, callingLine,
                                            function, functionLine)
        waiting = u"waitingForRefresh" if self.waitingForRefresh else ""
        print(caller + " ".join([repr(i) for i in msg]), waiting)

    def next(self):
        self.log("start")
        if self.waitingForRefresh:
            if self.bgCounter == 0:
                self.bgCounter = 1
                self.log("    ", self.bgCounter, 0)
                return 0
            self.bgCounter -= 1
            self.log("    ", self.bgCounter, -1)
            return -1
        self.bgCounter = 1
        if not self.waitingForRefresh:
            while self.inputsIndex + 1 < len(self.inputs):
                assert not self.waitingForRefresh
                self.inputsIndex += 1
                cmd = self.inputs[self.inputsIndex]
                if type(cmd) == types.FunctionType:
                    result = cmd(self.fakeDisplay, self.inputsIndex)
                    if result is not None:
                        self.waitingForRefresh = True
                        self.log("next(k)", repr(cmd)[:8], repr(result))
                        return result
                    self.log("next(f)", repr(cmd)[:8], repr(result))
                elif isStringType(cmd) and len(cmd) == 1:
                    if (not self.inBracketedPaste) and cmd != ascii.ESC:
                        self.waitingForRefresh = True
                    self.log("next(q) ", repr(cmd), ord(cmd))
                    return ord(cmd)
                elif (type(cmd) is tuple and len(cmd) > 1 and
                      type(cmd[0]) is int):
                    if cmd == BRACKETED_PASTE_BEGIN:
                        self.inBracketedPaste = True
                    self.log("next(s) ", cmd, type(cmd))
                    self.tupleIndex += 1
                    if self.tupleIndex >= len(cmd):
                        self.tupleIndex = -1
                        if cmd == BRACKETED_PASTE_END:
                            self.inBracketedPaste = False
                        if cmd != BRACKETED_PASTE_BEGIN:
                            self.waitingForRefresh = True
                        self.log("next(u)", cmd, type(cmd))
                        self.log("return", constants.ERR)
                        return constants.ERR
                    self.inputsIndex -= 1
                    self.log("return", cmd[self.tupleIndex])
                    return cmd[self.tupleIndex]
                else:
                    if (not self.inBracketedPaste) and cmd != ascii.ESC:
                        self.waitingForRefresh = True
                    self.log("return", cmd, type(cmd))
                    return cmd
        self.log("return", constants.ERR)
        return constants.ERR

def testLog(log_level, *msg):
    # Adjust constant to increase verbosity.
    if log_level >= 0:
        return
    functionLine = inspect.stack()[1][2]
    function = inspect.stack()[1][3]
    frame = inspect.stack()[2]
    callingFile = os.path.split(frame[1])[1]
    callingLine = frame[2]
    callingFunction = frame[3]
    caller = "%20s %5s %20s %3s %s " % (callingFile, callingLine,
                                        callingFunction, functionLine, function)
    print(caller + " ".join([repr(i) for i in msg]))


getchCallback = None


def setGetchCallback(callback):
    global getchCallback
    getchCallback = callback


# Test output. Use |display| to check the screen output.
class FakeDisplay:

    def __init__(self):
        self.rows = 15
        self.cols = 40
        self.colors = {}
        self.cursorRow = 0
        self.cursorCol = 0
        self.displayStyle = None
        self.displayText = None
        self.reset()

    def checkStyle(self, row, col, height, width, colorPair):
        #assert (colorPair & DEBUG_COLOR_PAIR_MASK) in self.colors.values()
        assert colorPair >= DEBUG_COLOR_PAIR_BASE
        for i in range(height):
            for k in range(width):
                d = self.displayStyle[row + i][col + k]
                if d != colorPair:
                    self.show()
                    return (
                        u"\n  row %s, col %s color/style mismatch '%d' != '%d'"
                        % (row + i, col + k, d, colorPair))
        return None

    def checkText(self, row, col, lines, verbose=3):
        assert isinstance(row, int)
        assert isinstance(col, int)
        assert isinstance(lines, list)
        assert isinstance(lines[0], unicode)
        assert isinstance(verbose, int)
        for i in range(len(lines)):
            line = lines[i]
            for k in range(len(line)):
                if row + i >= self.rows:
                    return u"\n  Row %d is outside of the %d row display" % (
                        row + i, self.rows)
                if col + k >= self.cols:
                    return (u"\n  Column %d is outside of the %d column display"
                            % (col + k, self.cols))
                d = self.displayText[row + i][col + k]
                c = line[k]
                if d != c:
                    #self.show()
                    result = u"\n  row %s, col %s mismatch '%s' != '%s'" % (
                        row + i, col + k, d, c)
                    if verbose >= 1:
                        actualLine = u"".join(self.displayText[row + i])
                        result += u"\n  actual:   |%s|" % actualLine
                    if verbose >= 2:
                        expectedText = u"".join(line)
                        result += u"\n  expected: %s|%s|" % (u" " * col,
                                                             expectedText)
                    if verbose >= 3:
                        result += u"\n  mismatch:  %*s^" % (col + k, u"")
                    return result
        return None

    def draw(self, cursorRow, cursorCol, text, colorPair):
        #assert (colorPair & DEBUG_COLOR_PAIR_MASK) in self.colors.values()
        assert isinstance(cursorRow, int)
        assert isinstance(cursorCol, int)
        assert isinstance(text, unicode)
        assert colorPair >= DEBUG_COLOR_PAIR_BASE
        for i in text:
            if i == '\r':
                cursorCol = 0
                continue
            try:
                self.displayText[cursorRow][cursorCol] = i
                self.displayStyle[cursorRow][cursorCol] = colorPair
                cursorCol += 1
                if columnWidth(i) > 1:
                    self.displayText[cursorRow][cursorCol] = u" "
                    self.displayStyle[cursorRow][cursorCol] = colorPair
                    cursorCol += 1
            except IndexError:
                raise error()
        return cursorRow, cursorCol

    def findText(self, screenText):
        assert isinstance(screenText, unicode)
        for row in range(len(self.displayText)):
            line = self.displayText[row]
            col = u"".join(line).find(screenText)
            if col != -1:
                return row, col
        print(u"Error: Did not find", screenText)
        self.show()
        return -1, -1

    def getColorPair(self, colorIndex):
        assert colorIndex < DEBUG_COLOR_PAIR_BASE
        colorPair = self.colors.setdefault(
            colorIndex, DEBUG_COLOR_PAIR_BASE + len(self.colors))
        return colorPair

    def getStyle(self):
        return [
            u"".join([
                unichr((c & DEBUG_COLOR_PAIR_MASK) - DEBUG_COLOR_PAIR_BASE + 91)
                for c in self.displayStyle[i]
            ])
            for i in range(self.rows)
        ]

    def getText(self):
        return [u"".join(self.displayText[i]) for i in range(self.rows)]

    def setScreenSize(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.reset()

    def show(self):
        assert self.displayStyle[0][0] != -1, \
            u"Error: showing display before drawing to it."
        print(u'   %*s   %s' % (-self.cols, u'display', u'style'))
        print(u'  +' + u'-' * self.cols + u'+ +' + u'-' * self.cols + u'+')
        for i, (line, styles) in enumerate(
                zip(self.getText(), self.getStyle())):
            print(u"%2d|%s| |%s|" % (i, line, styles))
        print(u'  +' + u'-' * self.cols + u'+ +' + u'-' * self.cols + u'+')

    def reset(self):
        self.displayStyle = [
            [-1 for _ in range(self.cols)] for _ in range(self.rows)
        ]
        self.displayText = [
            [u"x" for _ in range(self.cols)] for _ in range(self.rows)
        ]


fakeDisplay = None
fakeInput = None
mouseEvents = []


def getFakeDisplay():
    return fakeDisplay


def printFakeDisplay():
    fakeDisplay.show()


#####################################


class FakeCursesWindow:

    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.cursorRow = 0
        self.cursorCol = 0

    def addstr(self, *args):
        testLog(4, *args)
        cursorRow = args[0]
        cursorCol = args[1]
        assert isinstance(cursorRow, int)
        assert isinstance(cursorCol, int)
        assert isinstance(args[2], bytes), repr(args[2])
        text = args[2].decode("utf-8")
        color = args[3]
        assert isinstance(cursorRow, int)
        self.cursorRow, self.cursorCol = fakeDisplay.draw(
            cursorRow, cursorCol, text, color)

    def getch(self):
        testLog(4)
        if 1:
            if getchCallback:
                val = getchCallback()
                return val
        val = fakeInput.next()
        if self.movie and val != constants.ERR and val != 0:
            if val == 409:
                print(u"val", val, u"mouse_info", mouseEvents[-1])
            else:
                print(u"val", val)
        return val

    def getyx(self):
        testLog(2)
        return (self.cursorRow, self.cursorCol)

    def getmaxyx(self):
        testLog(2)
        return (fakeDisplay.rows, fakeDisplay.cols)

    def keypad(self, *args):
        testLog(2, *args)

    def leaveok(self, *args):
        testLog(2, *args)

    def move(self, a, b):
        testLog(2, a, b)
        self.cursorRow = a
        self.cursorCol = b

    def noutrefresh(self):
        pass

    def refresh(self):
        testLog(2)

    def resize(self, a, b):
        testLog(2, a, b)

    def scrollok(self, *args):
        testLog(2, *args)

    def timeout(self, *args):
        testLog(2, *args)


class StandardScreen(FakeCursesWindow):

    def __init__(self):
        global fakeDisplay, fakeInput
        testLog(2)
        FakeCursesWindow.__init__(self, 0, 0)
        self.cmdCount = -1
        fakeDisplay = FakeDisplay()
        self.fakeDisplay = fakeDisplay
        fakeInput = FakeInput(fakeDisplay)
        self.fakeInput = fakeInput
        self.movie = False

    def setFakeInputs(self, cmdList):
        self.fakeInput.setInputs(cmdList)

    def getmaxyx(self):
        testLog(2)
        return (self.fakeDisplay.rows, self.fakeDisplay.cols)

    def refresh(self, *args):
        testLog(2, *args)

    def test_find_text(self, screenText):
        return fakeDisplay.findText(screenText)

    def test_rendered_command_count(self, cmdCount):
        if self.cmdCount != cmdCount:
            fakeInput.waitingForRefresh = False
            self.cmdCount = cmdCount
            if self.movie:
                fakeDisplay.show()


def baudrate(*args):
    testLog(2, *args)
    return -1


def can_change_color(*args):
    testLog(2, *args)
    return 1


def color_content(*args):
    testLog(2, *args)


def color_pair(*args):
    testLog(2, *args)
    return fakeDisplay.getColorPair(*args)


def curs_set(*args):
    testLog(2, *args)


def errorpass(*args):
    testLog(2, *args)


def getch(*args):
    testLog(2, *args)
    return constants.ERR


def addMouseEvent(mouseEvent):
    testLog(2)
    return mouseEvents.append(mouseEvent)


def getmouse(*args):
    testLog(2, *args)
    return mouseEvents.pop()


def has_colors(*args):
    testLog(2, *args)
    return True


def init_color(*args):
    testLog(2, *args)


def init_pair(*args):
    testLog(4, *args)


def keyname(*args):
    testLog(2, *args)
    # Raise expected exception types.
    a = int(*args)  # ValueError.
    if a >= 2**31:
        raise OverflowError()
    if a < 0:
        raise ValueError()


def meta(*args):
    testLog(2, *args)


def mouseinterval(*args):
    testLog(2, *args)


def mousemask(*args):
    testLog(2, *args)


def newwin(*args):
    testLog(2, *args)
    return FakeCursesWindow(args[0], args[1])


def raw(*args):
    testLog(2, *args)


def resizeterm(*args):
    testLog(2, *args)


def start_color(*args):
    testLog(2, *args)


def ungetch(*args):
    testLog(2, *args)


def use_default_colors(*args):
    testLog(2, *args)


def get_pair(*args):
    fakeDisplay.getColorPair(*args)
    testLog(2, *args)


def wrapper(fun, *args, **kw):
    standardScreen = StandardScreen()
    fun(standardScreen, *args, **kw)
