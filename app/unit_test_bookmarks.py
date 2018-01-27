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
import os
import sys
import unittest

from app.curses_util import *
import app.fake_curses_testing
import app.prefs
import app.text_buffer
import app.window

kTestFile = '#test_file_with_unlikely_file_name~'

class EmptyObject:
  pass

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
    self.fakeHost = EmptyObject()
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

  def runWithTestFile(self, fakeInputs):
    sys.argv = [kTestFile]
    self.assertFalse(os.path.isfile(kTestFile))
    self.runWithFakeInputs(fakeInputs)

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
      raise Exception(exceptionMessage)
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
    self.textBuffer.bookmarks = [((0, 0),), ((10, 10),), ((20, 20),),
                                 ((30, 30),), ((40, 40),),]
    visibleBookmarks = self.lineNumbers.getVisibleBookmarks(
        self.fakeHost.scrollRow, self.lineNumbers.rows)
    expectedBookmarks = {((0, 0),), ((10, 10),), ((20, 20),)}

    # Check that visibleBookmarks contains all the correct bookmarks
    self.assertEqual(set(visibleBookmarks), expectedBookmarks)
    # Check that the number of bookmarks is the same, as set removes duplicates.
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

  def test_bookmarks_render(self):
    self.runWithFakeInputs([
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
            "New buffer         |    1, 1 | 100%,100%",
            "                                        "]),
        'f', 'i', 'r', 's', 't', ' ', 'l', 'i', 'n', 'e',
        CTRL_E, 'b', 'm', CTRL_J, CTRL_J, # Create bookmark and go to next line.
        's', 'e', 'c', 'o', 'n', 'd', ' ', 'l', 'i', 'n', 'e', CTRL_J,
        't', 'h', 'i', 'r', 'd', ' ', 'l', 'i', 'n', 'e',
        CTRL_E, 'b', 'm', CTRL_J, CTRL_J, # Create bookmark and go to next line.
        'f', 'o', 'u', 'r', 't', 'h', ' ', 'l', 'i', 'n', 'e', CTRL_J,
        'f', 'i', 'f', 't', 'h', ' ', 'l', 'i', 'n', 'e', CTRL_J,
        's', 'i', 'x', 't', 'h', ' ', 'l', 'i', 'n', 'e', CTRL_J,
        's', 'e', 'v', 'e', 'n', 't', 'h', ' ', 'l', 'i', 'n', 'e', CTRL_J,
        'e', 'i', 'g', 'h', 't', 'h', ' ', 'l', 'i', 'n', 'e', CTRL_J,
        CTRL_E, 'b', 'm', CTRL_J, # Create a new bookmark.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 first line                       ",
            "     2 second line                      ",
            "     3 third line                       ",
            "     4 fourth line                      ",
            "     5 fifth line                       ",
            "     6 sixth line                       ",
            "     7 seventh line                     ",
            "     8 eighth line                      ",
            "     9                                  ",
            "                                        ",
            "                                        ",
            "Added bookmark     |    9, 1 | 100%,100%",
            "                                        "]),
        # Bookmarks should now be at the following positions (row, col):
        #   (1, 11), (3, 11), (8, 12).
        KEY_F2, # This should cause the cursor to jump to the first bookmark.
        self.displayCheck(0, 0, [
            " ci     *                               ",
            "                                        ",
            "     1 first line                       ",
            "     2 second line                      ",
            "     3 third line                       ",
            "     4 fourth line                      ",
            "     5 fifth line                       ",
            "     6 sixth line                       ",
            "     7 seventh line                     ",
            "     8 eighth line                      ",
            "     9                                  ",
            "                                        ",
            "                                        ",
            "                        1, 11 | 100%,100%",
            "                                        "]),
        CTRL_Q, 'n'
      ])
