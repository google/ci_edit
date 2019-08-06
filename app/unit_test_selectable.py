# Copyright 2017 Google Inc.
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

import unittest

import app.log
import app.ci_program
import app.selectable


class SelectableTestCases(unittest.TestCase):

    def setUp(self):
        self.selectable = app.selectable.Selectable(app.ci_program.CiProgram())
        app.log.shouldWritePrintLog = True

    def tearDown(self):
        self.selectable = None

    def test_default_values(self):
        selectable = self.selectable
        self.assertEqual(selectable.selection(), (0, 0, 0, 0))

    def test_selection_none(self):
        selectable = self.selectable
        selectable.lines = [u"oneTwo", u"", u"five"]
        selectable.parseDocument()
        selectable.selectionMode = app.selectable.kSelectionNone
        self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0))
        selectable.penCol = 3
        self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0))

    def test_selection_all(self):
        selectable = self.selectable
        selectable.lines = [u"oneTwo", u"", u"five"]
        selectable.parseDocument()
        selectable.selectionMode = app.selectable.kSelectionAll
        self.assertEqual(selectable.extendSelection(), (2, 4, 0, 0, 0))
        selectable.penCol = 3
        self.assertEqual(selectable.extendSelection(), (2, 1, 0, 0, 0))

    def test_selection_block(self):
        selectable = self.selectable
        selectable.lines = [u"oneTwo", u"", u"five"]
        selectable.parseDocument()
        selectable.selectionMode = app.selectable.kSelectionBlock
        self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0))
        selectable.penCol = 3
        self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0))

    def test_selection_character(self):
        selectable = self.selectable
        selectable.lines = [u"oneTwo", u"", u"five"]
        selectable.parseDocument()
        selectable.selectionMode = app.selectable.kSelectionCharacter
        self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0))
        selectable.penCol = 3
        self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0))

    def test_selection_line(self):
        selectable = self.selectable
        selectable.lines = [u"one two", u"", u"five"]
        selectable.parseDocument()
        selectable.penRow = 1
        selectable.selectionMode = app.selectable.kSelectionLine
        app.log.debug(u"selectable.extendSelection",
                      selectable.extendSelection())
        self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0))
        selectable.penRow = 3
        selectable.penCol = 3
        selectable.markerRow = 1
        selectable.markerCol = 4
        self.assertEqual(selectable.extendSelection(), (0, -3, 0, -4, 0))

    def test_selection_word(self):
        selectable = self.selectable
        selectable.lines = [u"one two", u"Several test words.", u"five"]
        selectable.parseDocument()
        selectable.selectionMode = app.selectable.kSelectionWord
        selectable.penRow = 1
        selectable.penCol = 2
        self.assertEqual(selectable.extendSelection(), (0, 5, 0, 0, 0))
        selectable.penRow = 1
        selectable.penCol = 9
        selectable.markerCol = 2
        self.assertEqual(selectable.extendSelection(), (0, 3, 0, -2, 0))

    # Deletion tests.

    def test_deletion_none(self):
        selectable = self.selectable
        selectable.lines = [u"one two", u"Several test words.", u"five"]
        selectable.parseDocument()
        selectable.selectionMode = app.selectable.kSelectionNone
        selectable.penCol = 1
        selectable.doDeleteSelection()
        self.assertEqual(selectable.lines,
                         [u"one two", u"Several test words.", u"five"])

    def test_deletion_all(self):
        selectable = self.selectable
        selectable.lines = [u"oneTwo", u"", u"five"]
        selectable.parseDocument()
        selectable.selectionMode = app.selectable.kSelectionAll
        self.assertEqual(selectable.extendSelection(), (2, 4, 0, 0, 0))
        selectable.penCol = 3
        self.assertEqual(selectable.extendSelection(), (2, 1, 0, 0, 0))

    def test_deletion_block(self):
        selectable = self.selectable
        selectable.lines = [u"oneTwo", u"", u"five"]
        selectable.parseDocument()
        selectable.selectionMode = app.selectable.kSelectionBlock
        self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0))
        selectable.penCol = 3
        self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0))

    def test_deletion_character(self):
        selectable = self.selectable
        selectable.lines = [u"one two", u"Several test words.", u"five"]
        selectable.parseDocument()
        selectable.selectionMode = app.selectable.kSelectionCharacter
        selectable.penCol = 1
        selectable.doDeleteSelection()
        self.assertEqual(selectable.lines,
                         [u"ne two", u"Several test words.", u"five"])
        selectable.markerCol = 3
        selectable.doDeleteSelection()
        self.assertEqual(selectable.lines,
                         [u"ntwo", u"Several test words.", u"five"])
        selectable.penRow = 1
        selectable.penCol = 1
        selectable.doDeleteSelection()
        self.assertEqual(selectable.lines, [u"ntweveral test words.", u"five"])

    def test_deletion_line(self):
        selectable = self.selectable
        selectable.lines = [u"one two", u"", u"five"]
        selectable.parseDocument()
        selectable.penRow = 1
        selectable.selectionMode = app.selectable.kSelectionLine
        app.log.debug(u"selectable.extendSelection",
                      selectable.extendSelection())
        self.assertEqual(selectable.extendSelection(), (0, 0, 0, 0, 0))
        selectable.penRow = 3
        selectable.penCol = 3
        selectable.markerRow = 1
        selectable.markerCol = 4
        self.assertEqual(selectable.extendSelection(), (0, -3, 0, -4, 0))

    def test_deletion_word(self):
        selectable = self.selectable
        selectable.lines = [u"one two", u"Several test words.", u"five"]
        selectable.parseDocument()
        selectable.selectionMode = app.selectable.kSelectionWord
        selectable.penRow = 1
        selectable.penCol = 2
        self.assertEqual(selectable.extendSelection(), (0, 5, 0, 0, 0))
        selectable.penRow = 1
        selectable.penCol = 9
        selectable.markerCol = 2
        self.assertEqual(selectable.extendSelection(), (0, 3, 0, -2, 0))

if __name__ == "__main__":
    unittest.main()
