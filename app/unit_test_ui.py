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
import app.prefs


kTestFile = u'#application_test_file_with_unlikely_file_name~'


class UiBasicsTestCases(app.fake_curses_testing.FakeCursesTestCase):
  def setUp(self):
    self.longMessage = True
    if True:
      # The buffer manager will retain the test file in RAM. Reset it.
      try:
        del sys.modules['app.buffer_manager']
        import app.buffer_manager
      except KeyError:
        pass
    if os.path.isfile(kTestFile):
      os.unlink(kTestFile)
    self.assertFalse(os.path.isfile(kTestFile))
    app.fake_curses_testing.FakeCursesTestCase.setUp(self)

  def test_logo(self):
    self.runWithTestFile(kTestFile, [
        #self.assertEqual(256, app.prefs.startup['numColors']),
        self.displayCheck(0, 0, [" ci "]),
        self.displayCheckStyle(0, 0, 1, len(" ci "), app.prefs.color['logo']),
        CTRL_Q])

  def test_whole_screen(self):
    #self.setMovieMode(True)
    self.runWithTestFile(kTestFile, [
        self.displayCheck(0, 0, [
            u" ci     .                               ",
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
            u"New buffer         |    1, 1 |   0%,  0%",
            u"                                        ",
            ]), CTRL_Q])

  def test_resize_screen(self):
    self.runWithTestFile(kTestFile, [
        self.displayCheck(0, 0, [
            u" ci     .                               ",
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
            u"New buffer         |    1, 1 |   0%,  0%",
            u"                                        ",
            ]),
        self.resizeScreen(10, 36),
        self.displayCheck(0, 0, [
            u" ci     .                           ",
            u"                                    ",
            u"     1                              ",
            u"                                    ",
            u"                                    ",
            u"                                    ",
            u"                                    ",
            u"                                    ",
            u"                    1, 1 |   0%,  0%",
            u"                                    ",
            ]),
            CTRL_Q])

  def test_prediction(self):
    #self.setMovieMode(True)
    self.runWithTestFile(kTestFile, [
        self.displayCheck(-1, 0, [u"      "]),
        #CTRL_P, self.displayCheck(-1, 0, ["p: "]), CTRL_J,
        self.displayCheck(-1, 0, [u"      "]),
        #CTRL_P, self.displayCheck(-1, 0, ["p: "]), CTRL_J,
        CTRL_Q])

  def test_text_contents(self):
    self.runWithTestFile(kTestFile, [
        self.displayCheck(2, 7, [u"        "]), u't', u'e', u'x', u't',
        self.displayCheck(2, 7, [u"text "]),  CTRL_Q, u'n'])

  def test_session(self):
    self.runWithTestFile(kTestFile, [
        self.displayCheck(0, 0, [
            u" ci     .                               ",
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
            u"New buffer         |    1, 1 |   0%,  0%",
            u"                                        "]),
        u'H', u'e', u'l', u'l', u'o',
        self.displayCheck(0, 0, [
            u" ci     *                               ",
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
            u"                                        "]),
        CTRL_Z,
        self.displayCheck(0, 0, [
            u" ci     .                               ",
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
            u"                                        "]),
        CTRL_Q])
