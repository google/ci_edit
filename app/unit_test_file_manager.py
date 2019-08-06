# -*- coding: utf-8 -*-

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


class FileManagerTestCases(app.fake_curses_testing.FakeCursesTestCase):

    def setUp(self):
        self.longMessage = True
        app.fake_curses_testing.FakeCursesTestCase.setUp(self)

    def test_save_as(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.displayCheck(0, 0, [u" ci     "]),
            self.displayCheck(2, 7, [u"     "]), CTRL_S,
            self.displayCheck(0, 0, [u" ci    Save File As"]), CTRL_Q, CTRL_Q
        ])  # TODO(dschuyler): fix need for extra CTRL_Q.

    def test_save_as_to_quit(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.displayCheck(0, 0, [u" ci     "]),
            self.displayCheck(2, 7, [u"     "]),
            ord('a'),
            self.displayCheck(2, 7, [u"a    "]), CTRL_S,
            self.displayCheck(0, 0, [u" ci    Save File As"]), CTRL_Q,
            self.displayCheck(0, 0, [u" ci     "]),
            self.displayCheck(-2, 0, [u"      "]), CTRL_Q,
            ord('n')
        ])

    def test_dir_and_path_with_cr(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.displayCheck(0, 0, [u" ci     "]),
            self.displayCheck(2, 7, [u"     "]), CTRL_O,
            self.displayCheck(0, 0, [u" ci    Open File  "]), CTRL_A,
            self.writeText(self.pathToSample(u"")),
            self.displayCheck(3, 0, [u"./     ", u"../     "]),
            self.displayCheck(5, 0, [u"._ A name with cr\\r/"]),
            self.addMouseInfo(0, 5, 0,
                              curses.BUTTON1_PRESSED), curses.KEY_MOUSE,
            self.displayCheck(5, 0, [u"example"]),
            self.displayFindCheck(u"/._ A name with ",
                                  u"cr\\r/"), KEY_ESCAPE, curses.ERR,
            self.displayCheck(0, 0, [u" ci     "]),
            self.displayCheck(2, 7, [u"     "]), CTRL_O,
            self.displayCheck(0, 0, [u" ci    Open File  "]), CTRL_A,
            self.writeText(self.pathToSample(u"._ A name")), CTRL_I,
            self.displayCheck(5, 0, [u"example"]),
            self.displayFindCheck(u"/._ A name with ", u"cr\\r/"), CTRL_Q,
            CTRL_Q
        ])

    def test_open(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.displayCheck(0, 0, [u" ci     "]),
            self.displayCheck(2, 7, [u"     "]), CTRL_O,
            self.displayCheck(0, 0, [u" ci    Open File  "]), CTRL_Q, CTRL_Q
        ])  # TODO(dschuyler): fix need for extra CTRL_Q.

    def test_open_binary_file(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.displayCheck(0, 0, [u" ci     "]),
            self.displayCheck(2, 7, [u"     "]), CTRL_O,
            self.displayCheck(0, 0, [u" ci    Open File  "]), CTRL_A,
            self.writeText(self.pathToSample(u"binary_test_file")), CTRL_J,
            self.displayCheck(2, 7, [u"006401006c1a005a0800640000640100"]),
            CTRL_Q
        ])

    def test_open_valid_unicode_file(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.displayCheck(0, 0, [u" ci     "]),
            self.displayCheck(2, 7, [u"     "]), CTRL_O,
            self.displayCheck(0, 0, [u" ci    Open File  "]), CTRL_A,
            self.writeText(self.pathToSample(u"valid_unicode")), CTRL_J,
            self.displayCheck(4, 7, [u"Здравствуйте"]), CTRL_Q
        ])

    def test_empty_path_input(self):
        """Avoid crash when pressing return when the path input is empty."""
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.displayCheck(0, 0, [u" ci     "]),
            self.displayCheck(2, 7, [u"     "]),
            CTRL_O,
            self.displayCheck(0, 0, [u" ci    Open File  "]),
            CTRL_A,
            KEY_BACKSPACE1,
            self.displayCheck(2, 7, [u"     "]),
            CTRL_J,
            self.displayCheck(0, 0, [u" ci    Open File  "]),
            KEY_ESCAPE,
            curses.ERR,
            self.displayCheck(0, 0, [u" ci     "]),
            CTRL_Q,
        ])

    def test_show_hide_columns(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.prefCheck(u'editor', u'filesShowSizes', True),
            self.displayCheck(0, 0, [u" ci     "]),
            CTRL_O,
            self.displayCheck(0, 0, [u" ci    Open"]),
            self.addClickInfo(1000, u"[x]sizes", curses.BUTTON1_PRESSED),
            curses.KEY_MOUSE,
            CTRL_Q
        ])

    def test_click_scroll(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.displayCheck(0, 0, [u" ci     "]),
            CTRL_O,
            self.displayCheck(0, 0, [u" ci    Open"]),
            KEY_PAGE_DOWN,
            self.displayFindCheck(u"AUTHORS", u""),
            CTRL_Q,
            # TODO(dschuyler): Quitting from the file manager uses two frame
            # updates. When that is fixed, this second CTRL_Q should be removed.
            CTRL_Q,
        ])
