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

from app.bookmark import Bookmark
import app.prefs
import app.text_buffer
import app.window


class BookmarkTestCases(unittest.TestCase):
  def setUp(self):
    self.fakeHost = mock.Mock()
    self.textBuffer = app.text_buffer.TextBuffer()
    self.textBuffer.lines = 50
    self.lineNumbers = app.window.LineNumbers(self.fakeHost)
    self.lineNumbers.rows = 30
    self.lineNumbers.parent = self.fakeHost
    self.fakeHost.lineNumberColumn = self.lineNumbers
    self.fakeHost.textBuffer = self.textBuffer
    self.fakeHost.scrollRow = self.fakeHost.cursorRow = 0

  def tearDown(self):
    pass

  def test_bookmark_comparisons(self):
    b1 = Bookmark(1, 5)
    b2 = Bookmark(1, 3)
    self.assertTrue(b1 > b2)
    self.assertTrue(b1 >= b2)
    self.assertFalse(b1 < b2)
    self.assertFalse(b1 <= b2)
    self.assertTrue(b2 < b1)
    self.assertTrue(b2 <= b1)
    self.assertFalse(b2 > b1)
    self.assertFalse(b2 >= b1)
    self.assertTrue(b1 != b2)
    self.assertFalse(b1 == b2)
    self.assertFalse(hash(b1) == hash(b2))

    b1 = Bookmark(2, 5)
    # b2 = Bookmark(1, 3)
    self.assertTrue(b1 > b2)
    self.assertTrue(b1 >= b2)
    self.assertFalse(b1 < b2)
    self.assertFalse(b1 <= b2)
    self.assertTrue(b2 < b1)
    self.assertTrue(b2 <= b1)
    self.assertFalse(b2 > b1)
    self.assertFalse(b2 >= b1)
    self.assertTrue(b1 != b2)
    self.assertFalse(b1 == b2)
    self.assertFalse(hash(b1) == hash(b2))

    # b1 = Bookmark(2, 5)
    b2 = Bookmark(1, 10)
    self.assertTrue(b1 > b2)
    self.assertTrue(b1 >= b2)
    self.assertFalse(b1 < b2)
    self.assertFalse(b1 <= b2)
    self.assertTrue(b2 < b1)
    self.assertTrue(b2 <= b1)
    self.assertFalse(b2 > b1)
    self.assertFalse(b2 >= b1)
    self.assertTrue(b1 != b2)
    self.assertFalse(b1 == b2)
    self.assertFalse(hash(b1) == hash(b2))

    b1 = Bookmark(1, 10)
    # b2 = Bookmark(1, 10)
    self.assertFalse(b1 > b2)
    self.assertTrue(b1 >= b2)
    self.assertFalse(b1 < b2)
    self.assertTrue(b1 <= b2)
    self.assertFalse(b2 < b1)
    self.assertTrue(b2 <= b1)
    self.assertFalse(b2 > b1)
    self.assertTrue(b2 >= b1)
    self.assertFalse(b1 != b2)
    self.assertTrue(b1 == b2)
    self.assertTrue(hash(b1) == hash(b2))

    # b1 - Bookmark(1, 10)
    b2 = Bookmark(-10, 10)
    self.assertTrue(b1 > b2)
    self.assertTrue(b1 >= b2)
    self.assertFalse(b1 < b2)
    self.assertFalse(b1 <= b2)
    self.assertTrue(b2 < b1)
    self.assertTrue(b2 <= b1)
    self.assertFalse(b2 > b1)
    self.assertFalse(b2 >= b1)
    self.assertTrue(b1 != b2)
    self.assertFalse(b1 == b2)
    self.assertFalse(hash(b1) == hash(b2))

  def test_bookmark_contains(self):
    def checkRanges(bookmark):
      """
      Checks that every integer between the bookmark's interval is 'in'
      the bookmark. It also checks if the two integers outside of the bookmark's
      range on both sides of its interval are NOT 'in' the bookmark.
      """
      begin = bookmark.begin
      end = bookmark.end
      for i in range(begin, end + 1):
        self.assertTrue(i in bookmark)
      self.assertFalse(begin - 2 in bookmark)
      self.assertFalse(begin - 1 in bookmark)
      self.assertFalse(end + 1 in bookmark)
      self.assertFalse(end + 2 in bookmark)

    checkRanges(Bookmark(1, 5))
    checkRanges(Bookmark(-3, 3))
    checkRanges(Bookmark(-5000, -4990))

    # Check intervals of length 0
    checkRanges(Bookmark(0, 0))
    checkRanges(Bookmark(5000, 5000))
    checkRanges(Bookmark(-5000, 5000))

    b = Bookmark(3, float('inf'))
    self.assertTrue(1000000 in b)
    self.assertTrue(float('inf') in b)

  def test_bookmark_overlap(self):
    b1 = Bookmark(1, 5)
    b2 = Bookmark(1, 5)
    self.assertTrue(b1.overlaps(b2))
    self.assertTrue(b2.overlaps(b1))

    b1 = Bookmark(2, 5)
    b2 = Bookmark(1, 5)
    self.assertTrue(b1.overlaps(b2))
    self.assertTrue(b2.overlaps(b1))

    b1 = Bookmark(1, 3)
    b2 = Bookmark(1, 5)
    self.assertTrue(b1.overlaps(b2))
    self.assertTrue(b2.overlaps(b1))

    b1 = Bookmark(3, 4)
    b2 = Bookmark(1, 5)
    self.assertTrue(b1.overlaps(b2))
    self.assertTrue(b2.overlaps(b1))

    b1 = Bookmark(3, 10)
    b2 = Bookmark(1, 5)
    self.assertTrue(b1.overlaps(b2))
    self.assertTrue(b2.overlaps(b1))

    b1 = Bookmark(5, 10)
    b2 = Bookmark(1, 5)
    self.assertTrue(b1.overlaps(b2))
    self.assertTrue(b2.overlaps(b1))

    b1 = Bookmark(-5, 0)
    b2 = Bookmark(-5, 5)
    self.assertTrue(b1.overlaps(b2))
    self.assertTrue(b2.overlaps(b1))

    b1 = Bookmark(0, 0)
    b2 = Bookmark(0, 0)
    self.assertTrue(b1.overlaps(b2))
    self.assertTrue(b2.overlaps(b1))

    b1 = Bookmark(0, 0)
    b2 = Bookmark(-5, float('inf'))
    self.assertTrue(b1.overlaps(b2))
    self.assertTrue(b2.overlaps(b1))

  def test_bookmark_properties(self):
    b1 = Bookmark(3, 5)
    self.assertTrue(b1.begin == 3)
    self.assertTrue(b1.end == 5)
    self.assertTrue(b1.range == (3, 5))

    b1.range = (10, 20)
    self.assertTrue(b1.begin == 10)
    self.assertTrue(b1.end == 20)
    self.assertTrue(b1.range == (10, 20))

    b1.range = (20, 10)
    self.assertTrue(b1.begin == 10)
    self.assertTrue(b1.end == 20)
    self.assertTrue(b1.range == (10, 20))

    b1.range = (3,)
    self.assertTrue(b1.begin == 3)
    self.assertTrue(b1.end == 3)
    self.assertTrue(b1.range == (3, 3))

    b1.begin = -3
    self.assertTrue(b1.begin == -3)
    self.assertTrue(b1.end == 3)
    self.assertTrue(b1.range == (-3, 3))

    b1.begin = 10
    self.assertTrue(b1.begin == 3)
    self.assertTrue(b1.end == 10)
    self.assertTrue(b1.range == (3, 10))

    b1.end = 15
    self.assertTrue(b1.begin == 3)
    self.assertTrue(b1.end == 15)
    self.assertTrue(b1.range == (3, 15))

    b1.end = -5
    self.assertTrue(b1.begin == -5)
    self.assertTrue(b1.end == 3)
    self.assertTrue(b1.range == (-5, 3))

    b1.begin = float('inf')
    self.assertTrue(b1.begin == 3)
    self.assertTrue(b1.end == float('inf'))
    self.assertTrue(b1.range == (3, float('inf')))

  def test_get_next_bookmark_color(self):
    def test_with_an_x_colored_terminal(x):
      mock.patch.dict(app.prefs.startup, {'numColors': x}, clear=True)
      colors = set()
      expectedNumberOfColors = 5
      for _ in range(expectedNumberOfColors):
        color = self.textBuffer.getBookmarkColor()
        # Make sure that a color index is returned.
        self.assertEqual(type(color), int)
        colors.add(color)
      # Test that all colors were different.
      self.assertEqual(len(colors), expectedNumberOfColors)
      color = self.textBuffer.getBookmarkColor()
      colors.add(color)
      # Test that the function rotates 5 colors.
      self.assertEqual(len(colors), expectedNumberOfColors)

      # Test for 8-colored mode
      test_with_an_x_colored_terminal(8)

      # Test for 256-colored mode
      test_with_an_x_colored_terminal(256)

  def test_get_visible_bookmarks(self):
    # Set up mock objects to test the LineNumbers methods.

    self.textBuffer.bookmarks = [Bookmark(0, 0), Bookmark(10, 10), Bookmark(20, 20),
                                 Bookmark(30, 30), Bookmark(40, 40)]
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, self.fakeHost.scrollRow + self.lineNumbers.rows)
    expectedBookmarks = {Bookmark(0, 0), Bookmark(10, 10), Bookmark(20, 20)}
    self.assertEqual(set(visibleBookmarks), expectedBookmarks)
    self.assertEqual(len(visibleBookmarks), len(expectedBookmarks))

    self.fakeHost.scrollRow = 20
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, 20 + self.lineNumbers.rows)
    expectedBookmarks = {Bookmark(20, 20), Bookmark(30, 30), Bookmark(40, 40)}
    self.assertEqual(set(visibleBookmarks), expectedBookmarks)
    self.assertEqual(len(visibleBookmarks), len(expectedBookmarks))

    self.fakeHost.scrollRow = 21
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, self.fakeHost.scrollRow + self.lineNumbers.rows)
    expectedBookmarks = {Bookmark(30, 30), Bookmark(40, 40)}
    self.assertEqual(set(visibleBookmarks), expectedBookmarks)
    self.assertEqual(len(visibleBookmarks), len(expectedBookmarks))

    self.fakeHost.scrollRow = 21
    self.lineNumbers.rows = 10
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, self.fakeHost.scrollRow + self.lineNumbers.rows)
    expectedBookmarks = {Bookmark(30, 30)}
    self.assertEqual(set(visibleBookmarks), expectedBookmarks)
    self.assertEqual(len(visibleBookmarks), len(expectedBookmarks))

    self.lineNumbers.rows = 9
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, self.fakeHost.scrollRow + self.lineNumbers.rows)
    expectedBookmarks = {}
    self.assertEqual(visibleBookmarks, [])

    self.fakeHost.scrollRow = 10
    self.textBuffer.bookmarks = [Bookmark(0, 10), Bookmark(11, 29),
                                 Bookmark(30, 45), Bookmark(46, 49)]
    self.lineNumbers.rows = 15
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, self.fakeHost.scrollRow + self.lineNumbers.rows)
    expectedBookmarks = {Bookmark(0, 10), Bookmark(11, 29)}
    self.assertEqual(set(visibleBookmarks), expectedBookmarks)
    self.assertEqual(len(visibleBookmarks), len(expectedBookmarks))
