# Copyright 2017 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

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

  def test_selection_none(self):
    selectable = self.selectable
    selectable.lines = ['onetwo', '', 'five']
    selectable.selectionMode = app.selectable.kSelectionNone
    self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0, 0))
    selectable.cursorCol = 3
    self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0, 0))

  def test_selection_all(self):
    selectable = self.selectable
    selectable.lines = ['onetwo', '', 'five']
    selectable.selectionMode = app.selectable.kSelectionAll
    self.assertEqual(selectable.extendSelection(), (2, 4, 4, 0, 0, 0))
    selectable.cursorCol = 3
    self.assertEqual(selectable.extendSelection(), (2, 1, 4, 0, 0, 0))

  def test_selection_block(self):
    selectable = self.selectable
    selectable.lines = ['onetwo', '', 'five']
    selectable.selectionMode = app.selectable.kSelectionBlock
    self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0, 0))
    selectable.cursorCol = 3
    self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0, 0))

  def test_selection_character(self):
    selectable = self.selectable
    selectable.lines = ['onetwo', '', 'five']
    selectable.selectionMode = app.selectable.kSelectionCharacter
    self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0, 0))
    selectable.cursorCol = 3
    self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0, 0))

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

  # Deletion tests.

  def test_deletion_none(self):
    selectable = self.selectable
    selectable.lines = ['one two', 'Several test words.', 'five']
    selectable.selectionMode = app.selectable.kSelectionNone
    selectable.cursorCol = 1
    selectable.doDeleteSelection()
    self.assertEqual(selectable.lines,
        ['one two', 'Several test words.', 'five'])

  def test_deletion_all(self):
    selectable = self.selectable
    selectable.lines = ['onetwo', '', 'five']
    selectable.selectionMode = app.selectable.kSelectionAll
    self.assertEqual(selectable.extendSelection(), (2, 4, 4, 0, 0, 0))
    selectable.cursorCol = 3
    self.assertEqual(selectable.extendSelection(), (2, 1, 4, 0, 0, 0))

  def test_deletion_block(self):
    selectable = self.selectable
    selectable.lines = ['onetwo', '', 'five']
    selectable.selectionMode = app.selectable.kSelectionBlock
    self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0, 0))
    selectable.cursorCol = 3
    self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0, 0))

  def test_deletion_character(self):
    selectable = self.selectable
    selectable.lines = ['one two', 'Several test words.', 'five']
    selectable.selectionMode = app.selectable.kSelectionCharacter
    selectable.cursorCol = 1
    selectable.doDeleteSelection()
    self.assertEqual(selectable.lines,
        ['ne two', 'Several test words.', 'five'])
    selectable.markerCol = 3
    selectable.doDeleteSelection()
    self.assertEqual(selectable.lines,
        ['ntwo', 'Several test words.', 'five'])
    selectable.cursorRow = 1
    selectable.cursorCol = 1
    selectable.doDeleteSelection()
    self.assertEqual(selectable.lines,
        ['ntweveral test words.', 'five'])

  def test_deletion_line(self):
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

  def test_deletion_word(self):
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
