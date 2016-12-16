
import app.log
import app.selectable
import unittest

class SelectableTestCases(unittest.TestCase):
  def setUp(self):
    self.selectable = app.selectable.Selectable()
    app.log.shouldWritePrintLog = True
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

  def test_selection_line(self):
    selectable = self.selectable
    selectable.lines = ['one two', '', 'five']
    selectable.cursorRow = 1
    selectable.selectionMode = app.selectable.kSelectionLine
    app.log.debug('selectable', selectable.debug())
    app.log.debug('selectable.extendSelection', selectable.extendSelection())
    self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0, 0))
    selectable.cursorRow = 3
    selectable.cursorCol = 3
    selectable.markerRow = 1
    selectable.markerCol = 4
    self.assertEqual(selectable.extendSelection(), (0, -3, 0, 0, -4, 0))

  def test_selection_word(self):
    selectable = self.selectable
    selectable.lines = ['one two', 'Several test words.', 'five']
    selectable.selectionMode = app.selectable.kSelectionWord
    selectable.cursorRow = 1
    selectable.cursorCol = 2
    self.assertEqual(selectable.extendSelection(), (0, 5, 7, 0, 0, 0))
    selectable.cursorRow = 1
    selectable.cursorCol = 9
    selectable.markerCol = 2
    self.assertEqual(selectable.extendSelection(), (0, 3, 12, 0, -2, 0))

if __name__ == '__main__':
  unittest.main()
