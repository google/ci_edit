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

import app.parser
import app.prefs
from timeit import timeit
import unittest


class PerformanceTestCases(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    pass

  def test_array_vs_getter(self):
    setup = '''data = ['a'] * 100\n'''
    setup += '''def get(n):\n'''
    setup += '''  return data[n]\n'''
    setup += '''class B:\n'''
    setup += '''  def __getitem__(self, n):\n'''
    setup += '''    return data[n]\n'''
    setup += '''b = B()\n'''
    a = timeit(
        '''x = data[5]\n''',
        setup=setup,
        number=10000)
    b = timeit(
        '''x = get(5)\n''',
        setup=setup,
        number=10000)
    c = timeit(
        '''x = b[5]\n''',
        setup=setup,
        number=10000)
    #print "\n%s %s %s | %s %s" % (a, b, a/b, c, a/c)
    # Calling a function or member is significantly slower than direct access.
    self.assertGreater(b, a * 1.7)
    self.assertGreater(c, a * 2)

  def test_slice_vs_startswith(self):
    setup = '''x = 'a' * 100\n'''
    a = timeit(
        '''x[:2] == "  "\n''',
        setup=setup,
        number=100000)
    b = timeit(
        '''x.startswith("  ")\n''',
        setup=setup,
        number=100000)
    c = timeit(
        '''x[0] == " " and x[1] == " "\n''',
        setup=setup,
        number=100000)
    #print "\na %s, b %s, c %s | %s %s" % (a, b, c, c, a/c)
    # Calling a function or member is significantly slower than direct access.
    self.assertGreater(b, a * 2.0)  # b is much slower.
    self.assertGreater(b, c * 2.0)  # b is much slower.
    self.assertGreater(a, c * 0.7)  # a and c are similar.
    self.assertGreater(c, a * 0.6)  # a and c are similar.

  def test_default_parameter(self):
    setup  = '''def withDefault(a, b=None):\n'''
    setup += '''  if b is not None: return b\n'''
    setup += '''  return a*a\n'''
    setup += '''def withoutDefault(a, b):\n'''
    setup += '''  if b is -1: return b\n'''
    setup += '''  return a*b\n'''
    a = timeit(
        '''withDefault(5);''' * 100,
        setup=setup,
        number=10000)
    b = timeit(
        '''withoutDefault(5, 0);''' * 100,
        setup=setup,
        number=10000)
    # Assert that neither too much faster than the other
    self.assertGreater(a, b * 0.81)
    self.assertGreater(b, a * 0.77)

  def test_insert1(self):
    return  # Remove to enable test (disabled due to running time).
    # This tests a performance assumption. If this test fails, the program
    # should still work fine, but it may not run as fast as it could by using
    # different assumptions.
    #
    # Insert into an array of strings is expected to be faster than insert into
    # a contiguous buffer of similar size.
    #
    # This is why ci_edit uses both a self.data buffer and a self.lines[] array.
    # Though splitting the data into lines is also expensive, see tests below.
    #
    # At 1,000 bytes the performance is similar.
    a = timeit('data1 = data1[:500] + "x" + data1[500:]',
        setup='data1 = "a" * 1000',
        number=10000)
    b = timeit('data2[5] = data2[5][:50] + "x" + data2[5][50:]',
        setup='data2 = ["a" * 100] * 10',
        number=10000)
    self.assertGreater(a, b * 0.8)
    self.assertLess(a, b * 4)
    # At 10,000 bytes the array of strings is 1.4 to 3 times faster.
    a = timeit('data1 = data1[:5000] + "x" + data1[5000:]',
        setup='data1 = "a" * 10000',
        number=10000)
    b = timeit('data2[50] = data2[50][:50] + "x" + data2[50][50:]',
        setup='data2 = ["a" * 100] * 100',
        number=10000)
    self.assertGreater(a, b * 1.4)
    self.assertLess(a, b * 4)
    # At 100,000 bytes the array of strings is 12 to 24 times faster.
    a = timeit('data1 = data1[:50000] + "x" + data1[50000:]',
        setup='data1 = "a" * 100000',
        number=10000)
    b = timeit('data2[500] = data2[500][:50] + "x" + data2[500][50:]',
        setup='data2 = ["a" * 100] * 1000',
        number=10000)
    self.assertGreater(a, b * 12)
    self.assertLess(a, b * 24)

  def test_split_insert(self):
    return  # Remove to enable test (disabled due to running time).
    # This tests a performance assumption. If this test fails, the program
    # should still work fine, but it may not run as fast as it could by using
    # different assumptions.
    #
    # With frequent splitting the performance reverses.
    for lineCount in (100, 1000, 5000):
      half = lineCount / 2
      a = timeit(r'''data2 = data1.split('\n'); \
              data2[%s] = data2[%s][:50] + "x" + data2[%s][50:]; \
              ''' % (half, half, half),
          setup=r'''data1 = ("a" * 100 + '\n') * %s''' % (lineCount,),
          number=10000)
      b = timeit('data1 = data1[:%s] + "x" + data1[%s:]' % (half, half),
          setup=r'''data1 = ("a" * 100 + '\n') * %s''' % (lineCount,),
          number=10000)
      print "\n%9s: %s %s" % (lineCount, a, b)
      self.assertGreater(a, b)

  def test_split_insert_balance(self):
    return  # Remove to enable test (disabled due to running time).
    # This tests a performance assumption. If this test fails, the program
    # should still work fine, but it may not run as fast as it could by using
    # different assumptions.
    #
    # With 5 inserts between splits, the performance is nearly the same.
    for lineCount in (100, 1000, 5000):
      half = lineCount / 2
      a = timeit(r'''data2 = data1.split('\n');'''+
              (r'''data2[%s] = data2[%s][:50] + "x" + data2[%s][50:]; \
              ''' % (half, half, half)) * 5,
          setup=r'''data1 = ("a" * 100 + '\n') * %s''' % (lineCount,),
          number=10000)
      b = timeit(('data1 = data1[:%s] + "x" + data1[%s:]; ' % (half, half)) * 5,
          setup=r'''data1 = ("a" * 100 + '\n') * %s''' % (lineCount,),
          number=10000)
      print "\n%9s: %s %s" % (lineCount, a, b)

