import app.prefs
import app.text_buffer
import unittest
from mock import patch

class BookmarkTestCases(unittest.TestCase):
  def setUp(self):
    self.textBuffer = app.text_buffer.TextBuffer()

  def tearDown(self):
    pass

  def test_get_next_bookmark_color(self):
    # Test for 8-colored mode
    patch.dict(app.prefs.startup, {'numColors': 8}, clear=True)
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

    # Test for 256-colored mode
    patch.dict(app.prefs.startup, {'numColors': 256}, clear=True)
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