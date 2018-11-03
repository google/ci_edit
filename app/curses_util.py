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

import curses
import curses.ascii
import fcntl
import os
import signal
import struct
import sys
import termios


# Strings are found using the cursesKeyName() function.
# Constants are found using the curses.getch() function.

# Tuple events are preceded by an escape (27).
BRACKETED_PASTE_BEGIN = (91, 50, 48, 48, 126)  # i.e. "[200~"
BRACKETED_PASTE_END = (91, 50, 48, 49, 126)  # i.e. "[201~"
BRACKETED_PASTE = (b'terminal_paste',)  # Pseudo event type.

UNICODE_INPUT = (b'unicode_input',)  # Pseudo event type.

CTRL_AT = b'^@'  # 0x00
CTRL_SPACE = b'^@'  # 0x00
CTRL_A = b'^A'  # 0x01
CTRL_B = b'^B'  # 0x02
CTRL_C = b'^C'  # 0x03
CTRL_D = b'^D'  # 0x04
CTRL_E = b'^E'  # 0x05
CTRL_F = b'^F'  # 0x06
CTRL_G = b'^G'  # 0x07
CTRL_H = b'^H'  # 0x08
CTRL_I = b'^I'  # 0x09
CTRL_J = b'^J'  # 0x0a
CTRL_K = b'^K'  # 0x0b
CTRL_L = b'^L'  # 0x0c
CTRL_M = b'^M'  # 0x0d
CTRL_N = b'^N'  # 0x0e
CTRL_O = b'^O'  # 0x0f
CTRL_P = b'^P'  # 0x10
CTRL_Q = b'^Q'  # 0x11
CTRL_R = b'^R'  # 0x12
CTRL_S = b'^S'  # 0x13
CTRL_T = b'^T'  # 0x14
CTRL_U = b'^U'  # 0x15
CTRL_V = b'^V'  # 0x16
CTRL_W = b'^W'  # 0x17
CTRL_X = b'^X'  # 0x18
CTRL_Y = b'^Y'  # 0x19
CTRL_Z = b'^Z'  # 0x1a
CTRL_OPEN_BRACKET = b'^['  # 0x1b
CTRL_BACKSLASH = b'^\\'  # 0x1c
CTRL_CLOSE_BRACKET = b'^]'  # 0x1d
CTRL_CARROT = b'^^'  # 0x1e
CTRL_UNDERBAR = b'^_'  # 0x1f

KEY_ALT_A = 165
KEY_ALT_B = 171
KEY_ALT_C = 167
KEY_ALT_S = 159
KEY_ALT_SHIFT_PAGE_DOWN = b'kNXT4'
KEY_ALT_SHIFT_PAGE_UP = b'kPRV4'
KEY_BACKSPACE1 = curses.ascii.BS  # 8
KEY_BACKSPACE2 = curses.ascii.DEL  # 127
KEY_BACKSPACE3 = curses.KEY_BACKSPACE  # 263
KEY_BTAB = curses.KEY_BTAB
KEY_DELETE = curses.KEY_DC
KEY_END = curses.KEY_END
KEY_ESCAPE = curses.ascii.ESC
KEY_HOME = curses.KEY_HOME
KEY_PAGE_DOWN = curses.KEY_NPAGE
KEY_PAGE_UP = curses.KEY_PPAGE
KEY_SEND = curses.KEY_SEND
KEY_SHIFT_PAGE_DOWN = curses.KEY_SNEXT
KEY_SHIFT_PAGE_UP = curses.KEY_SPREVIOUS
KEY_SHOME = curses.KEY_SHOME


if sys.platform == u"darwin":
  KEY_ALT_LEFT = (91, 49, 59, 57, 68)
  KEY_ALT_RIGHT = (91, 49, 59, 57, 67)
  KEY_ALT_SHIFT_LEFT = (91, 49, 59, 49, 48, 68,)
  KEY_ALT_SHIFT_RIGHT = (91, 49, 59, 49, 48, 67,)
else:
  KEY_ALT_LEFT = b'kLFT3'
  KEY_ALT_RIGHT = b'kRIT3'
  KEY_ALT_SHIFT_LEFT = b'kLFT4'
  KEY_ALT_SHIFT_RIGHT = b'kRIT4'

if u"SSH_CLIENT" in os.environ:
  KEY_ALT_LEFT = (98,)  # Need a better way to sort this out.
  KEY_ALT_RIGHT = (102,)  # ditto


KEY_CTRL_DOWN = b'kDN5'
KEY_CTRL_SHIFT_DOWN = b'kDN6'
KEY_CTRL_LEFT = b'kLFT5'
KEY_CTRL_SHIFT_LEFT = b'kLFT6'
KEY_CTRL_RIGHT = b'kRIT5'
KEY_CTRL_SHIFT_RIGHT = b'kRIT6'
KEY_CTRL_UP = b'kUP5'
KEY_CTRL_SHIFT_UP = b'kUP6'

