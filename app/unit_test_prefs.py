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
    #testNumber('0x42', (0, 4))
    #testNumber('0x0', (0, 3))
    testNumber('.2342', (0, 5))
    testNumber('2.342', (0, 5))
    testNumber('23.42', (0, 5))
    testNumber('234.2', (0, 5))
    testNumber('2342.', (0, 5))

