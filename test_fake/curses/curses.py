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
import app.curses_util
import inspect
import os
import sys
import traceback


kNoOpsPerFlush = 5  # TODO: match to value in commandLoop().
class FakeInput:
  def __init__(self, display):
    self.fakeDisplay = display
    self.inputs = []
    self.inputsIndex = -1
    self.flushCounter = kNoOpsPerFlush

  def setInputs(self, cmdList):
    self.inputs = cmdList
    self.inputsIndex = -1
    self.flushCounter = kNoOpsPerFlush

  def next(self):
    while self.inputsIndex + 1 < len(self.inputs):
      self.inputsIndex += 1
      cmd = self.inputs[self.inputsIndex]
      if type(cmd) == type(testLog):
        if self.flushCounter:
          self.inputsIndex -= 1
          self.flushCounter -= 1
          return ERR
        cmd(self.fakeDisplay)
        self.flushCounter = kNoOpsPerFlush
      elif type(cmd) == type('a') and len(cmd) == 1:
        return ord(cmd)
      else:
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
    self.cursorRow = 0
    self.cursorCol = 0
    self.display = None
    self.reset()

  def check(self, row, col, lines):
    for i in range(len(lines)):
      line = lines[i]
      for k in range(len(line)):
        d = self.display[row + i][col + k]
        c = line[k]
        if d != c:
          self.show()
          return "row %s, col %s mismatch '%s' != '%s'" % (
              row + i, col + k, d, c)
    return None

  def get(self):
    return [''.join(self.display[i]) for i in range(self.rows)]

  def show(self):
    print '+' + '-' * self.cols + '+'
    for line in self.get():
      print '|' + line + '|'
    print '+' + '-' * self.cols + '+'

  def reset(self):
    self.display = [
        ['x' for k in range(self.cols)] for i in range(self.rows)]

fakeDisplay = None
fakeInput = None

def getFakeDisplay():
  return fakeDisplay

def printFakeDisplay():
  fakeDisplay.show()


#####################################


class FakeCursesWindow:
  def __init__(self, rows, cols):
    self.rows = rows
    self.cols = cols

  def addstr(self, *args):
    global fakeDisplay
    testLog(*args)
    cursorRow = args[0]
    cursorCol = args[1]
    text = args[2]
    color = args[3]
    for i in range(len(text)):
      fakeDisplay.display[cursorRow][cursorCol + i] = text[i]
    return (1, 1)

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
    return (0, 0)

  def getmaxyx(self):
    testLog()
    return (fakeDisplay.rows, fakeDisplay.cols)

  def keypad(self, a):
    testLog(a)

  def leaveok(self, a):
    testLog(a)

  def move(self, a, b):
    testLog(a, b)

  def noutrefresh(self):
    pass

  def refresh(self):
    testLog()

  def resize(self, a, b):
    testLog(a, b)

  def scrollok(self, a):
    testLog(a)

  def timeout(self, a):
    testLog(a)


class StandardScreen(FakeCursesWindow):
  def __init__(self):
    testLog()
    global fakeDisplay, fakeInput
    fakeDisplay = FakeDisplay()
    fakeInput = FakeInput(fakeDisplay)
    self.fakeInput = fakeInput

  def setFakeInputs(self, cmdList):
    self.fakeInput.setInputs(cmdList)

  def getyx(self):
    testLog()
    return (0, 0)

  def getmaxyx(self):
    testLog()
    global fakeDisplay
    return (fakeDisplay.rows, fakeDisplay.cols)


def can_change_color():
  testLog()

def color_content():
  testLog()

def color_pair(a):
  testLog(a)
  return 1

def curs_set(a):
  testLog(a)

def error():
  testLog()

def errorpass():
  testLog()

def getch():
  testLog()
  return ERR

def getmouse():
  testLog()

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

def raw():
  pass

def resizeterm():
  pass

def start_color():
  pass

def ungetch():
  pass

def use_default_colors():
  pass

def get_pair(a):
  pass

def wrapper(fun, *args, **kw):
  standardScreen = StandardScreen()
  fun(standardScreen, *args, **kw)

