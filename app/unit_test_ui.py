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
import os
import sys

from app.curses_util import *
import app.ci_program
import app.fake_curses_testing

kTestFile = u'#application_test_file_with_unlikely_file_name~'


class UiBasicsTestCases(app.fake_curses_testing.FakeCursesTestCase):

    def setUp(self):
        self.longMessage = True
        if os.path.isfile(kTestFile):
            os.unlink(kTestFile)
        self.assertFalse(os.path.isfile(kTestFile))
        app.fake_curses_testing.FakeCursesTestCase.setUp(self)

    def test_logo(self):
        self.runWithTestFile(
            kTestFile,
            [
                #self.assertEqual(256, self.prg.prefs.startup['numColors']),
                self.displayCheck(0, 0, [u" ci "]),
                self.displayCheckStyle(0, 0, 1, len(" ci "),
                                       self.prg.prefs.color['logo']),
                CTRL_Q
            ])

    def test_prediction(self):
        #self.setMovieMode(True)
        self.runWithTestFile(
            kTestFile,
            [
                self.displayCheck(-1, 0, [u"      "]),
                #CTRL_P, self.displayCheck(-1, 0, ["p: "]), CTRL_J,
                self.displayCheck(-1, 0, [u"      "]),
                #CTRL_P, self.displayCheck(-1, 0, ["p: "]), CTRL_J,
                CTRL_Q
            ])

    def test_resize_screen(self):
        self.runWithTestFile(kTestFile, [
            self.displayCheck(0, 0, [
                u" ci    _file_with_unlikely_file_name~ . ",
                u"                                        ",
                u"     1                                  ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"Creating new file  |    1, 1 |   0%,  0%",
                u"                                        ",
            ]),
            self.resizeScreen(10, 36),
            self.displayCheck(0, 0, [
                u" ci    e_with_unlikely_file_name~ . ",
                u"                                    ",
                u"     1                              ",
                u"                                    ",
                u"                                    ",
                u"                                    ",
                u"                                    ",
                u"                                    ",
                u"                    1, 1 |   0%,  0%",
                u"                                    ",
            ]), CTRL_Q
        ])

    def test_save_on_close(self):
        #self.setMovieMode(True)
        self.runWithTestFile(kTestFile, [
            self.displayCheck(0, 0, [
                u" ci    " + kTestFile[-30:],
            ]),
            self.displayCheck(13, 0, [
                u"Creating new file  ",
                u"                   ",
            ]), u't',
            self.displayCheck(13, 0, [
                u"                   ",
                u"                   ",
            ]), CTRL_S,
            self.displayCheck(13, 0, [
                u"File saved    ",
                u"                   ",
            ]), u"e", CTRL_W,
            self.displayCheck(13, 0, [
                u"                   ",
                u"Save changes? (yes, no, or cancel):",
            ]), u"y",
            self.displayCheck(0, 0, [
                u" ci     . ",
            ]), CTRL_O,
            self.writeText(kTestFile), CTRL_J,
            #self.displayCheck(0, 0, [
            #    u" ci    " + kTestFile[-30:],
            #    u"            ",
            #    u"     1 te   ",
            #]),
            CTRL_Q
        ])

    def test_session(self):
        self.runWithTestFile(kTestFile, [
            self.displayCheck(0, 0, [
                u" ci    _file_with_unlikely_file_name~ . ",
                u"                                        ",
                u"     1                                  ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"Creating new file  |    1, 1 |   0%,  0%",
                u"                                        "
            ]), u'H', u'e', u'l', u'l', u'o',
            self.displayCheck(0, 0, [
                u" ci    _file_with_unlikely_file_name~ * ",
                u"                                        ",
                u"     1 Hello                            ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                        1, 6 |   0%,100%",
                u"                                        "
            ]), CTRL_Z,
            self.displayCheck(0, 0, [
                u" ci    _file_with_unlikely_file_name~ . ",
                u"                                        ",
                u"     1                                  ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                        1, 1 |   0%,  0%",
                u"                                        "
            ]), CTRL_Q
        ])

    def test_text_contents(self):
        self.runWithTestFile(kTestFile, [
            self.displayCheck(2, 7, [u"        "]), u't', u'e', u'x', u't',
            self.displayCheck(2, 7, [u"text "]), CTRL_Q, u'n'
        ])

    def test_whole_screen(self):
        #self.setMovieMode(True)
        self.runWithTestFile(kTestFile, [
            self.displayCheck(0, 0, [
                u" ci    _file_with_unlikely_file_name~ . ",
                u"                                        ",
                u"     1                                  ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"                                        ",
                u"Creating new file  |    1, 1 |   0%,  0%",
                u"                                        ",
            ]), CTRL_Q
        ])
