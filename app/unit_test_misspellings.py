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

from app.curses_util import *
import app.fake_curses_testing


class MisspellingsTestCases(app.fake_curses_testing.FakeCursesTestCase):

    def setUp(self):
        self.longMessage = True
        app.fake_curses_testing.FakeCursesTestCase.setUp(self)

    def test_highlight_misspellings(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.displayCheck(0, 0, [u" ci  "]),
            self.cursorCheck(2, 7),
            self.writeText(u'test asdf orange'),
            self.selectionCheck(0, 16, 0, 0, 0),
            self.displayCheckStyle(2, 7, 1, len(u"test "),
                                   self.prg.color.get(u'text', 0)),
            self.displayCheckStyle(2, 12, 1, len(u"asdf"),
                                   self.prg.color.get(u'misspelling', 0)),
            self.displayCheckStyle(2, 16, 1, len(u" orange"),
                                   self.prg.color.get(u'text', 0)),
            CTRL_Q,
            u'n',
        ])
