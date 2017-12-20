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

import app.prefs
import curses


colors = 256
cache__ = {}

def reset():
  global cache__
  cache__ = {}

def get(colorType, delta=0):
  global cache__
  if type(colorType) == type(0):
    colorIndex = colorType
  else:
    colorIndex = app.prefs.color[colorType]
  colorIndex = min(colors - 1, colorIndex + delta)
  color = cache__.get(colorIndex) or curses.color_pair(colorIndex)
  cache__[colorIndex] = color
  if colorType in ('error', 'misspelling'):
    color |= curses.A_BOLD | curses.A_REVERSE
  return color
