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
