
import app.text_buffer
import unittest

class SelectableTestCases(unittest.TestCase):
  def setUp(self):
    self.selectable = app.text_buffer.Selectable()

  def tearDown(self):
    self.selectable = None

  def test_default_values(self):
    selectable = self.selectable
    self.assertEqual(selectable.cursorRow, 0)
    self.assertEqual(selectable.cursorCol, 0)
    self.assertEqual(selectable.markerRow, 0)
    self.assertEqual(selectable.markerCol, 0)

if __name__ == '__main__':
  unittest.main()
