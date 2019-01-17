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


class ExecutePromptTestCases(app.fake_curses_testing.FakeCursesTestCase):

    def setUp(self):
        self.longMessage = True
        app.fake_curses_testing.FakeCursesTestCase.setUp(self)

    def test_execute(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.displayCheck(-1, 0, [u"      "]), CTRL_E,
            self.displayCheck(-1, 0, [u"e: "]), CTRL_J,
            self.displayCheck(-1, 0, [u"      "]), CTRL_E,
            self.displayCheck(-1, 0, [u"e: "]), CTRL_J, CTRL_Q
        ])

    def test_pipe_sort(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.writeText(u"carrot\nbanana\nbanana\napple\n"),
            self.displayCheck(2, 7, [
                u"carrot  ", u"banana  ", u"banana  ", u"apple  ",
                u"           "
            ]), CTRL_A, CTRL_E,
            self.writeText(u'|sort'),
            self.displayCheck(-1, 0, [u"e: |sort  "]), CTRL_J,
            self.displayCheck(2, 7, [
                u"apple  ", u"banana  ", u"banana  ", u"carrot  ",
                u"           "
            ]), CTRL_Q, u"n"
        ])
