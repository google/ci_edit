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


from .constants import *
import ascii
import app.curses_util
import inspect
import os
import signal
import sys
import time
import traceback
import types


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

  def next(self):
    if not self.waitingForRefresh:
      while self.inputsIndex + 1 < len(self.inputs):
        assert not self.waitingForRefresh
        self.inputsIndex += 1
        cmd = self.inputs[self.inputsIndex]
        if type(cmd) == types.FunctionType:
          result = cmd(self.fakeDisplay, self.inputsIndex)
          if result is not None:
            self.waitingForRefresh = True
            return result
        elif type(cmd) == types.StringType and len(cmd) == 1:
          if (not self.inBracketedPaste) and cmd != ascii.ESC:
            self.waitingForRefresh = True
          if self.isVerbose:
            print repr(cmd), ord(cmd)
          return ord(cmd)
        elif (type(cmd) == types.TupleType and len(cmd) > 1 and
            type(cmd[0]) == types.IntType):
          if cmd == app.curses_util.BRACKETED_PASTE_BEGIN:
            self.inBracketedPaste = True
          if self.isVerbose and self.tupleIndex == 0:
            print cmd, type(cmd)
          self.tupleIndex += 1
          if self.tupleIndex >= len(cmd):
            self.tupleIndex = -1
            if cmd == app.curses_util.BRACKETED_PASTE_END:
              self.inBracketedPaste = False
              self.waitingForRefresh = True
            return ERR
          self.inputsIndex -= 1
          return cmd[self.tupleIndex]
        else:
          if (not self.inBracketedPaste) and cmd != ascii.ESC:
            self.waitingForRefresh = True
          if self.isVerbose:
            print cmd, type(cmd)
          return cmd
    return ERR


def testLog(*msg):
  # Remove return to get function call trace.
  return
  functionLine = inspect.stack()[1][2]
  function = inspect.stack()[1][3]
  frame = inspect.stack()[2]
  callingFile = os.path.split(frame[1])[1]
  callingLine = frame[2]
  callingFunction = frame[3]
  caller = "%20s %5s %20s %3s %s " % (callingFile,
        callingLine, callingFunction, functionLine, function)
  print caller + " ".join([repr(i) for i in msg])


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

  def checkStyle(self, row, col, height, width, color):
    colorPair = self.colors.get(color)
    if colorPair is None:
      return "\n  color %s is not ready" % (color,)
    for i in range(height):
      for k in range(width):
        d = self.displayStyle[row + i][col + k]
        if d != colorPair:
          self.show()
          return "\n  row %s, col %s color/style mismatch '%d' != '%d'" % (
              row + i, col + k, d, colorPair)
    return None

  def checkText(self, row, col, lines, verbose=3):
    for i in range(len(lines)):
      line = lines[i]
      for k in range(len(line)):
        if row + i >= self.rows:
          return "\n  Row %d is outside of the %d row display" % (row + i,
              self.rows)
        if col + k >= self.cols:
          return "\n  Column %d is outside of the %d column display" % (col + k,
              self.cols)
        d = self.displayText[row + i][col + k]
        c = line[k]
        if d != c:
          self.show()
          result = "\n  row %s, col %s mismatch '%s' != '%s'" % (
              row + i, col + k, d, c)
          if verbose >= 1:
            actualLine = ''.join(self.displayText[row + i])
            result += unicode("\n  actual:   |%s|") % actualLine
          if verbose >= 2:
            expectedText = ''.join(line)
            expectedLine = (actualLine[:col] + expectedText +
                actualLine[col + len(expectedText):])
            result += unicode("\n  expected: |%s|") % expectedLine
          if verbose >= 3:
            result += unicode("\n  mismatch:  %*s^") % (col + k, '')
          return result
    return None


  def getColorPair(self, colorIndex):
    return self.colors.setdefault(colorIndex, 91 + len(self.colors))

  def getStyle(self):
    return [
      ''.join([unichr(c) for c in self.displayStyle[i]])
          for i in range(self.rows)
      ]

  def getText(self):
    return [''.join(self.displayText[i]) for i in range(self.rows)]

  def setScreenSize(self, rows, cols):
    self.rows = rows
    self.cols = cols
    self.reset()

  def show(self):
    print '   %*s   %s' % (-self.cols, 'display', 'style')
    print '  +' + '-' * self.cols + '+ +' + '-' * self.cols + '+'
    for i, (line, styles) in enumerate(zip(self.getText(), self.getStyle())):
      print "%2d|%s| |%s|" % (i, line, styles)
    print '  +' + '-' * self.cols + '+ +' + '-' * self.cols + '+'

  def reset(self):
    self.displayStyle = [
        [-1 for k in range(self.cols)] for i in range(self.rows)]
    self.displayText = [
        [u'x' for k in range(self.cols)] for i in range(self.rows)]

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
    global fakeDisplay
    try:
      testLog(*args)
      cursorRow = args[0]
      cursorCol = args[1]
      text = args[2].decode('utf-8')
      color = args[3]
      for i in range(len(text)):
        fakeDisplay.displayText[cursorRow][cursorCol + i] = text[i]
        fakeDisplay.displayStyle[cursorRow][cursorCol + i] = color
      self.cursorRow = cursorRow + len(text)
      self.cursorCol = cursorCol + len(text[-1])
      if len(text) > 1:
        self.cursorCol = len(text[-1])
      return (1, 1)
    except:
      sys.exit(1)

  def getch(self):
    testLog()
    if 1:
      global getchCallback
      if getchCallback:
        val = getchCallback()
        return val
    val = fakeInput.next()
    if 0 and val != ERR:
      print 'val', val
    return val

  def getyx(self):
    testLog()
    return (self.cursorRow, self.cursorCol)

  def getmaxyx(self):
    testLog()
    return (fakeDisplay.rows, fakeDisplay.cols)

  def keypad(self, *args):
    testLog(*args)

  def leaveok(self, *args):
    testLog(*args)

  def move(self, a, b):
    testLog(a, b)
    self.cursorRow = a
    self.cursorCol = b

  def noutrefresh(self):
    pass

  def refresh(self):
    testLog()

  def resize(self, a, b):
    testLog(a, b)

  def scrollok(self, *args):
    testLog(*args)

  def timeout(self, *args):
    testLog(*args)


