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

performance1 = '''
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
        test = """/* first comment */
two
// second comment
#include "test.h"
void blah();
"""
        self.prefs = app.prefs.Prefs()
        self.parser.parse(None, self.prefs, test, self.prefs.grammars['cpp'], 0,
                          99999)
        #self.assertEqual(selectable.selection(), (0, 0, 0, 0))

    if 0:

        def test_profile_parse(self):
            profile = cProfile.Profile()
            parser = app.parser.Parser()
            path = 'app/actions.py'
            data = io.open(path).read()
            grammar = self.prefs.getGrammar(path)

            profile.enable()
            parser.parse(data, grammar, 0, sys.maxsize)
            profile.disable()

            output = io.StringIO.StringIO()
            stats = pstats.Stats(
                profile, stream=output).sort_stats('cumulative')
            stats.print_stats()
            print(output.getvalue())
