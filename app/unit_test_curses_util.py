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

import unittest

import app.curses_util


class CursesUtilTestCases(unittest.TestCase):
  def test_column_to_index(self):
    self.assertEqual(0, app.curses_util.columnToIndex(0, u"test"))
    self.assertEqual(1, app.curses_util.columnToIndex(1, u"test"))
    self.assertEqual(2, app.curses_util.columnToIndex(2, u"test"))
    self.assertEqual(3, app.curses_util.columnToIndex(3, u"test"))
    # Test past the length of the string.
    self.assertEqual(3, app.curses_util.columnToIndex(4, u"test"))
    self.assertEqual(3, app.curses_util.columnToIndex(8, u"test"))

    self.assertEqual(0, app.curses_util.columnToIndex(0, u"こんにちは"))
    self.assertEqual(0, app.curses_util.columnToIndex(1, u"こんにちは"))
    self.assertEqual(1, app.curses_util.columnToIndex(2, u"こんにちは"))
    self.assertEqual(1, app.curses_util.columnToIndex(3, u"こんにちは"))
    self.assertEqual(2, app.curses_util.columnToIndex(4, u"こんにちは"))
    self.assertEqual(4, app.curses_util.columnToIndex(8, u"こんにちは"))
    self.assertEqual(4, app.curses_util.columnToIndex(9, u"こんにちは"))

    # Test past the length of the string.
    self.assertEqual(4, app.curses_util.columnToIndex(10, u"こんにちは"))
    self.assertEqual(4, app.curses_util.columnToIndex(11, u"こんにちは"))
    self.assertEqual(4, app.curses_util.columnToIndex(12, u"こんにちは"))

  def test_fit_to_rendered_width(self):
    self.assertEqual(0, app.curses_util.fitToRenderedWidth(0, u"test"))
    self.assertEqual(1, app.curses_util.fitToRenderedWidth(1, u"test"))
    self.assertEqual(2, app.curses_util.fitToRenderedWidth(2, u"test"))
    self.assertEqual(3, app.curses_util.fitToRenderedWidth(3, u"test"))
    self.assertEqual(4, app.curses_util.fitToRenderedWidth(4, u"test"))
    # Test past the length of the string.
    self.assertEqual(4, app.curses_util.fitToRenderedWidth(8, u"test"))

    self.assertEqual(0, app.curses_util.fitToRenderedWidth(0, u"こんにちは"))
    self.assertEqual(0, app.curses_util.fitToRenderedWidth(1, u"こんにちは"))
    self.assertEqual(1, app.curses_util.fitToRenderedWidth(2, u"こんにちは"))
    self.assertEqual(1, app.curses_util.fitToRenderedWidth(3, u"こんにちは"))
    self.assertEqual(2, app.curses_util.fitToRenderedWidth(4, u"こんにちは"))
    self.assertEqual(4, app.curses_util.fitToRenderedWidth(8, u"こんにちは"))
    self.assertEqual(4, app.curses_util.fitToRenderedWidth(9, u"こんにちは"))
    self.assertEqual(5, app.curses_util.fitToRenderedWidth(10, u"こんにちは"))

    # Test past the length of the string.
    self.assertEqual(5, app.curses_util.fitToRenderedWidth(11, u"こんにちは"))
    self.assertEqual(5, app.curses_util.fitToRenderedWidth(12, u"こんにちは"))

  def test_rendered_width(self):
    self.assertEqual(0, app.curses_util.renderedWidth(u""))
    self.assertEqual(4, app.curses_util.renderedWidth(u"test"))

    self.assertEqual(2, app.curses_util.renderedWidth(u"こ"))
    self.assertEqual(4, app.curses_util.renderedWidth(u"こん"))
    self.assertEqual(6, app.curses_util.renderedWidth(u"こんに"))
    self.assertEqual(10, app.curses_util.renderedWidth(u"こんにちは"))

    self.assertEqual(3, app.curses_util.renderedWidth(u"aこ"))
    self.assertEqual(5, app.curses_util.renderedWidth(u"aこん"))
    self.assertEqual(3, app.curses_util.renderedWidth(u"こc"))
    self.assertEqual(4, app.curses_util.renderedWidth(u"aこc"))
    self.assertEqual(7, app.curses_util.renderedWidth(u"aこbんc"))

