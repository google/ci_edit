# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.parser
import app.prefs
import unittest


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
    self.parser.parse(test, app.prefs.prefs['grammar']['cpp'])
    #self.assertEqual(selectable.selection(), (0, 0, 0, 0))
