# Copyright 2017 Google Inc.
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
import app.prefs


class PrefsTestCases(app.fake_curses_testing.FakeCursesTestCase):

    def setUp(self):
        self.longMessage = True
        app.fake_curses_testing.FakeCursesTestCase.setUp(self)
        self.prefs = app.prefs.Prefs()

    def test_default_prefs(self):
        self.runWithFakeInputs([
            self.prefCheck(u'editor', u'saveUndo', True),
            CTRL_Q,
        ])

    def test_get_file_type(self):
        getFileType = self.prefs.getFileType
        self.assertEqual(getFileType(""), "words")
        self.assertEqual(getFileType("a.py"), "py")
        self.assertEqual(getFileType("a.cc"), "cpp")
        self.assertEqual(getFileType("a.c"), "c")
        self.assertEqual(getFileType("a.h"), "cpp")
        self.assertEqual(getFileType("Makefile"), "make")
        self.assertEqual(getFileType("BUILD"), "bazel")
        self.assertEqual(getFileType("build"), "words")
        self.assertEqual(getFileType("BUILD.gn"), "gn")
        self.assertEqual(getFileType("a.md"), "md")

    def test_tabs_to_spaces(self):
        tabsToSpaces = self.prefs.tabsToSpaces
        self.assertEqual(tabsToSpaces("words"), True)
        self.assertEqual(tabsToSpaces("make"), False)
        self.assertEqual(tabsToSpaces("cpp"), True)
        self.assertEqual(tabsToSpaces(None), False)
        self.assertEqual(tabsToSpaces("foo"), None)