KEY_F1 = curses.KEY_F1
KEY_F2 = curses.KEY_F2
KEY_F3 = curses.KEY_F3
KEY_F4 = curses.KEY_F4
KEY_F5 = curses.KEY_F5
KEY_F6 = curses.KEY_F6
KEY_F7 = curses.KEY_F7
KEY_F8 = curses.KEY_F8
KEY_F9 = curses.KEY_F9
KEY_F10 = curses.KEY_F10
KEY_SHIFT_F1 = curses.KEY_F13
KEY_SHIFT_F2 = curses.KEY_F14
KEY_SHIFT_F3 = curses.KEY_F15
KEY_SHIFT_F4 = curses.KEY_F16
KEY_SHIFT_F5 = curses.KEY_F17
KEY_SHIFT_F6 = curses.KEY_F18
KEY_SHIFT_F7 = curses.KEY_F19
KEY_SHIFT_F8 = curses.KEY_F20
KEY_SHIFT_F9 = curses.KEY_F21
KEY_SHIFT_F10 = curses.KEY_F22

KEY_SHIFT_DOWN = curses.KEY_SF
KEY_DOWN = curses.KEY_DOWN
KEY_SHIFT_UP = curses.KEY_SR
KEY_UP = curses.KEY_UP
KEY_LEFT = curses.KEY_LEFT
KEY_SHIFT_LEFT = curses.KEY_SLEFT
KEY_RIGHT = curses.KEY_RIGHT
KEY_SHIFT_RIGHT = curses.KEY_SRIGHT

KEY_MOUSE = curses.KEY_MOUSE
KEY_RESIZE = curses.KEY_RESIZE

def mouseButtonName(buttonState):
  """Curses debugging. Prints readable name for state of mouse buttons."""
  result = u""
  if buttonState & curses.BUTTON1_RELEASED:
    result += u'BUTTON1_RELEASED'
  if buttonState & curses.BUTTON1_PRESSED:
    result += u'BUTTON1_PRESSED'
  if buttonState & curses.BUTTON1_CLICKED:
    result += u'BUTTON1_CLICKED'
  if buttonState & curses.BUTTON1_DOUBLE_CLICKED:
    result += u'BUTTON1_DOUBLE_CLICKED'

  if buttonState & curses.BUTTON2_RELEASED:
    result += u'BUTTON2_RELEASED'
  if buttonState & curses.BUTTON2_PRESSED:
    result += u'BUTTON2_PRESSED'
  if buttonState & curses.BUTTON2_CLICKED:
    result += u'BUTTON2_CLICKED'
  if buttonState & curses.BUTTON2_DOUBLE_CLICKED:
    result += u'BUTTON2_DOUBLE_CLICKED'

  if buttonState & curses.BUTTON3_RELEASED:
    result += u'BUTTON3_RELEASED'
  if buttonState & curses.BUTTON3_PRESSED:
    result += u'BUTTON3_PRESSED'
  if buttonState & curses.BUTTON3_CLICKED:
    result += u'BUTTON3_CLICKED'
  if buttonState & curses.BUTTON3_DOUBLE_CLICKED:
    result += u'BUTTON3_DOUBLE_CLICKED'

  if buttonState & curses.BUTTON4_RELEASED:
    result += u'BUTTON4_RELEASED'
  if buttonState & curses.BUTTON4_PRESSED:
    result += u'BUTTON4_PRESSED'
  if buttonState & curses.BUTTON4_CLICKED:
    result += u'BUTTON4_CLICKED'
  if buttonState & curses.BUTTON4_DOUBLE_CLICKED:
    result += u'BUTTON4_DOUBLE_CLICKED'

  if buttonState & curses.REPORT_MOUSE_POSITION:
    result += u'REPORT_MOUSE_POSITION'

  if buttonState & curses.BUTTON_SHIFT:
    result += u' SHIFT'
  if buttonState & curses.BUTTON_CTRL:
    result += u' CTRL'
  if buttonState & curses.BUTTON_ALT:
    result += u' ALT'
  return result

def cursesKeyName(keyCode):
  try:
    return curses.keyname(keyCode)
  except:
    pass
  return None

# This is built-in in Python 3.
# In Python 2 it's done by hand.
def terminalSize():
  h, w = struct.unpack(
      b'HHHH',
      fcntl.ioctl(0, termios.TIOCGWINSZ,
      struct.pack(b'HHHH', 0, 0, 0, 0)))[:2]
  return h, w

def hackCursesFixes():
  if sys.platform == u'darwin':
    def windowChangedHandler(signum, frame):
      curses.ungetch(curses.KEY_RESIZE)
    signal.signal(signal.SIGWINCH, windowChangedHandler)
  def wakeGetch(signum, frame):
    curses.ungetch(0)
  signal.signal(signal.SIGUSR1, wakeGetch)
