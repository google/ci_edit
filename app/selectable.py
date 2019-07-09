# Copyright 2016 Google Inc.
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

import re

import app.config
import app.line_buffer
import app.log
import app.regex

# No selection.
kSelectionNone = 0
# Entire document selected.
kSelectionAll = 1
# A rectangular block selection.
kSelectionBlock = 2
# Character by character selection.
kSelectionCharacter = 3
# Select whole lines.
kSelectionLine = 4
# Select whole words.
kSelectionWord = 5
# How many selection modes are there.
kSelectionModeCount = 6

kSelectionModeNames = [
    'None',
    'All',
    'Block',
    'Char',
    'Line',
    'Word',
]


class Selectable(app.line_buffer.LineBuffer):

    def __init__(self, program):
        app.line_buffer.LineBuffer.__init__(self, program)
        # When a text document is not line wrapped then each row will represent
        # one line in the document, thow rows are zero based and lines are one
        # based. With line wrapping enabled there may be more rows than lines
        # since a line may wrap into multiple rows.
        self.penRow = 0
        # When a text document contains only ascii characters then each char
        # (character) will represent one column in the text line (col is zero
        # based and the column displayed in the UI is one based). When double
        # wide character are present then a line of text will have more columns
        # than characters.
        # (penChar is not currently used).
        self.penChar = 0
        # When a text document contains only ascii characters then each column
        # will represent one column in the text line (col is zero based and
        # column displayed in the UI is one based).
        self.penCol = 0
        self.markerRow = 0
        self.markerCol = 0
        self.selectionMode = kSelectionNone

    def countSelected(self):
        lines = self.getSelectedText()
        chars = len(lines) - 1  # Count carriage returns.
        for line in lines:
            chars += len(line)
        return chars, len(lines)

    def selection(self):
        return (self.penRow, self.penCol, self.markerRow, self.markerCol)

    def selectionModeName(self):
        return kSelectionModeNames[self.selectionMode]

    def getSelectedText(self):
        upperRow, upperCol, lowerRow, lowerCol = self.startAndEnd()
        return self.getText(upperRow, upperCol, lowerRow, lowerCol,
                            self.selectionMode)

    def getText(self,
                upperRow,
                upperCol,
                lowerRow,
                lowerCol,
                selectionMode=kSelectionCharacter):
        if app.config.strict_debug:
            assert isinstance(upperRow, int)
            assert isinstance(upperCol, int)
            assert isinstance(lowerRow, int)
            assert isinstance(lowerCol, int)
            assert isinstance(selectionMode, int)
            assert upperRow <= lowerRow
            assert upperRow != lowerRow or upperCol <= lowerCol
            assert kSelectionNone <= selectionMode < kSelectionModeCount
        lines = []
        if selectionMode == kSelectionBlock:
            if (lowerRow + 1 < len(self.lines)):
                lowerRow += 1
            for i in range(upperRow, lowerRow):
                lines.append(self.lines[i][upperCol:lowerCol])
        elif (selectionMode == kSelectionAll or
              selectionMode == kSelectionCharacter or
              selectionMode == kSelectionLine or
              selectionMode == kSelectionWord):
            if upperRow == lowerRow:
                lines.append(self.lines[upperRow][upperCol:lowerCol])
            else:
                for i in range(upperRow, lowerRow + 1):
                    if i == upperRow:
                        lines.append(self.lines[i][upperCol:])
                    elif i == lowerRow:
                        lines.append(self.lines[i][:lowerCol])
                    else:
                        lines.append(self.lines[i])
        return tuple(lines)

    def doDeleteSelection(self):
        upperRow, upperCol, lowerRow, lowerCol = self.startAndEnd()
        self.doDelete(upperRow, upperCol, lowerRow, lowerCol)

    def doDelete(self, upperRow, upperCol, lowerRow, lowerCol):
        if app.config.strict_debug:
            assert isinstance(upperRow, int)
            assert isinstance(upperCol, int)
            assert isinstance(lowerRow, int)
            assert isinstance(lowerCol, int)
            assert upperRow <= lowerRow
            assert upperRow != lowerRow or upperCol <= lowerCol
        if self.upperChangedRow > upperRow:
            self.upperChangedRow = upperRow
        if self.selectionMode == kSelectionBlock:
            for i in range(upperRow, lowerRow + 1):
                line = self.lines[i]
                self.lines[i] = line[:upperCol] + line[lowerCol:]
        elif (self.selectionMode == kSelectionNone or
              self.selectionMode == kSelectionAll or
              self.selectionMode == kSelectionCharacter or
              self.selectionMode == kSelectionLine or
              self.selectionMode == kSelectionWord):
            upperLine = self.lines[upperRow]
            lowerLine = self.lines[lowerRow]
            self.lines[upperRow] = upperLine[:upperCol] + lowerLine[lowerCol:]
            if upperRow != lowerRow:
                del self.lines[upperRow + 1:lowerRow + 1]

    def insertLines(self, lines):
        if app.config.strict_debug:
            assert isinstance(lines, tuple)
        self.insertLinesAt(self.penRow, self.penCol, lines, self.selectionMode)

    def insertLinesAt(self, row, col, lines, selectionMode):
        if app.config.strict_debug:
            assert isinstance(row, int)
            assert isinstance(col, int)
            assert isinstance(lines, tuple)
            assert isinstance(selectionMode, int)
        if len(lines) == 0:
            return
        lines = list(lines)
        if self.upperChangedRow > row:
            self.upperChangedRow = row
        if selectionMode == kSelectionBlock:
            for i, line in enumerate(lines):
                self.lines[row + i] = (self.lines[row + i][:col] + line +
                                       self.lines[row + i][col:])
                self.lines.insert(row, line)
        elif (selectionMode == kSelectionNone or
              selectionMode == kSelectionAll or
              selectionMode == kSelectionCharacter or
              selectionMode == kSelectionLine or
              selectionMode == kSelectionWord):
            lines.reverse()
            firstLine = self.lines[row]
            if len(lines) == 1:
                self.lines[row] = (firstLine[:col] + lines[0] + firstLine[col:])
            else:
                self.lines[row] = (firstLine[:col] + lines[-1])
                currentRow = row + 1
                self.lines.insert(currentRow, lines[0] + firstLine[col:])
                for line in lines[1:-1]:
                    self.lines.insert(currentRow, line)
        else:
            app.log.info('selection mode not recognized', selectionMode)

    def __extendWords(self, upperRow, upperCol, lowerRow, lowerCol):
        """Extends and existing selection to the nearest word boundaries. The
        pen and marker will be extended away from each other. The extension may
        occur in one, both, or neither direction."""
        line = self.parser.rowText(upperRow)
        for segment in re.finditer(app.regex.kReWordBoundary, line):
            if segment.start() <= upperCol < segment.end():
                upperCol = segment.start()
                break
        line = self.parser.rowText(lowerRow)
        for segment in re.finditer(app.regex.kReWordBoundary, line):
            if segment.start() < lowerCol < segment.end():
                lowerCol = segment.end()
                break
        return upperCol, lowerCol

    def extendSelection(self):
        """Get a tuple of:
        (penRow, penCol, markerRow, markerCol, selectionMode)"""
        if self.selectionMode == kSelectionNone:
            return (0, 0, -self.markerRow, -self.markerCol, 0)
        elif self.selectionMode == kSelectionAll:
            lowerRow = self.parser.rowCount() - 1
            lowerCol = self.parser.rowWidth(-1)
            return (lowerRow - self.penRow,
                    lowerCol - self.penCol, -self.markerRow,
                    -self.markerCol, 0)
        elif self.selectionMode == kSelectionLine:
            return (0, -self.penCol, 0, -self.markerCol, 0)
        elif self.selectionMode == kSelectionWord:
            if self.penRow > self.markerRow or (self.penRow == self.markerRow
                                                and
                                                self.penCol > self.markerCol):
                upperCol, lowerCol = self.__extendWords(
                    self.markerRow, self.markerCol, self.penRow, self.penCol)
                return (0, lowerCol - self.penCol, 0, upperCol - self.markerCol,
                        0)
            else:
                upperCol, lowerCol = self.__extendWords(
                    self.penRow, self.penCol, self.markerRow, self.markerCol)
                return (0, upperCol - self.penCol, 0, lowerCol - self.markerCol,
                        0)
        return (0, 0, 0, 0, 0)

    def startAndEnd(self):
        """Get the marker and pen pair as the earlier of the two then the later
        of the two. The result accounts for the current selection mode."""
        upperRow = 0
        upperCol = 0
        lowerRow = 0
        lowerCol = 0
        if self.selectionMode == kSelectionNone:
            upperRow = self.penRow
            upperCol = self.penCol
            lowerRow = self.penRow
            lowerCol = self.penCol
        elif self.selectionMode == kSelectionAll:
            upperRow = 0
            upperCol = 0
            lowerRow = self.parser.rowCount() - 1
            lowerCol = self.parser.rowWidth(-1)
        elif self.selectionMode == kSelectionBlock:
            upperRow = min(self.markerRow, self.penRow)
            upperCol = min(self.markerCol, self.penCol)
            lowerRow = max(self.markerRow, self.penRow)
            lowerCol = max(self.markerCol, self.penCol)
        elif (self.selectionMode == kSelectionCharacter or
              self.selectionMode == kSelectionLine or
              self.selectionMode == kSelectionWord):
            upperRow = self.markerRow
            upperCol = self.markerCol
            lowerRow = self.penRow
            lowerCol = self.penCol
            if upperRow == lowerRow and upperCol > lowerCol:
                upperCol, lowerCol = lowerCol, upperCol
            elif upperRow > lowerRow:
                upperRow, lowerRow = lowerRow, upperRow
                upperCol, lowerCol = lowerCol, upperCol
        #app.log.detail('start and end', upperRow, upperCol, lowerRow, lowerCol)
        return (upperRow, upperCol, lowerRow, lowerCol)
