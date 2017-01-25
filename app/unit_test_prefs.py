# Copyright 2017 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.prefs
import re
import unittest


numbersRe = re.compile(app.prefs.joinReList(app.prefs.__common_numbers))


class PrefsTestCases(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    pass

  def test_common_numbers(self):
    def testNumber(str, reg):
      sre = numbersRe.search(str)
      for i,s in enumerate(sre.groups()):
        if s is not None:
          self.assertEqual(sre.regs[i+1], reg)
          self.assertEqual(s, str)
    testNumber('0342', (0, 4))
    testNumber('2342', (0, 4))
    testNumber('0x42', (0, 4))
    testNumber('0x0', (0, 3))
    testNumber('.2342', (0, 5))
    testNumber('2.342', (0, 5))
    testNumber('23.42', (0, 5))
    testNumber('234.2', (0, 5))
    testNumber('2342.', (0, 5))

