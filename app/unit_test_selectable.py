import app.selectable
import unittest

class SelectableTestCases(unittest.TestCase):
  def setUp(self):
    self.selectable = app.selectable.Selectable()

  def tearDown(self):
    self.selectable = None

  def test_default_values(self):
    selectable = self.selectable
    self.assertEqual(selectable.selection(), (0, 0, 0, 0))

  def test_selection_all(self):
    selectable = self.selectable
    selectable.lines = ['one', '', 'five']
    selectable.selectionMode = app.selectable.kSelectionAll
    self.assertEqual(selectable.extendSelection(), (2, 4, 4, 0, 0, 0))

  def test_selection_word(self):
    selectable = self.selectable
    selectable.lines = ['one two', '', 'five']
    mode = app.selectable.kSelectionWord
    selectable.selectionMode = mode
    self.assertEqual(selectable.extendSelection(), (0, 7, 7, 0, 0, mode))
    selectable.cursorRow = 2
    selectable.extendSelection()
    self.assertEqual(selectable.extendSelection(), (2, 4, 4, 2, 0, mode))

if __name__ == '__main__':
  unittest.main()
