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

import curses
import fcntl
import os
import signal
import struct
import sys
import termios
import curses.ascii


# Strings are found using the cursesKeyName() function.
# Constants are found using the curses.getch() function.

# Tuple events are preceded by an escape (27).
BRACKETED_PASTE_BEGIN = (91, 50, 48, 48, 126)
BRACKETED_PASTE_END = (91, 50, 48, 49, 126)
BRACKETED_PASTE = ('terminal_paste',)  # Pseudo event type.

UNICODE_INPUT = ('unicode_input',)  # Pseudo event type.

CTRL_AT = '^@'  # 0x00
CTRL_SPACE = '^@'  # 0x00
CTRL_A = '^A'  # 0x01
CTRL_B = '^B'  # 0x02
CTRL_C = '^C'  # 0x03
CTRL_D = '^D'  # 0x04
CTRL_E = '^E'  # 0x05
CTRL_F = '^F'  # 0x06
CTRL_G = '^G'  # 0x07
CTRL_H = '^H'  # 0x08
CTRL_I = '^I'  # 0x09
CTRL_J = '^J'  # 0x0a
CTRL_K = '^K'  # 0x0b
CTRL_L = '^L'  # 0x0c
CTRL_M = '^M'  # 0x0d
CTRL_N = '^N'  # 0x0e
CTRL_O = '^O'  # 0x0f
CTRL_P = '^P'  # 0x10
CTRL_Q = '^Q'  # 0x11
CTRL_R = '^R'  # 0x12
CTRL_S = '^S'  # 0x13
CTRL_T = '^T'  # 0x14
CTRL_U = '^U'  # 0x15
CTRL_V = '^V'  # 0x16
CTRL_W = '^W'  # 0x17
CTRL_X = '^X'  # 0x18
CTRL_Y = '^Y'  # 0x19
CTRL_Z = '^Z'  # 0x1a
CTRL_OPEN_BRACKET = '^['  # 0x1b
CTRL_BACKSLASH = '^\\'  # 0x1c
CTRL_CLOSE_BRACKET = '^]'  # 0x1d
CTRL_CARROT = '^^'  # 0x1e
CTRL_UNDERBAR = '^_'  # 0x1f

KEY_ESCAPE = curses.ascii.ESC

KEY_BACKSPACE1 = curses.ascii.BS  # 8
KEY_BACKSPACE2 = curses.ascii.DEL  # 127
KEY_BACKSPACE3 = curses.KEY_BACKSPACE  # 263
KEY_DELETE = curses.KEY_DC
KEY_HOME = curses.KEY_HOME
KEY_END = curses.KEY_END
KEY_PAGE_DOWN = curses.KEY_NPAGE
KEY_SHIFT_PAGE_DOWN = curses.KEY_SNEXT
KEY_ALT_SHIFT_PAGE_DOWN = 'kNXT4'
KEY_PAGE_UP = curses.KEY_PPAGE
KEY_SHIFT_PAGE_UP = curses.KEY_SPREVIOUS
KEY_ALT_SHIFT_PAGE_UP = 'kPRV4'
KEY_BTAB = curses.KEY_BTAB

KEY_ALT_A = 165
KEY_ALT_B = 171
KEY_ALT_C = 167
KEY_ALT_S = 159


if sys.platform == 'darwin':
  KEY_ALT_LEFT = (91, 49, 59, 57, 68)
  KEY_ALT_RIGHT = (91, 49, 59, 57, 67)
  KEY_ALT_SHIFT_LEFT = (91, 49, 59, 49, 48, 68,)
  KEY_ALT_SHIFT_RIGHT = (91, 49, 59, 49, 48, 67,)
else:
  KEY_ALT_LEFT = 'kLFT3'
  KEY_ALT_RIGHT = 'kRIT3'
  KEY_ALT_SHIFT_LEFT = 'kLFT4'
  KEY_ALT_SHIFT_RIGHT = 'kRIT4'

if 'SSH_CLIENT' in os.environ:
  KEY_ALT_LEFT = (98,)  # Need a better way to sort this out.
  KEY_ALT_RIGHT = (102,)  # ditto


KEY_CTRL_DOWN = 'kDN5'
KEY_CTRL_SHIFT_DOWN = 'kDN6'
KEY_CTRL_LEFT = 'kLFT5'
KEY_CTRL_SHIFT_LEFT = 'kLFT6'
KEY_CTRL_RIGHT = 'kRIT5'
KEY_CTRL_SHIFT_RIGHT = 'kRIT6'
KEY_CTRL_UP = 'kUP5'
KEY_CTRL_SHIFT_UP = 'kUP6'

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
  result = ''
  if buttonState & curses.BUTTON1_RELEASED:
    result += 'BUTTON1_RELEASED'
  if buttonState & curses.BUTTON1_PRESSED:
    result += 'BUTTON1_PRESSED'
  if buttonState & curses.BUTTON1_CLICKED:
    result += 'BUTTON1_CLICKED'
  if buttonState & curses.BUTTON1_DOUBLE_CLICKED:
    result += 'BUTTON1_DOUBLE_CLICKED'

  if buttonState & curses.BUTTON2_RELEASED:
    result += 'BUTTON2_RELEASED'
  if buttonState & curses.BUTTON2_PRESSED:
    result += 'BUTTON2_PRESSED'
  if buttonState & curses.BUTTON2_CLICKED:
    result += 'BUTTON2_CLICKED'
  if buttonState & curses.BUTTON2_DOUBLE_CLICKED:
    result += 'BUTTON2_DOUBLE_CLICKED'

  if buttonState & curses.BUTTON3_RELEASED:
    result += 'BUTTON3_RELEASED'
  if buttonState & curses.BUTTON3_PRESSED:
    result += 'BUTTON3_PRESSED'
  if buttonState & curses.BUTTON3_CLICKED:
    result += 'BUTTON3_CLICKED'
  if buttonState & curses.BUTTON3_DOUBLE_CLICKED:
    result += 'BUTTON3_DOUBLE_CLICKED'

  if buttonState & curses.BUTTON4_RELEASED:
    result += 'BUTTON4_RELEASED'
  if buttonState & curses.BUTTON4_PRESSED:
    result += 'BUTTON4_PRESSED'
  if buttonState & curses.BUTTON4_CLICKED:
    result += 'BUTTON4_CLICKED'
  if buttonState & curses.BUTTON4_DOUBLE_CLICKED:
    result += 'BUTTON4_DOUBLE_CLICKED'

  if buttonState & curses.REPORT_MOUSE_POSITION:
    result += 'REPORT_MOUSE_POSITION'

  if buttonState & curses.BUTTON_SHIFT:
    result += ' SHIFT'
  if buttonState & curses.BUTTON_CTRL:
    result += ' CTRL'
  if buttonState & curses.BUTTON_ALT:
    result += ' ALT'
  return result

def cursesKeyName(keyCode):
  try:
    return curses.keyname(keyCode)
  except:
    pass
  return None

# This should be provide by something built in and apparently it is in Python 3.
# In Python 2 it's done by hand.
def terminalSize():
  h, w = struct.unpack(
      'HHHH',
      fcntl.ioctl(0, termios.TIOCGWINSZ,
      struct.pack('HHHH', 0, 0, 0, 0)))[:2]
  return h, w

def hackCursesFixes():
  if sys.platform == 'darwin':
    def windowChangedHandler(signum, frame):
      curses.ungetch(curses.KEY_RESIZE)
    signal.signal(signal.SIGWINCH, windowChangedHandler)
  def wakeGetch(signum, frame):
    curses.ungetch(0)
  signal.signal(signal.SIGUSR1, wakeGetch)
