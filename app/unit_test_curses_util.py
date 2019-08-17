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
        self.assertIs(None, app.curses_util.columnToIndex(4, u"test"))
        self.assertIs(None, app.curses_util.columnToIndex(8, u"test"))

        self.assertEqual(0, app.curses_util.columnToIndex(0, u"\ttest\ttabs"))
        self.assertEqual(0, app.curses_util.columnToIndex(1, u"\ttest\ttabs"))
        self.assertEqual(0, app.curses_util.columnToIndex(2, u"\ttest\ttabs"))
        self.assertEqual(0, app.curses_util.columnToIndex(3, u"\ttest\ttabs"))
        self.assertEqual(0, app.curses_util.columnToIndex(4, u"\ttest\ttabs"))
        self.assertEqual(0, app.curses_util.columnToIndex(5, u"\ttest\ttabs"))
        self.assertEqual(0, app.curses_util.columnToIndex(6, u"\ttest\ttabs"))
        self.assertEqual(0, app.curses_util.columnToIndex(7, u"\ttest\ttabs"))
        self.assertEqual(1, app.curses_util.columnToIndex(8, u"\ttest\ttabs"))
        self.assertEqual(2, app.curses_util.columnToIndex(9, u"\ttest\ttabs"))
        self.assertEqual(3, app.curses_util.columnToIndex(10, u"\ttest\ttabs"))
        self.assertEqual(4, app.curses_util.columnToIndex(11, u"\ttest\ttabs"))
        self.assertEqual(5, app.curses_util.columnToIndex(12, u"\ttest\ttabs"))
        self.assertEqual(5, app.curses_util.columnToIndex(13, u"\ttest\ttabs"))
        self.assertEqual(5, app.curses_util.columnToIndex(14, u"\ttest\ttabs"))
        self.assertEqual(5, app.curses_util.columnToIndex(15, u"\ttest\ttabs"))
        self.assertEqual(6, app.curses_util.columnToIndex(16, u"\ttest\ttabs"))
        self.assertEqual(7, app.curses_util.columnToIndex(17, u"\ttest\ttabs"))
        self.assertEqual(8, app.curses_util.columnToIndex(18, u"\ttest\ttabs"))
        # Test past the length of the string.
        self.assertIs(None, app.curses_util.columnToIndex(21, u"\ttest\ttabs"))
        self.assertIs(None, app.curses_util.columnToIndex(22, u"\ttest\ttabs"))
        self.assertIs(None, app.curses_util.columnToIndex(999, u"\ttest\ttabs"))

        self.assertEqual(0, app.curses_util.columnToIndex(0, u"こんにちは"))
        self.assertEqual(0, app.curses_util.columnToIndex(1, u"こんにちは"))
        self.assertEqual(1, app.curses_util.columnToIndex(2, u"こんにちは"))
        self.assertEqual(1, app.curses_util.columnToIndex(3, u"こんにちは"))
        self.assertEqual(2, app.curses_util.columnToIndex(4, u"こんにちは"))
        self.assertEqual(4, app.curses_util.columnToIndex(8, u"こんにちは"))
        self.assertEqual(4, app.curses_util.columnToIndex(9, u"こんにちは"))
        # Test past the length of the string.
        self.assertIs(None, app.curses_util.columnToIndex(10, u"こんにちは"))
        self.assertIs(None, app.curses_util.columnToIndex(11, u"こんにちは"))
        self.assertIs(None, app.curses_util.columnToIndex(12, u"こんにちは"))


    def test_charAtColumn(self):
        cu = app.curses_util
        self.assertEqual(u"t", cu.charAtColumn(0, u"test"))
        self.assertEqual(u"e", cu.charAtColumn(1, u"test"))
        self.assertEqual(u"s", cu.charAtColumn(2, u"test"))
        self.assertEqual(u"t", cu.charAtColumn(3, u"test"))
        # Test past the length of the string.
        self.assertIs(None, cu.charAtColumn(4, u"test"))
        self.assertIs(None, cu.charAtColumn(8, u"test"))

        self.assertEqual(u"\t", cu.charAtColumn(0, u"\ttest\ttabs"))
        self.assertEqual(u"\t", cu.charAtColumn(1, u"\ttest\ttabs"))
        self.assertEqual(u"\t", cu.charAtColumn(2, u"\ttest\ttabs"))
        self.assertEqual(u"\t", cu.charAtColumn(3, u"\ttest\ttabs"))
        self.assertEqual(u"\t", cu.charAtColumn(4, u"\ttest\ttabs"))
        self.assertEqual(u"\t", cu.charAtColumn(5, u"\ttest\ttabs"))
        self.assertEqual(u"\t", cu.charAtColumn(6, u"\ttest\ttabs"))
        self.assertEqual(u"\t", cu.charAtColumn(7, u"\ttest\ttabs"))
        self.assertEqual(u"t", cu.charAtColumn(8, u"\ttest\ttabs"))
        self.assertEqual(u"e", cu.charAtColumn(9, u"\ttest\ttabs"))
        self.assertEqual(u"s", cu.charAtColumn(10, u"\ttest\ttabs"))
        self.assertEqual(u"t", cu.charAtColumn(11, u"\ttest\ttabs"))
        self.assertEqual(u"\t", cu.charAtColumn(12, u"\ttest\ttabs"))
        self.assertEqual(u"\t", cu.charAtColumn(13, u"\ttest\ttabs"))
        self.assertEqual(u"\t", cu.charAtColumn(14, u"\ttest\ttabs"))
        self.assertEqual(u"\t", cu.charAtColumn(15, u"\ttest\ttabs"))
        self.assertEqual(u"t", cu.charAtColumn(16, u"\ttest\ttabs"))
        self.assertEqual(u"a", cu.charAtColumn(17, u"\ttest\ttabs"))
        self.assertEqual(u"b", cu.charAtColumn(18, u"\ttest\ttabs"))
        self.assertEqual(u"s", cu.charAtColumn(19, u"\ttest\ttabs"))
        # Test past the length of the string.
        self.assertIs(None, cu.charAtColumn(20, u"\ttest\ttabs"))
        self.assertIs(None, cu.charAtColumn(21, u"\ttest\ttabs"))
        self.assertIs(None, cu.charAtColumn(999, u"\ttest\ttabs"))

        self.assertEqual(u"こ", cu.charAtColumn(0, u"こんにちは"))
        self.assertEqual(u"こ", cu.charAtColumn(1, u"こんにちは"))
        self.assertEqual(u"ん", cu.charAtColumn(2, u"こんにちは"))
        self.assertEqual(u"ん", cu.charAtColumn(3, u"こんにちは"))
        self.assertEqual(u"に", cu.charAtColumn(4, u"こんにちは"))
        self.assertEqual(u"は", cu.charAtColumn(8, u"こんにちは"))
        self.assertEqual(u"は", cu.charAtColumn(9, u"こんにちは"))
        # Test past the length of the string.
        self.assertIs(None, cu.charAtColumn(10, u"こんにちは"))
        self.assertIs(None, cu.charAtColumn(11, u"こんにちは"))
        self.assertIs(None, cu.charAtColumn(12, u"こんにちは"))

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

        # Test with tabs.
        self.assertEqual(u"   ", app.curses_util.renderedSubStr(
            u"\tこんにちは", 0, 3))
        self.assertEqual(u"     こ",
                         app.curses_util.renderedSubStr(u"\tこんにちは", 3, 10))
        self.assertEqual(u"        こん",
                         app.curses_util.renderedSubStr(u"\tこんにちは", 0, 12))
        self.assertEqual(u"        <tab",
                         app.curses_util.renderedSubStr(u"\t<tab", 0, None))
        self.assertEqual(
            u"         <tab+space",
            app.curses_util.renderedSubStr(u"\t <tab+space", 0, None))
        self.assertEqual(
            u"        <space+tab",
            app.curses_util.renderedSubStr(u" \t<space+tab", 0, None))
        self.assertEqual(u"a       <",
                         app.curses_util.renderedSubStr(u"a\t<", 0, None))
        self.assertEqual(
            u"some text.>     <",
            app.curses_util.renderedSubStr(u"some text.>\t<", 0, None))
        self.assertEqual(u"                <2tabs",
                         app.curses_util.renderedSubStr(u"\t\t<2tabs", 0, None))
        self.assertEqual(
            u"line    with    tabs",
            app.curses_util.renderedSubStr(u"line\twith\ttabs", 0, None))
        self.assertEqual(
            u"ends with tab>  ",
            app.curses_util.renderedSubStr(u"ends with tab>\t", 0, None))

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

    def test_char_width(self):
        self.assertEqual(0, app.curses_util.charWidth(u"", 0))
        self.assertEqual(8, app.curses_util.charWidth(u"\t", 0))
        self.assertEqual(1, app.curses_util.charWidth(u" ", 0))
        self.assertEqual(7, app.curses_util.charWidth(u"\t", 1))
        self.assertEqual(6, app.curses_util.charWidth(u"\t", 2))
        self.assertEqual(2, app.curses_util.charWidth(u"\t", 6))
        self.assertEqual(1, app.curses_util.charWidth(u"\t", 7))
        self.assertEqual(0, app.curses_util.charWidth(u"", 8))
        self.assertEqual(8, app.curses_util.charWidth(u"\t", 8))
        self.assertEqual(7, app.curses_util.charWidth(u"\t", 9))
        self.assertEqual(2, app.curses_util.charWidth(u"こ", 0))

    def test_prior_col(self):
        test = u"""\tfive\t"""
        prior_col = app.curses_util.priorCol
        self.assertEqual(None, prior_col(0, test))
        self.assertEqual(0, prior_col(1, test))
        self.assertEqual(0, prior_col(2, test))
        self.assertEqual(0, prior_col(3, test))
        self.assertEqual(0, prior_col(4, test))
        self.assertEqual(0, prior_col(5, test))
        self.assertEqual(0, prior_col(6, test))
        self.assertEqual(0, prior_col(7, test))
        self.assertEqual(0, prior_col(8, test))
        self.assertEqual(8, prior_col(9, test))
        self.assertEqual(9, prior_col(10, test))
        self.assertEqual(10, prior_col(11, test))
        self.assertEqual(11, prior_col(12, test))
        self.assertEqual(12, prior_col(13, test))
        self.assertEqual(12, prior_col(14, test))
        self.assertEqual(12, prior_col(15, test))
        self.assertEqual(12, prior_col(16, test))
        self.assertEqual(None, prior_col(17, test))
