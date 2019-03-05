# Copyright 2019 Google Inc.
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
import os
import sys

from app.curses_util import *
import app.ci_program
import app.fake_curses_testing

kTestFile = u'#application_test_file_with_unlikely_file_name~'


class CopyPasteTestCases(app.fake_curses_testing.FakeCursesTestCase):

    def setUp(self):
        self.longMessage = True
        app.fake_curses_testing.FakeCursesTestCase.setUp(self)

    def test_bracketed_paste(self):
        self.runWithFakeInputs([
                self.displayCheck(2, 7, [u"      "]),
                curses.ascii.ESC,
                app.curses_util.BRACKETED_PASTE_BEGIN,
                u't',
                u'e',
                225,
                186,
                191,  # Send an "" in utf-8.
                u't',
                curses.ascii.ESC,
                app.curses_util.BRACKETED_PASTE_END,
                self.displayCheck(2, 7, [u'te\u1ebft ']),
                CTRL_Q,
                u'n'
            ])

    def test_write_text(self):
        self.runWithFakeInputs([
            self.writeText(u'test\n'),
            CTRL_Q, u'n'
        ])
