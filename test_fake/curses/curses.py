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


import app.curses_util
import inspect
import os
import sys
import traceback


fakeInputs = []
def setFakeInputs(cmdList):
  global fakeInputs
  fakeInputs = cmdList[:]
  fakeInputs.reverse()


def testLog(*msg):
  function = inspect.stack()[1][3]
  frame = inspect.stack()[2]
  caller = "%20s %5s %20s %s " % (os.path.split(frame[1])[1],
        frame[2], frame[3], function)
  #print dir(inspect.stack()[1][0])
  #print inspect.stack()[1][0].__class__
  print caller + " ".join([str(i) for i in msg])

COLORS = 256

KEY_ALT_A = 0
KEY_ALT_B = 1
KEY_ALT_C = 2
KEY_ALT_LEFT = 3
KEY_ALT_RIGHT = 4
KEY_ALT_S = 5
KEY_ALT_SHIFT_LEFT = 6
KEY_ALT_SHIFT_RIGHT = 7
KEY_BACKSPACE = 8
KEY_BACKSPACE1 = 9
KEY_BACKSPACE2 = 10
KEY_BACKSPACE3 = 11
KEY_BTAB = 12
KEY_CTRL_DOWN = 13
KEY_CTRL_LEFT = 14
KEY_CTRL_RIGHT = 15
KEY_CTRL_SHIFT_DOWN = 16
KEY_CTRL_SHIFT_LEFT = 17
KEY_CTRL_SHIFT_RIGHT = 18
KEY_CTRL_SHIFT_UP = 19
KEY_CTRL_UP = 20
KEY_DC = 21
KEY_DELETE = 22
KEY_DOWN = 23
KEY_END = 24
KEY_ESCAPE = 25
KEY_F1 = 26
KEY_F10 = 27
KEY_F13 = 28
KEY_F14 = 29
KEY_F15 = 30
KEY_F16 = 31
KEY_F17 = 32
KEY_F18 = 33
KEY_F19 = 34
KEY_F2 = 35
KEY_F20 = 36
KEY_F21 = 37
KEY_F22 = 38
KEY_F3 = 39
KEY_F4 = 40
KEY_F5 = 41
KEY_F6 = 42
KEY_F7 = 43
KEY_F8 = 44
KEY_F9 = 45
KEY_HOME = 46
KEY_LEFT = 47
KEY_MOUSE = 48
KEY_NPAGE = 49
KEY_PAGE_DOWN = 50
KEY_PAGE_UP = 51
KEY_PPAGE = 52
KEY_RESIZE = 53
KEY_RESIZE = 54
KEY_RIGHT = 55
KEY_SF = 56
KEY_SHIFT_DOWN = 57
KEY_SHIFT_F2 = 58
KEY_SHIFT_F3 = 59
KEY_SHIFT_LEFT = 60
KEY_SHIFT_RIGHT = 61
KEY_SHIFT_UP = 62
KEY_SLEFT = 63
KEY_SR = 64
KEY_SRIGHT = 65
KEY_UP = 66


A_REVERSE = 0
BUTTON1_CLICKED = 1
BUTTON1_DOUBLE_CLICKED = 2
BUTTON1_PRESSED = 3
BUTTON1_RELEASED = 4
BUTTON2_CLICKED = 5
BUTTON2_DOUBLE_CLICKED = 6
BUTTON2_PRESSED = 7
BUTTON2_RELEASED = 8
BUTTON3_CLICKED = 9
BUTTON3_DOUBLE_CLICKED = 10
BUTTON3_PRESSED = 11
BUTTON3_RELEASED = 12
BUTTON4_CLICKED = 13
BUTTON4_DOUBLE_CLICKED = 14
BUTTON4_PRESSED = 15
BUTTON4_RELEASED = 16
BUTTON_ALT = 17
BUTTON_CTRL = 18
BUTTON_SHIFT = 19
COLORS = 20
COLORS256 = 21
ERR = 22
REPORT_MOUSE_POSITION = 23


class FakeCursesWindow:
  def __init__(self):
    testLog()

  def addstr(self, *args):
    testLog(*args)
    return (1, 1)

  def getch(self):
    testLog()
    return fakeInputs and fakeInputs.pop() or ERR

  def getmaxyx(self):
    testLog()
    return (1, 1)

  def keypad(self, a):
    testLog(a)

  def leaveok(self, a):
    testLog(a)

  def move(self, a, b):
    testLog(a, b)

  def refresh(self):
    testLog()

  def resize(self, a, b):
    testLog(a, b)

  def timeout(self, a):
    testLog(a)


class StandardScreen:
  def __init__(self):
    testLog()

  def getmaxyx(self):
    testLog()
    return (11, 19)


def can_change_color():
  testLog()

def color_content():
  testLog()

def color_pair(a):
  testLog(a)

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

def init_pair():
  testLog()

def keyname():
  testLog()

def meta():
  testLog()

def mouseinterval():
  testLog()

def mousemask():
  testLog()

def newwin():
  pass

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

def wrapper():
  pass

def getch():
  return -1

def get_pair(a):
  pass

def init_pair(a, b, c):
  pass

def meta(a):
  pass

def mouseinterval(a):
  pass

def mousemask(a):
  pass

def newwin(a, b):
  return FakeCursesWindow()

def raw():
  pass

def use_default_colors():
  pass

def wrapper(fun, *args, **kw):
  standardScreen = StandardScreen()
  fun(standardScreen, *args, **kw)

