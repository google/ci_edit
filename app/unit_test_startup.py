
# -*- coding: utf-8 -*-
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

kTestFile = u'#startup_test_file_with_unlikely_file_name~'


class StartupTestCases(app.fake_curses_testing.FakeCursesTestCase):

    def setUp(self):
        self.longMessage = True
        app.fake_curses_testing.FakeCursesTestCase.setUp(self)

    def test_no_args(self):
        self.runWithFakeInputs([
            self.displayCheck(2, 7, [u"      "]),
            self.cursorCheck(2, 7),
            CTRL_Q
        ])

    def test_one_file(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.displayCheck(2, 7, [u"// Copyright "]),
            self.cursorCheck(2, 7),
            CTRL_Q
        ], [sys.argv[0], self.pathToSample(u"sample.cc")])

    def test_two_files(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            KEY_PAGE_DOWN,
            self.displayCheck(5, 7, [u"// This is a C++ sample file"]),
            self.cursorCheck(2, 7), CTRL_W,
            KEY_PAGE_DOWN,
            self.displayCheck(5, 7, [u"// This is a C++ sample header"]),
            CTRL_Q
        ], [sys.argv[0], self.pathToSample(u"sample.cc"),
        self.pathToSample(u"sample.h")])

    def test_one_file_line(self):
        #self.setMovieMode(True)
        self.runWithFakeInputs([
            self.displayCheck(2, 7, [u"// distributed under the License"]),
            self.cursorCheck(4, 7),
            CTRL_Q
        ], [sys.argv[0], self.pathToSample(u"sample.cc:12")])