class StandardScreen(FakeCursesWindow):
  def __init__(self):
    global fakeDisplay, fakeInput
    testLog()
    FakeCursesWindow.__init__(self, 0, 0)
    fakeDisplay = FakeDisplay()
    self.fakeDisplay = fakeDisplay
    fakeInput = FakeInput(fakeDisplay)
    self.fakeInput = fakeInput
    self.movie = False

  def setFakeInputs(self, cmdList):
    self.fakeInput.setInputs(cmdList)

  def getmaxyx(self):
    testLog()
    return (self.fakeDisplay.rows, self.fakeDisplay.cols)

  def refresh(self):
    if self.movie:
      fakeDisplay.show()
    fakeInput.waitingForRefresh = False
    testLog()


def can_change_color():
  testLog()

def color_content():
  testLog()

def color_pair(*args):
  testLog(*args)
  return fakeDisplay.getColorPair(*args)

def curs_set(*args):
  testLog(*args)

def error():
  testLog()

def errorpass():
  testLog()

def getch():
  testLog()
  return ERR

def addMouseEvent(mouseEvent):
  testLog()
  return mouseEvents.append(mouseEvent)

def getmouse():
  testLog()
  return mouseEvents.pop()

def has_colors():
  testLog()

def init_color():
  testLog()

def init_pair(*args):
  testLog(*args)

def keyname():
  testLog()

def meta(*args):
  testLog(*args)

def mouseinterval(*args):
  testLog(*args)

def mousemask(*args):
  testLog(*args)

def newwin(*args):
  testLog(*args)
  return FakeCursesWindow(args[0], args[1])

def raw(*args):
  testLog(*args)

def resizeterm(*args):
  testLog(*args)

def start_color(*args):
  testLog(*args)

def ungetch(*args):
  testLog(*args)

def use_default_colors(*args):
  testLog(*args)

def get_pair(*args):
  fakeDisplay.getColorPair(*args)
  testLog(*args)

def wrapper(fun, *args, **kw):
  standardScreen = StandardScreen()
  fun(standardScreen, *args, **kw)

