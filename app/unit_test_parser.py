# Copyright 2016 Google Inc.
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

import cProfile
import io
import pstats
import sys
from timeit import timeit
import unittest

import app.parser
import app.prefs

performance1 = u'''
import app.parser
path = 'app/actions.py'
data = open(path).read()
grammar = self.prefs.getGrammar(path)
'''


class ParserTestCases(unittest.TestCase):

    def setUp(self):
        self.parser = app.parser.Parser()

    def tearDown(self):
        self.parser = None

    def test_parse(self):
        tests = [
            u"""/* first comment */
two
// second comment
#include "test.h"
void blah();
// No end of line""",
            u"""/* first comment */
two
// second comment
#include "test.h"
void blah();
""",
            u"""/* test includes */
// The malformed include on the next line is a regression test.
#include <test.h"
#include "test.h"
#include <test.h
#include "test.h"

#include <te"st.h>
#include "test>.h"

#include "test.h>
#include <test.h>
#include "test.h
#include <test.h>
void blah();

""",
        ]
        for test in tests:
            #self.assertEqual(test.splitlines(), test.split(u"\n"))
            lines = test.split(u"\n")
            self.prefs = app.prefs.Prefs()
            self.parser.parse(None, self.prefs, test,
                              self.prefs.grammars[u'cpp'], 0, 99999)
            #self.parser.debugLog(print, test)
            self.assertEqual(len(lines), self.parser.rowCount())
            for i, line in enumerate(lines):
                self.assertEqual(self.parser.rowText(i), line)
                self.assertEqual(
                    self.parser.rowTextAndWidth(i), (line, len(line)))
            for node in self.parser.parserNodes:
                # These tests have no double wide characters.
                self.assertEqual(node[app.parser.kBegin],
                                 node[app.parser.kVisual])
            self.parser.debug_checkLines(None, test)

    def test_parse_cpp_literal(self):
        test = u"""/* first comment */
char stuff = R"mine(two
// not a comment)mine";
void blah();
"""
        self.prefs = app.prefs.Prefs()
        self.parser.parse(None, self.prefs, test, self.prefs.grammars['cpp'], 0,
                          99999)
        self.assertEqual(self.parser.rowText(0), u"/* first comment */")
        self.assertEqual(self.parser.rowText(1), u"""char stuff = R"mine(two""")
        self.assertEqual(
            self.parser.grammarAt(0, 0),
            self.prefs.grammars[u'cpp_block_comment'])
        self.assertEqual(
            self.parser.grammarAt(1, 8), self.prefs.grammars[u'cpp'])
        self.assertEqual(
            self.parser.grammarAt(1, 18),
            self.prefs.grammars[u'cpp_string_literal'])
        self.assertEqual(
            self.parser.grammarAt(3, 7), self.prefs.grammars[u'cpp'])

    def test_parse_rs_raw_string(self):
        test = u"""// one
let stuff = r###"two
not an "## end
ignored " quote"###;
fn main { }
// two
"""
        self.prefs = app.prefs.Prefs()
        self.parser.parse(None, self.prefs, test, self.prefs.grammars[u'rs'], 0,
                          99999)
        self.assertEqual(self.parser.rowText(0), u"// one")
        self.assertEqual(self.parser.rowText(1), u"""let stuff = r###"two""")
        self.assertEqual(
            self.parser.grammarAt(0, 0),
            self.prefs.grammars[u'cpp_line_comment'])
        self.assertEqual(
            self.parser.grammarAt(1, 8), self.prefs.grammars[u'rs'])
        self.assertEqual(
            self.parser.grammarAt(1, 18), self.prefs.grammars[u'rs_raw_string'])
        self.assertEqual(
            self.parser.grammarAt(2, 12), self.prefs.grammars[u'rs_raw_string'])
        self.assertEqual(
            self.parser.grammarAt(3, 15), self.prefs.grammars[u'rs_raw_string'])
        self.assertEqual(
            self.parser.grammarAt(3, 12), self.prefs.grammars[u'rs_raw_string'])
        self.assertEqual(
            self.parser.grammarAt(4, 7), self.prefs.grammars[u'rs'])

    def test_parse_tabs(self):
        test = u"""\t<tab
\t <tab+space
 \t<space+tab
\ta<
a\t<
some text.>\t<
\t\t<2tabs
line\twith\ttabs
ends with tab>\t
\t
"""
        self.prefs = app.prefs.Prefs()
        p = self.parser
        self.parser.parse(None, self.prefs, test, self.prefs.grammars[u'rs'], 0,
                          99999)
        if 0:
            print("")
            for i,t in enumerate(test.splitlines()):
                print("{}: {}".format(i, repr(t)))
            p.debugLog(print, test)

        self.assertEqual(p.rowCount(), 11)

        self.assertEqual(p.rowText(0), u"\t<tab")
        self.assertEqual(p.rowText(1), u"\t <tab+space")
        self.assertEqual(p.rowText(2), u" \t<space+tab")
        self.assertEqual(p.rowText(3), u"\ta<")
        self.assertEqual(p.rowText(4), u"a\t<")
        self.assertEqual(p.rowText(5), u"some text.>\t<")
        self.assertEqual(p.rowText(6), u"\t\t<2tabs")
        self.assertEqual(p.rowText(7), u"line\twith\ttabs")
        self.assertEqual(p.rowText(8), u"ends with tab>\t")
        self.assertEqual(p.rowText(9), u"\t")

        self.assertEqual(p.rowTextAndWidth(0), (u"\t<tab", 12))
        self.assertEqual(p.rowTextAndWidth(1), (u"\t <tab+space", 19))
        self.assertEqual(p.rowTextAndWidth(2), (u" \t<space+tab", 18))
        self.assertEqual(p.rowTextAndWidth(3), (u"\ta<", 10))
        self.assertEqual(p.rowTextAndWidth(4), (u"a\t<", 9))
        self.assertEqual(p.rowTextAndWidth(5), (u"some text.>\t<", 17))
        self.assertEqual(p.rowTextAndWidth(6), (u"\t\t<2tabs", 22))
        self.assertEqual(p.rowTextAndWidth(7), (u"line\twith\ttabs", 20))
        self.assertEqual(p.rowTextAndWidth(8), (u"ends with tab>\t", 16))
        self.assertEqual(p.rowTextAndWidth(9), (u"\t", 8))

        self.assertEqual(p.rowWidth(0), 12)
        self.assertEqual(p.rowWidth(1), 19)
        self.assertEqual(p.rowWidth(2), 18)
        self.assertEqual(p.rowWidth(3), 10)
        self.assertEqual(p.rowWidth(4), 9)
        self.assertEqual(p.rowWidth(5), 17)
        self.assertEqual(p.rowWidth(6), 22)
        self.assertEqual(p.rowWidth(7), 20)
        self.assertEqual(p.rowWidth(8), 16)
        self.assertEqual(p.rowWidth(9), 8)

        self.assertEqual(p.grammarIndexFromRowCol(0, 0), 1)
        self.assertEqual(p.grammarIndexFromRowCol(0, 7), 1)
        self.assertEqual(p.grammarIndexFromRowCol(0, 8), 2)
        self.assertEqual(p.grammarIndexFromRowCol(1, 0), 1)

        #self.assertEqual(p.grammarAt(0, 0), 0)


        self.assertEqual(p.nextCharRowCol(999999, 0), None)
        # Test u"\t<tab".
        self.assertEqual(p.nextCharRowCol(0, 0), (0, 8))
        self.assertEqual(p.nextCharRowCol(0, 1), (0, 7))
        self.assertEqual(p.nextCharRowCol(0, 7), (0, 1))
        self.assertEqual(p.nextCharRowCol(0, 8), (0, 1))
        self.assertEqual(p.nextCharRowCol(0, 11), (0, 1))
        self.assertEqual(p.nextCharRowCol(0, 12), (1, -12))
        # Test u"\t\t<2tabs".
        self.assertEqual(p.nextCharRowCol(6, 0), (0, 8))
        self.assertEqual(p.nextCharRowCol(6, 8), (0, 8))
        self.assertEqual(p.nextCharRowCol(6, 16), (0, 1))
        self.assertEqual(p.nextCharRowCol(6, 22), (1, -22))
        # Test u"\t".
        self.assertEqual(p.nextCharRowCol(9, 0), (0, 8))
        self.assertEqual(p.nextCharRowCol(9, 8), (1, -8))
        self.assertEqual(p.nextCharRowCol(10, 0), None)

        # Test u"\t<tab".
        self.assertEqual(p.priorCharRowCol(0, 0), None)
        self.assertEqual(p.priorCharRowCol(0, 1), (0, -1))
        self.assertEqual(p.priorCharRowCol(0, 7), (0, -7))
        # Test u"\t\t<2tabs".
        self.assertEqual(p.priorCharRowCol(6, 1), (0, -1))
        self.assertEqual(p.priorCharRowCol(6, 5), (0, -5))
        self.assertEqual(p.priorCharRowCol(6, 8), (0, -8))
        self.assertEqual(p.priorCharRowCol(6, 9), (0, -1))
        self.assertEqual(p.priorCharRowCol(6, 15), (0, -7))
        self.assertEqual(p.priorCharRowCol(6, 16), (0, -8))
        self.assertEqual(p.priorCharRowCol(6, 17), (0, -1))
        self.assertEqual(p.priorCharRowCol(6, 18), (0, -1))
        self.assertEqual(p.priorCharRowCol(6, 19), (0, -1))
        self.assertEqual(p.priorCharRowCol(6, 20), (0, -1))
        # Test u"\t".
        self.assertEqual(p.priorCharRowCol(9, 1), (0, -1))
        self.assertEqual(p.priorCharRowCol(9, 5), (0, -5))
        self.assertEqual(p.priorCharRowCol(9, 8), (0, -8))

    if 0:

        def test_profile_parse(self):
            profile = cProfile.Profile()
            parser = app.parser.Parser()
            path = u'app/actions.py'
            data = io.open(path).read()
            grammar = self.prefs.getGrammar(path)

            profile.enable()
            parser.parse(data, grammar, 0, sys.maxsize)
            profile.disable()

            output = io.StringIO.StringIO()
            stats = pstats.Stats(
                profile, stream=output).sort_stats(u'cumulative')
            stats.print_stats()
            print(output.getvalue())
