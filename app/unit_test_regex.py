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

#import re
import unittest

import app.regex


class RegexTestCases(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    pass

  def test_common_numbers(self):
    def testNumber(str, reg):
      sre = app.regex.kReNumbers.search(str)
      if sre is None:
        self.assertEqual(sre, reg)
        return
      self.assertEqual(reg, sre.regs[0])
    testNumber('quick', None)
    testNumber('0342', (0, 4))
    testNumber('2342', (0, 4))
    testNumber('0x42', (0, 4))
    testNumber('0x0', (0, 3))
    testNumber('.2342', (0, 5))
    testNumber('2.342', (0, 5))
    testNumber('23.42', (0, 5))
    testNumber('234.2', (0, 5))
    testNumber('2342.', (0, 5))
    testNumber('23q42.', (0, 2))
    testNumber(' 2u ', (1, 3))
    testNumber(' 2U ', (1, 3))
    testNumber(' 2ull ', (1, 5))
    testNumber(' 2ULL ', (1, 5))
    testNumber(' 2.f ', (1, 4))
    testNumber(' .3f ', (1, 4))
    testNumber(' 4.7234e-11 ', (1, 11))

