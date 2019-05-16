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
import unittest

import app.curses_util


class CursesUtilTestCases(unittest.TestCase):

    def test_curses_key_name(self):
        # These actually test the fake curses.
        def test1():
            curses.keyname(-3)

        self.assertRaises(ValueError, test1)

        def test2():
            curses.keyname([])

        self.assertRaises(TypeError, test2)

        def test3():
            curses.keyname(9**999)

        self.assertRaises(OverflowError, test3)

    def test_renderedFindIter(self):

        def test(line, startCol, endCol, matches):
            matches.reverse()
            for s, column, length, index in app.curses_util.renderedFindIter(
                    line, startCol, endCol, (u'[]{}()',), True, True):
                self.assertEqual(matches.pop(), (s, column, length, index))

        # Float and leading zero.
        line = u"""5.32e+30 a 000808"""
        test(line, 0, len(line), [
            (u'5.32e+30', 0, 8, 1),
            (u'000808', 11, 6, 1),
        ])

        # Parenthesis and number.
        line = u"""(23432ull a"""
        test(line, 0, len(line), [
            (u'(', 0, 1, 0),
            (u'23432ull', 1, 8, 1),
        ])

        # Multiple numbers and string of brackets.
        line = u"""23 five )}]](23432ull a"""
        test(line, 0, len(line), [
            (u'23', 0, 2, 1),
            (u')}]](', 8, 5, 0),
            (u'23432ull', 13, 8, 1),
        ])

        # Constrained columns.
        line = u"""23 five )}]](23432ull a"""
        test(line, 1,
             len(line) - 4, [
                 (u'3', 1, 1, 1),
                 (u')}]](', 8, 5, 0),
                 (u'23432u', 13, 6, 1),
             ])

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

    def test_rendered_sub_str(self):
        self.assertEqual(u"test", app.curses_util.renderedSubStr(u"test", 0))
        self.assertEqual(u"test", app.curses_util.renderedSubStr(u"test", 0, 4))
        self.assertEqual(u"est", app.curses_util.renderedSubStr(u"test", 1, 4))
        self.assertEqual(u"st", app.curses_util.renderedSubStr(u"test", 2, 4))
        self.assertEqual(u"t", app.curses_util.renderedSubStr(u"test", 3, 4))
        self.assertEqual(u"", app.curses_util.renderedSubStr(u"test", 4, 4))
        self.assertEqual(u"tes", app.curses_util.renderedSubStr(u"test", 0, 3))
        self.assertEqual(u"te", app.curses_util.renderedSubStr(u"test", 0, 2))
        self.assertEqual(u"t", app.curses_util.renderedSubStr(u"test", 0, 1))
        self.assertEqual(u"", app.curses_util.renderedSubStr(u"test", 0, 0))
        self.assertEqual(u"es", app.curses_util.renderedSubStr(u"test", 1, 3))
        self.assertEqual(u"", app.curses_util.renderedSubStr(u"test", 2, 2))
        self.assertEqual(u"eight", app.curses_util.renderedSubStr(
            u"eight", 0, 5))
        self.assertEqual(u"igh", app.curses_util.renderedSubStr(u"eight", 1, 4))
        self.assertEqual(u"g", app.curses_util.renderedSubStr(u"eight", 2, 3))
        self.assertEqual(u"", app.curses_util.renderedSubStr(u"eight", 3, 3))
        self.assertEqual(u"こんにちは",
                         app.curses_util.renderedSubStr(u"こんにちは", 0, 10))
        self.assertEqual(u" んにちは",
                         app.curses_util.renderedSubStr(u"こんにちは", 1, 10))
        self.assertEqual(u"んにちは", app.curses_util.renderedSubStr(
            u"こんにちは", 2, 10))
        self.assertEqual(u" にちは", app.curses_util.renderedSubStr(
            u"こんにちは", 3, 10))
        self.assertEqual(u"にちは", app.curses_util.renderedSubStr(
            u"こんにちは", 4, 10))
        self.assertEqual(u"は", app.curses_util.renderedSubStr(u"こんにちは", 8))
        self.assertEqual(u"は", app.curses_util.renderedSubStr(u"こんにちは", 8, 10))
        self.assertEqual(u" ", app.curses_util.renderedSubStr(u"こんにちは", 9, 10))
        self.assertEqual(u"", app.curses_util.renderedSubStr(u"こんにちは", 10, 10))
        self.assertEqual(u"こんにち ", app.curses_util.renderedSubStr(
            u"こんにちは", 0, 9))
        self.assertEqual(u"こんにち", app.curses_util.renderedSubStr(
            u"こんにちは", 0, 8))
        self.assertEqual(u"こんに ", app.curses_util.renderedSubStr(
            u"こんにちは", 0, 7))
        self.assertEqual(u"こんに", app.curses_util.renderedSubStr(u"こんにちは", 0, 6))
        self.assertEqual(u"こん ", app.curses_util.renderedSubStr(u"こんにちは", 0, 5))
        self.assertEqual(u"こん", app.curses_util.renderedSubStr(u"こんにちは", 0, 4))
        self.assertEqual(u"こ ", app.curses_util.renderedSubStr(u"こんにちは", 0, 3))
        self.assertEqual(u"こ", app.curses_util.renderedSubStr(u"こんにちは", 0, 2))
        self.assertEqual(u" ", app.curses_util.renderedSubStr(u"こんにちは", 0, 1))
        self.assertEqual(u"", app.curses_util.renderedSubStr(u"こんにちは", 0, 0))

        # Test past the length of the string.
        self.assertEqual(u"", app.curses_util.renderedSubStr(u"", 1, 1))
        self.assertEqual(u"test", app.curses_util.renderedSubStr(u"test", 0, 8))

    def test_rendered_width(self):
        self.assertEqual(0, app.curses_util.columnWidth(u""))
        self.assertEqual(4, app.curses_util.columnWidth(u"test"))

        self.assertEqual(2, app.curses_util.columnWidth(u"こ"))
        self.assertEqual(4, app.curses_util.columnWidth(u"こん"))
        self.assertEqual(6, app.curses_util.columnWidth(u"こんに"))
        self.assertEqual(10, app.curses_util.columnWidth(u"こんにちは"))

        self.assertEqual(3, app.curses_util.columnWidth(u"aこ"))
        self.assertEqual(5, app.curses_util.columnWidth(u"aこん"))
        self.assertEqual(3, app.curses_util.columnWidth(u"こc"))
        self.assertEqual(4, app.curses_util.columnWidth(u"aこc"))
        self.assertEqual(7, app.curses_util.columnWidth(u"aこbんc"))
