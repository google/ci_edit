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

import os
import sys
import unittest

from app.bookmark import Bookmark
from app.curses_util import *
import app.fake_curses_testing
import app.prefs
import app.text_buffer
import app.window


kTestFile = '#bookmarks_test_file_with_unlikely_file_name~'


class BookmarkTestCases(app.fake_curses_testing.FakeCursesTestCase):
  def setUp(self):
    if True:
      # The buffer manager will retain the test file in RAM. Reset it.
      try:
        del sys.modules['app.buffer_manager']
        import app.buffer_manager
      except KeyError:
        pass
    if os.path.isfile(kTestFile):
      os.unlink(kTestFile)
    self.assertFalse(os.path.isfile(kTestFile))
    self.fakeHost = app.window.ViewWindow(None)
    self.textBuffer = app.text_buffer.TextBuffer()
    self.textBuffer.lines = 50
    self.lineNumbers = app.window.LineNumbers(self.fakeHost)
    self.lineNumbers.rows = 30
    self.lineNumbers.parent = self.fakeHost
    self.fakeHost.lineNumberColumn = self.lineNumbers
    self.fakeHost.textBuffer = self.textBuffer
    self.fakeHost.scrollRow = self.fakeHost.cursorRow = 0
    app.fake_curses_testing.FakeCursesTestCase.setUp(self)

  def tearDown(self):
    app.fake_curses_testing.FakeCursesTestCase.tearDown(self)

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

    # Check intervals of length 0.
    checkRanges(Bookmark(0, 0))
    checkRanges(Bookmark(5000, 5000))
    checkRanges(Bookmark(-5000, 5000))

    b = Bookmark(-3.99, 3.99) # Floats get casted to int (rounds towards zero).
    self.assertFalse(-4 in b)
    self.assertTrue(-3 in b)
    self.assertFalse(4 in b)
    self.assertTrue(3 in b)

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
    b2 = Bookmark(-5, 99)
    self.assertTrue(b1.overlaps(b2))
    self.assertTrue(b2.overlaps(b1))

    b1 = Bookmark(0, 0)
    b2 = Bookmark(-5, -1)
    self.assertFalse(b1.overlaps(b2))
    self.assertFalse(b2.overlaps(b1))

    b1 = Bookmark(5, 5)
    b2 = Bookmark(6, 9)
    self.assertFalse(b1.overlaps(b2))
    self.assertFalse(b2.overlaps(b1))

    b1 = Bookmark(3, 5)
    b2 = Bookmark(5, 8)
    self.assertTrue(b1.overlaps(b2))
    self.assertTrue(b2.overlaps(b1))

    b1 = Bookmark(-3.999, 3.999) # Rounds to range (-3, 3).
    b2 = Bookmark(-5, -4)
    self.assertFalse(b1.overlaps(b2))
    self.assertFalse(b2.overlaps(b1))

    b1 = Bookmark(-3.001, 3.001) # Rounds to range (-3, 3).
    b2 = Bookmark(3.99, 9.0) # Rounds to range (3, 9).
    self.assertTrue(b1.overlaps(b2))
    self.assertTrue(b2.overlaps(b1))

  def test_bookmark_properties(self):
    b = Bookmark(3, 5)
    self.assertTrue(b.begin == 3)
    self.assertTrue(b.end == 5)
    self.assertTrue(b.range == (3, 5))

    b = Bookmark(-5.99, 5.99) # Test constructor
    self.assertTrue(b.begin == -5)
    self.assertTrue(b.end == 5)
    self.assertTrue(b.range == (-5, 5))

    b.range = (10, 20)
    self.assertTrue(b.begin == 10)
    self.assertTrue(b.end == 20)
    self.assertTrue(b.range == (10, 20))

    b.range = (20, 10)
    self.assertTrue(b.begin == 10)
    self.assertTrue(b.end == 20)
    self.assertTrue(b.range == (10, 20))

    b.range = (3, 3)
    self.assertTrue(b.begin == 3)
    self.assertTrue(b.end == 3)
    self.assertTrue(b.range == (3, 3))

    b.begin = -3
    self.assertTrue(b.begin == -3)
    self.assertTrue(b.end == 3)
    self.assertTrue(b.range == (-3, 3))

    b.begin = 10
    self.assertTrue(b.begin == 3)
    self.assertTrue(b.end == 10)
    self.assertTrue(b.range == (3, 10))

    b.end = 15
    self.assertTrue(b.begin == 3)
    self.assertTrue(b.end == 15)
    self.assertTrue(b.range == (3, 15))

    b.end = -5
    self.assertTrue(b.begin == -5)
    self.assertTrue(b.end == 3)
    self.assertTrue(b.range == (-5, 3))

    b.begin = 3.9
    self.assertTrue(b.begin == 3)
    self.assertTrue(b.end == 3)
    self.assertTrue(b.range == (3, 3))

    b.end = 2.99
    self.assertTrue(b.begin == 2)
    self.assertTrue(b.end == 3)
    self.assertTrue(b.range == (2, 3))

    b.range = (-9.99, 9.99)
    self.assertTrue(b.begin == -9)
    self.assertTrue(b.end == 9)
    self.assertTrue(b.range == (-9, 9))

  def test_get_next_bookmark_color(self):
    try:
      import mock
    except ImportError:
      startYellow = '\033[93m'
      disableColor = '\033[0m'
      startBlue = '\033[94m'
      exceptionMessage = (startYellow + "This test could " +
          "not execute because the 'mock' module could not be found. If " +
          "you would like to run this test, please install the mock module " +
          "for python 2.7. You can visit their website at " + startBlue +
          "https://pypi.python.org/pypi/mock " + startYellow + "or you can " +
          "try running " + startBlue + "pip install mock." + disableColor)
      #raise Exception(exceptionMessage)
      print(exceptionMessage)
      return
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
    # Set up the fake objects to test the LineNumbers methods.
    self.textBuffer.bookmarks = [Bookmark(0, 0), Bookmark(10, 10),
                                 Bookmark(20, 20), Bookmark(30, 30),
                                 Bookmark(40, 40)]
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, self.fakeHost.scrollRow + self.lineNumbers.rows)
    expectedBookmarks = {Bookmark(0, 0), Bookmark(10, 10), Bookmark(20, 20)}

    # Check that visibleBookmarks contains all the correct bookmarks
    self.assertEqual(set(visibleBookmarks), expectedBookmarks)
    # Check that the number of bookmarks is the same, as set removes duplicates.
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

  def test_bookmarks_jump(self):
    # self.setMovieMode(True)
    self.runWithTestFile(kTestFile, [
        self.displayCheck(0, 0, [
            " ci     .                               ",
            "                                        ",
            "     1                                  ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "New buffer         |    1, 1 |   0%,  0%",
            "                                        "]),
        self.writeText('one'),
        CTRL_E, 'b', 'm', CTRL_J, CTRL_J, # Create bookmark and go to next line.
        CTRL_E, 'b', 'm', CTRL_J, # Create bookmark.
        self.writeText('two'), CTRL_J,
        self.writeText('three'),
        CTRL_E, 'b', 'm', CTRL_J, CTRL_J, # Create bookmark and go to next line.
        self.writeText('four'), CTRL_J,
        self.writeText('five'), CTRL_J,
        self.writeText('six'), CTRL_J,
        self.writeText('seven'), CTRL_J,
        self.writeText('eight'), CTRL_J,
        CTRL_E, 'b', 'm', CTRL_J, # Create a new bookmark.
        self.writeText('nine'), CTRL_J,
        self.writeText('ten'), CTRL_J,
        self.writeText('eleven'), CTRL_J,
        self.writeText('twelve'), CTRL_J,
        self.writeText('thirteen'), CTRL_J,
        self.writeText('fourteen'), CTRL_J,
        self.writeText('fifteen'), CTRL_J,
        self.writeText('sixteen'), CTRL_J,
        self.writeText('seventeen'), CTRL_J,
        self.writeText('eighteen'), CTRL_J,
        self.writeText('nineteen'), CTRL_J,
        self.writeText('twenty'), CTRL_J,
        self.writeText('twenty-one'), CTRL_J,
        self.writeText('twenty-two'), CTRL_J,
        self.writeText('twenty-three'),
        CTRL_E, 'b', 'm', CTRL_J, # Create a new bookmark.
        # Bookmarks are at positions (1, 4), (2, 1), (3, 6) (9, 1), (23, 13).
        # Note that rows here start at 1, so 1 is the first row.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "    13 thirteen                         ",
            "    14 fourteen                         ",
            "    15 fifteen                          ",
            "    16 sixteen                          ",
            "    17 seventeen                        ",
            "    18 eighteen                         ",
            "    19 nineteen                         ",
            "    20 twenty                           ",
            "    21 twenty-one                       ",
            "    22 twenty-two                       ",
            "    23 twenty-three                     ",
            "Added bookmark     |   23,13 |  95%,100%",
            "                                        "]),
        KEY_F2, # Jump to the first bookmark (1, 4).
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 one                              ",
            "     2 two                              ",
            "     3 three                            ",
            "     4 four                             ",
            "     5 five                             ",
            "     6 six                              ",
            "     7 seven                            ",
            "     8 eight                            ",
            "     9 nine                             ",
            "    10 ten                              ",
            "    11 eleven                           ",
            "                        1, 4 |   0%,100%",
            "                                        "]),
        KEY_F2, # Jump to the second bookmark (2, 1).
        # The display doesn't move because the bookmark is already in the
        # optimal position.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 one                              ",
            "     2 two                              ",
            "     3 three                            ",
            "     4 four                             ",
            "     5 five                             ",
            "     6 six                              ",
            "     7 seven                            ",
            "     8 eight                            ",
            "     9 nine                             ",
            "    10 ten                              ",
            "    11 eleven                           ",
            "                        2, 1 |   4%,  0%",
            "                                        "]),
        KEY_F2, # Jump to the third bookmark (3, 6).
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 one                              ",
            "     2 two                              ",
            "     3 three                            ",
            "     4 four                             ",
            "     5 five                             ",
            "     6 six                              ",
            "     7 seven                            ",
            "     8 eight                            ",
            "     9 nine                             ",
            "    10 ten                              ",
            "    11 eleven                           ",
            "                        3, 6 |   8%,100%",
            "                                        "]),
        KEY_F2, # Jump to the third bookmark (9, 6).
        # This moves the bookmark to the optimal scroll position.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     7 seven                            ",
            "     8 eight                            ",
            "     9 nine                             ",
            "    10 ten                              ",
            "    11 eleven                           ",
            "    12 twelve                           ",
            "    13 thirteen                         ",
            "    14 fourteen                         ",
            "    15 fifteen                          ",
            "    16 sixteen                          ",
            "    17 seventeen                        ",
            "                        9, 1 |  34%,  0%",
            "                                        "]),
        KEY_F2, # Jump to the fourth bookmark (23, 13).
        # This moves the bookmark to the optimal scroll position.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "    21 twenty-one                       ",
            "    22 twenty-two                       ",
            "    23 twenty-three                     ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                       23,13 |  95%,100%",
            "                                        "]),
        KEY_F2, # Jump to the first bookmark (1, 4).
        # This moves the bookmark to the optimal scroll position.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 one                              ",
            "     2 two                              ",
            "     3 three                            ",
            "     4 four                             ",
            "     5 five                             ",
            "     6 six                              ",
            "     7 seven                            ",
            "     8 eight                            ",
            "     9 nine                             ",
            "    10 ten                              ",
            "    11 eleven                           ",
            "                        1, 4 |   0%,100%",
            "                                        "]),
        KEY_SHIFT_F2, # Go back to the fourth bookmark (23, 13).
        # This moves the bookmark to the optimal scroll position.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "    21 twenty-one                       ",
            "    22 twenty-two                       ",
            "    23 twenty-three                     ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                                        ",
            "                       23,13 |  95%,100%",
            "                                        "]),
        KEY_SHIFT_F2, # Go back to the third bookmark (8, 6).
        # This moves the bookmark to the optimal scroll position.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     7 seven                            ",
            "     8 eight                            ",
            "     9 nine                             ",
            "    10 ten                              ",
            "    11 eleven                           ",
            "    12 twelve                           ",
            "    13 thirteen                         ",
            "    14 fourteen                         ",
            "    15 fifteen                          ",
            "    16 sixteen                          ",
            "    17 seventeen                        ",
            "                        9, 1 |  34%,  0%",
            "                                        "]),
        KEY_SHIFT_F2, # Go back to the second bookmark (2, 1).
        # This moves the bookmark to the optimal scroll position.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 one                              ",
            "     2 two                              ",
            "     3 three                            ",
            "     4 four                             ",
            "     5 five                             ",
            "     6 six                              ",
            "     7 seven                            ",
            "     8 eight                            ",
            "     9 nine                             ",
            "    10 ten                              ",
            "    11 eleven                           ",
            "                        3, 6 |   8%,100%",
            "                                        "]),
        KEY_SHIFT_F2, # Go back to the first bookmark (1, 4).
        # The display doesn't move because the bookmark is already in the
        # optimal position.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 one                              ",
            "     2 two                              ",
            "     3 three                            ",
            "     4 four                             ",
            "     5 five                             ",
            "     6 six                              ",
            "     7 seven                            ",
            "     8 eight                            ",
            "     9 nine                             ",
            "    10 ten                              ",
            "    11 eleven                           ",
            "                        2, 1 |   4%,  0%",
            "                                        "]),
        CTRL_Q, 'n',
      ])
