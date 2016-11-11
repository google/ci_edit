
import app.text_buffer
import unittest

class SelectableTestCases(unittest.TestCase):
  def setUp(self):
    self.selectable = app.text_buffer.Selectable()

  def tearDown(self):
    self.selectable = None

  def test_default_values(self):
    selectable = self.selectable
    self.assertEqual(selectable.selection(), (0, 0, 0, 0))

  def test_selection_all(self):
    selectable = self.selectable
    selectable.lines = ['one', '', 'five']
    selectable.selectionMode = app.text_buffer.kSelectionAll
    self.assertEqual(selectable.extendSelection(), (2, 4, 4, 0, 0, 0))

if __name__ == '__main__':
  unittest.main()
