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

import unittest

from app.curses_util import *
import app.fake_curses_testing


class DrawTestCases(app.fake_curses_testing.FakeCursesTestCase):

    def setUp(self):
        app.fake_curses_testing.FakeCursesTestCase.setUp(self)

    def test_draw_nothing(self):
        self.runWithFakeInputs([
            self.displayCheck(2, 7, [u"      "]),
            self.writeText(u"tex"),
            self.displayCheck(2, 7, [u"tex "]), KEY_BACKSPACE1, u"t",
            self.displayCheck(2, 7, [u"tet "]), CTRL_Q, u"n"
        ])

    def test_draw_tabs(self):
        test = u"""\t<tab
\t <tab+space
 \t<space+tab
\ta<
a\t<
some text.>\t<
\t\t<2tabs
line\twith\ttabs
ends with tab>\t
\t
"""
        self.runWithFakeInputs([
            self.displayCheck(2, 7, [u"                           "]),
            self.writeText(test),
            self.displayCheck(2, 7, [u"        <tab               "]),
            self.displayCheck(3, 7, [u"         <tab+space        "]),
            self.displayCheck(4, 7, [u"        <space+tab         "]),
            self.displayCheck(5, 7, [u"        a<                 "]),
            self.displayCheck(6, 7, [u"a       <                  "]),
            self.displayCheck(7, 7, [u"some text.>     <          "]),
            self.displayCheck(8, 7, [u"                <2tabs     "]),
            self.displayCheck(9, 7, [u"line    with    tabs       "]),
            self.displayCheck(10, 7, [u"ends with tab>             "]),
            self.displayCheck(11, 7, [u"                           "]),
            CTRL_Q, u"n"
        ])

    def test_draw_text(self):
        self.runWithFakeInputs([
            self.displayCheck(2, 7, [u"      "]),
            self.writeText(u"text"),
            self.displayCheck(2, 7, [u"text "]), CTRL_Q, u"n"
        ])

    def test_draw_long_line(self):
        #self.setMovieMode(True)
        lineLimitIndicator = self.prg.prefs.editor['lineLimitIndicator']
        self.prg.prefs.editor['lineLimitIndicator'] = 10
        self.runWithFakeInputs([
            self.displayCheck(2, 7, [u"      "]),
            self.writeText(u"A line with numbers 1234567890"),
            self.displayCheck(2, 7, [u"A line with numbers 1234567890"]),
            self.writeText(u". Writing"),
            self.displayCheck(2, 7, [u"ith numbers 1234567890. Writing"]),
            self.writeText(u" some more."),
            self.displayCheck(2, 7, [u" 1234567890. Writing some more."]),
            self.writeText(u"\n"),
            self.displayCheck(2, 7, [u"A line with numbers 1234567890."]),
            CTRL_Q, u"n"
        ])
        self.prg.prefs.editor['lineLimitIndicator'] = lineLimitIndicator
