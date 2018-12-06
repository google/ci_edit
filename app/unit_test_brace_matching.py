# -*- coding: latin-1 -*-

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
import sys

from app.curses_util import *
import app.fake_curses_testing


class BraceMatchingTestCases(app.fake_curses_testing.FakeCursesTestCase):
  def setUp(self):
    self.longMessage = True
    app.fake_curses_testing.FakeCursesTestCase.setUp(self)

  def test_parenthesis(self):
    #self.setMovieMode(True)
    sys.argv = []
    write = self.writeText
    checkStyle = self.displayCheckStyle
    bracketColor = self.prg.prefs.color['bracket']
    defaultColor = self.prg.prefs.color['default']
    matchingBracketColor = self.prg.prefs.color['matching_bracket']
    self.runWithFakeInputs([
        self.displayCheck(2, 7, [u"     "]),
        # Regression test for open ([{ without closing.
        write(u'('), self.displayCheck(2, 7, [u"(    "]), KEY_LEFT, CTRL_A,
        write(u'['), self.displayCheck(2, 7, [u"[    "]), KEY_LEFT, CTRL_A,
        write(u'{'), self.displayCheck(2, 7, [u"{    "]), KEY_LEFT, CTRL_A,
        # Test for closing )]} without opening.
        write(u')'), self.displayCheck(2, 7, [u")    "]), KEY_LEFT, CTRL_A,
        write(u']'), self.displayCheck(2, 7, [u"]    "]), KEY_LEFT, CTRL_A,
        write(u'}'), self.displayCheck(2, 7, [u"}    "]), KEY_LEFT, CTRL_A,
        # Test adjacent matching.
        write(u'()'), self.displayCheck(2, 7, [u"()    "]),
          checkStyle(2, 7, 1, 2, bracketColor), KEY_LEFT,
          checkStyle(2, 7, 1, 2, matchingBracketColor), CTRL_A,
        write(u'[]'), self.displayCheck(2, 7, [u"[]    "]),
          checkStyle(2, 7, 1, 2, bracketColor), KEY_LEFT,
          checkStyle(2, 7, 1, 2, matchingBracketColor), CTRL_A,
        write(u'{}'), self.displayCheck(2, 7, [u"{}    "]),
          checkStyle(2, 7, 1, 2, bracketColor), KEY_LEFT,
          checkStyle(2, 7, 1, 2, matchingBracketColor), CTRL_A,
        # Test same line matching.
        write(u'(test)'), self.displayCheck(2, 7, [u"(test)    "]),
          checkStyle(2, 7, 1, 1, bracketColor),
          checkStyle(2, 8, 1, 4, defaultColor),
          checkStyle(2, 12, 1, 1, bracketColor),
          KEY_LEFT,
          checkStyle(2, 7, 1, 1, matchingBracketColor),
          checkStyle(2, 8, 1, 4, defaultColor),
          checkStyle(2, 12, 1, 1, matchingBracketColor),
          CTRL_A,
        write(u'[test]'), self.displayCheck(2, 7, [u"[test]    "]),
          checkStyle(2, 7, 1, 1, bracketColor),
          checkStyle(2, 8, 1, 4, defaultColor),
          checkStyle(2, 12, 1, 1, bracketColor),
          KEY_LEFT,
          checkStyle(2, 7, 1, 1, matchingBracketColor),
          checkStyle(2, 8, 1, 4, defaultColor),
          checkStyle(2, 12, 1, 1, matchingBracketColor),
          CTRL_A,
        write(u'{test}'), self.displayCheck(2, 7, [u"{test}    "]),
          checkStyle(2, 7, 1, 1, bracketColor),
          checkStyle(2, 8, 1, 4, defaultColor),
          checkStyle(2, 12, 1, 1, bracketColor),
          KEY_LEFT,
          checkStyle(2, 7, 1, 1, matchingBracketColor),
          checkStyle(2, 8, 1, 4, defaultColor),
          checkStyle(2, 12, 1, 1, matchingBracketColor),
          CTRL_A,
        CTRL_Q, u'n'])
