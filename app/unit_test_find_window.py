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


class FindWindowTestCases(app.fake_curses_testing.FakeCursesTestCase):

    def setUp(self):
        self.longMessage = True
        app.fake_curses_testing.FakeCursesTestCase.setUp(self)

    def test_find(self):
        self.runWithFakeInputs([
            self.displayCheck(-1, 0, [u"      "]),
            CTRL_F,
            self.displayCheck(-3, 0, [u"Find: "]),
            CTRL_J,
            self.displayCheck(-1, 0, [u"      "]),
            CTRL_F,
            self.displayCheck(-3, 0, [u"Find: "]),
            CTRL_I,
            self.displayCheck(-3, 0, [u"Find: ", u"Replace: ", u"["]),
            #KEY_BTAB, KEY_BTAB, self.displayCheck(-1, 0, [u"Find: "]),
            CTRL_Q
        ])

    def test_find_forward_and_reverse(self):
        self.runWithFakeInputs([
            self.writeText(u"ten one two three\nfour one one five\n"
                           u" six seven one\none\n"),
            self.displayCheck(2, 7, [u"ten one two three  "]),
            self.displayCheck(-1, 0, [u"      "]), CTRL_F,
            self.displayCheck(-3, 0, [u"Find: "]),
            self.writeText(u'one'),
            self.selectionDocumentCheck(0, 4, 0, 7, 3), CTRL_F,
            self.selectionDocumentCheck(1, 5, 1, 8, 3), CTRL_F,
            self.selectionDocumentCheck(1, 9, 1, 12, 3), CTRL_R,
            self.selectionDocumentCheck(1, 5, 1, 8, 3), CTRL_R,
            self.selectionDocumentCheck(0, 4, 0, 7, 3), CTRL_R,
            self.selectionDocumentCheck(3, 0, 3, 3, 3), CTRL_R,
            self.selectionDocumentCheck(2, 11, 2, 14, 3), CTRL_R,
            self.selectionDocumentCheck(1, 9, 1, 12, 3), CTRL_R,
            self.selectionDocumentCheck(1, 5, 1, 8, 3), CTRL_F,
            self.selectionDocumentCheck(1, 9, 1, 12, 3), CTRL_F,
            self.selectionDocumentCheck(2, 11, 2, 14, 3), CTRL_F,
            self.selectionDocumentCheck(3, 0, 3, 3, 3), CTRL_F,
            self.selectionDocumentCheck(0, 4, 0, 7, 3), CTRL_F,
            self.selectionDocumentCheck(1, 5, 1, 8, 3), CTRL_Q, u"n"
        ])

    def test_replace(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.writeText(u"aDog\n"),
            self.displayCheck(2, 7, [u"aDog  "]), CTRL_F,
            self.writeText(u'a(.*)'),
            self.displayCheck(-3, 0, [u"Find: a(.*)  "]), CTRL_I,
            self.writeText(u'x\\1\\1'),
            self.displayCheck(-2, 0, [u"Replace: x\\1\\1  "]), CTRL_G,
            self.displayCheck(2, 7, [u"xDogDog  "]), CTRL_Q, u"n"
        ])

    def test_invalid_replace(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.writeText(u"aDog aDog\n"),
            self.displayCheck(2, 7, [u"aDog aDog  "]),
            CTRL_F,
            self.writeText(u"a"),
            self.displayCheck(-3, 0, [u"Find: a  "]),
            self.selectionDocumentCheck(0, 0, 0, 1, 3),
            CTRL_I,
            self.writeText(u'x\\1\\1'),
            self.displayCheck(-2, 0, [u"Replace: x\\1\\1  "]),
            CTRL_G,
            # The replacement will have failed (there is no \1 group). The
            # display should not have changed.
            self.displayCheck(2, 7, [u"aDog aDog  "]),
            # Since the replacement has an error, the selection should not move.
            #self.selectionDocumentCheck(0, 0, 0, 1, 3),
            # Doing a find doesn't involve the error in the replacement string,
            # so the selection should move.
            #CTRL_F, self.selectionDocumentCheck(0, 5, 0, 6, 3),
            CTRL_Q,
            u"n"
        ])

    def test_find_replace_groups(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.writeText(u'a\nb\na\nb\na\nb\n'),
            self.displayCheck(2, 7, [u"a ", u"b ", u"a ", u"b ", u"a ", u"b "]),

            # Enter Find and make two document replacements.
            CTRL_F,
            self.writeText(u'(a)'),
            self.displayCheck(-3, 0, [u"Find: (a)  "]),
            CTRL_I,
            self.writeText(u'\\1!\\1'),
            self.displayCheck(-2, 0, [u"Replace: \\1!\\1  "]),
            CTRL_G,
            self.displayCheck(2, 7,
                              [u"a!a ", u"b ", u"a ", u"b ", u"a ", u"b "]),
            CTRL_G,
            self.displayCheck(2, 7,
                              [u"a!a ", u"b ", u"a!a ", u"b ", u"a ", u"b "]),

            # Leave Find and Undo the document changes.
            KEY_ESCAPE,
            curses.ERR,
            CTRL_Z,
            self.displayCheck(2, 7, [u"a ", u"b ", u"a ", u"b ", u"a ", u"b "]),

            # Go to bottom of document.
            CTRL_G,
            u"b",
            KEY_ESCAPE,
            curses.ERR,

            # Enter Find and make a reverse search replacement.
            CTRL_F,
            CTRL_R,
            CTRL_I,
            CTRL_R,
            self.displayCheck(2, 7,
                              [u"a ", u"b ", u"a ", u"b ", u"a!a ", u"b "]),
            # TODO(dschuyler): CTRL_R,
            # TODO(dschuyler): self.displayCheck(2, 7, [u"a ", u"b ", u"a!a ",
            # u"b ", u"a!a ", u"b "]),

            # Quit without saving.
            CTRL_Q,
            u"n"
        ])

    def test_find_esc_from_find(self):
        self.runWithFakeInputs([
            # Check initial state.
            self.displayCheck(-1, 0, [u"      "]),
            self.displayCheckStyle(-2, 0, 1, 10,
                                   self.prg.color.get(u'status_line', 0)),

            # Basic open and close.
            CTRL_F,
            self.displayCheck(-3, 0, [u"Find: "]),
            KEY_ESCAPE,
            curses.ERR,
            self.displayCheck(-3, 0, [u"   ", u"   ", u"   "]),
            self.displayCheckStyle(-2, 0, 1, 10,
                                   self.prg.color.get(u'status_line', 0)),

            # Open, expand, and close.
            CTRL_F,
            self.displayCheck(-3, 0, [u"Find: "]),
            CTRL_I,
            self.displayCheck(-3, 0, [u"Find: ", u"Replace: ", u"["]),
            KEY_ESCAPE,
            curses.ERR,
            self.displayCheck(-3, 0, [u"   ", u"   ", u"   "]),
            self.displayCheckStyle(-2, 0, 1, 10,
                                   self.prg.color.get(u'status_line', 0)),

            # Regression test one for
            # https://github.com/google/ci_edit/issues/170.
            CTRL_F,
            self.displayCheck(-3, 0, [u"Find: ", u"Replace: ", u"["]),
            CTRL_I,
            CTRL_I,
            self.displayCheck(-3, 0, [u"Find: ", u"Replace: ", u"["]),
            KEY_ESCAPE,
            curses.ERR,
            self.displayCheck(-3, 0, [u"   ", u"   ", u"   "]),
            self.displayCheckStyle(-2, 0, 1, 10,
                                   self.prg.color.get(u'status_line', 0)),

            # Regression test two for
            # https://github.com/google/ci_edit/issues/170.
            CTRL_F,
            self.displayCheck(-3, 0, [u"Find: ", u"Replace: ", u"["]),
            self.addMouseInfo(0, 2, 10, curses.BUTTON1_PRESSED),
            curses.KEY_MOUSE,
            #self.displayCheck(-3, 0, ["   ", "   ", "   "]),
            self.displayCheckStyle(-2, 0, 1, 10,
                                   self.prg.color.get(u'status_line', 0)),
            CTRL_Q
        ])

    def test_replace_style_parse(self):
        self.runWithFakeInputs([
            #self.displayCheck(2, 7, [u"      "]),
            #self.displayCheckStyle(2, 7, 1, 10,
            #    self.prg.color.get(u'text', 0)),
            self.writeText(u'focusedWindow\n'),
            CTRL_F,
            #self.displayCheck(-1, 0, [u"Find:         "]),
            self.writeText(u'focused'),
            CTRL_I,
            #self.displayCheck(
            #    -3, 0, [u"Find: focused", "Replace:          ", u"["]),
            self.writeText(u'  focused'),
            #self.displayCheck(
            #    -3, 0, [u"Find: focused", "Replace:   focused", u"["]),
            CTRL_G,
            # Regression, replace causes 'Windo' to show as a misspelling.
            self.displayCheckStyle(2, 17, 1, 10, self.prg.color.get(u'text',
                                                                    0)),
            CTRL_Q,
            ord('n')
        ])
