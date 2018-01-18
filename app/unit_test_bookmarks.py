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

import mock
import unittest

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

    self.textBuffer.bookmarks = [((0, 0),), ((10, 10),), ((20, 20),),
                                 ((30, 30),), ((40, 40),),]
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, self.lineNumbers.rows)
    expectedBookmarks = {((0, 0),), ((10, 10),), ((20, 20),)}
    self.assertEqual(set(visibleBookmarks), expectedBookmarks)
    self.assertEqual(len(visibleBookmarks), len(expectedBookmarks))

    self.fakeHost.scrollRow = 20
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, 20 + self.lineNumbers.rows)
    expectedBookmarks = {((20, 20),), ((30, 30),), ((40, 40),)}
    self.assertEqual(set(visibleBookmarks), expectedBookmarks)
    self.assertEqual(len(visibleBookmarks), len(expectedBookmarks))

    self.fakeHost.scrollRow = 21
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, self.fakeHost.scrollRow + self.lineNumbers.rows)
    expectedBookmarks = {((30, 30),), ((40, 40),)}
    self.assertEqual(set(visibleBookmarks), expectedBookmarks)
    self.assertEqual(len(visibleBookmarks), len(expectedBookmarks))

    self.fakeHost.scrollRow = 21
    self.lineNumbers.rows = 10
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, self.fakeHost.scrollRow + self.lineNumbers.rows)
    expectedBookmarks = {((30, 30),)}
    self.assertEqual(set(visibleBookmarks), expectedBookmarks)
    self.assertEqual(len(visibleBookmarks), len(expectedBookmarks))

    self.lineNumbers.rows = 9
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, self.fakeHost.scrollRow + self.lineNumbers.rows)
    expectedBookmarks = {}
    self.assertEqual(visibleBookmarks, [])

    self.fakeHost.scrollRow = 10
    self.textBuffer.bookmarks = [((0, 10),), ((11, 30),),
                                 ((30, 45),), ((45, 49),)]
    self.lineNumbers.rows = 15
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, self.fakeHost.scrollRow + self.lineNumbers.rows)
    expectedBookmarks = {((0, 10),), ((11, 30),)}
    self.assertEqual(set(visibleBookmarks), expectedBookmarks)
    self.assertEqual(len(visibleBookmarks), len(expectedBookmarks))
