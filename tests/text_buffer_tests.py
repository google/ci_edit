
import app.text_buffer
import unittest

class TextBufferTestCases(unittest.TestCase):
  def setUp(self):
    self.textBuffer = app.text_buffer.BackingTextBuffer(None)

  def tearDown(self):
    self.textBuffer = None

  def test_default_values(self):
    textBuffer = self.textBuffer
    self.assertEqual(textBuffer.cursorRow, 0)
    self.assertEqual(textBuffer.cursorCol, 0)
    self.assertEqual(textBuffer.markerRow, 0)
    self.assertEqual(textBuffer.markerCol, 0)

if __name__ == '__main__':
  unittest.main()
