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


"""A fake curses api intended for making tests."""

COLORS = 256

KEY_BACKSPACE = 4
KEY_DC = 5
KEY_HOME = 6
KEY_END = 7


class FakeCursesWindow:
  def __init__(self):
    pass


class StandardScreen:
  def __init__(self):
    pass

  def getmaxyx(self):
    return (11, 19)


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

