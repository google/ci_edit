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

import curses
import re
import sys

import app.actions
import app.curses_util
import app.regex
import app.log
import app.parser
import app.selectable


class TextBuffer(app.actions.Actions):
    """The TextBuffer adds the drawing/rendering to the BackingTextBuffer."""

    def __init__(self, program):
        app.actions.Actions.__init__(self, program)
        self.lineLimitIndicator = 0
        self.highlightRe = None
        self.highlightCursorLine = False
        self.highlightTrailingWhitespace = True

    def checkScrollToCursor(self, window):
        """Move the selected view rectangle so that the cursor is visible."""
        maxRow, maxCol = window.rows, window.cols
        #     self.penRow >= self.view.scrollRow + maxRow 1 0
        rows = 0
        if self.view.scrollRow > self.penRow:
            rows = self.penRow - self.view.scrollRow
            app.log.error('AAA self.view.scrollRow > self.penRow',
                          self.view.scrollRow, self.penRow, self)
        elif self.penRow >= self.view.scrollRow + maxRow:
            rows = self.penRow - (self.view.scrollRow + maxRow - 1)
            app.log.error(
                'BBB self.penRow >= self.view.scrollRow + maxRow cRow',
                self.penRow, 'sRow', self.view.scrollRow, 'maxRow', maxRow,
                self)
        cols = 0
        if self.view.scrollCol > self.penCol:
            cols = self.penCol - self.view.scrollCol
            app.log.error('CCC self.view.scrollCol > self.penCol',
                          self.view.scrollCol, self.penCol, self)
        elif self.penCol >= self.view.scrollCol + maxCol:
            cols = self.penCol - (self.view.scrollCol + maxCol - 1)
            app.log.error('DDD self.penCol >= self.scrollCol + maxCol',
                          self.penCol, self.view.scrollCol, maxCol, self)
        assert not rows
        assert not cols
        self.updateScrollPosition(rows, cols)

    def draw(self, window):
        if self.view.rows <= 0 or self.view.cols <= 0:
            return
        if not self.view.program.prefs.editor['useBgThread']:
            if self.shouldReparse:
                self.parseGrammars()
                self.shouldReparse = False
        if self.view.hasCaptiveCursor:
            self.checkScrollToCursor(window)
        rows, cols = window.rows, window.cols
        colorPref = self.view.colorPref
        colorDelta = 32 * 4
        #colorDelta = 4
        if 0:
            for i in range(rows):
                window.addStr(i, 0, '?' * cols, colorPref(120))
        if 0:
            # Draw window with no concern for sub-rectangles.
            self.drawTextArea(window, 0, 0, rows, cols, 0)
        elif 1:
            splitRow = rows
            splitCol = max(0, self.lineLimitIndicator - self.view.scrollCol)
            if self.lineLimitIndicator <= 0 or splitCol >= cols:
                # Draw only left side.
                self.drawTextArea(window, 0, 0, splitRow, cols, 0)
            elif 0 < splitCol < cols:
                # Draw both sides.
                self.drawTextArea(window, 0, 0, splitRow, splitCol, 0)
                self.drawTextArea(window, 0, splitCol, splitRow,
                                  cols - splitCol, colorDelta)
            else:
                # Draw only right side.
                assert splitCol <= 0
                self.drawTextArea(window, 0, splitCol, splitRow,
                                  cols - splitCol, colorDelta)
        else:
            # Draw debug checker board.
            splitRow = rows // 2
            splitCol = 17
            self.drawTextArea(window, 0, 0, splitRow, splitCol, 0)
            self.drawTextArea(window, 0, splitCol, splitRow, cols - splitCol,
                              colorDelta)
            self.drawTextArea(window, splitRow, 0, rows - splitRow, splitCol,
                              colorDelta)
            self.drawTextArea(window, splitRow, splitCol, rows - splitRow,
                              cols - splitCol, 0)
        # Blank screen past the end of the buffer.
        color = colorPref('outside_document')
        endOfText = min(
            max(self.parser.rowCount() - self.view.scrollRow, 0), rows)
        for i in range(endOfText, rows):
            window.addStr(i, 0, ' ' * cols, color)

    def drawTextArea(self, window, top, left, rows, cols, colorDelta):
        startRow = self.view.scrollRow + top
        endRow = startRow + rows
        startCol = self.view.scrollCol + left
        endCol = startCol + cols
        appPrefs = self.view.program.prefs
        defaultColor = appPrefs.color['default']
        spellChecking = appPrefs.editor.get('spellChecking', True)
        colorPref = self.view.colorPref
        spelling = self.program.dictionary
        spelling.setUpWordsForPath(self.fullPath)
        if self.parser:
            # Highlight grammar.
            rowLimit = min(max(self.parser.rowCount() - startRow, 0), rows)
            for i in range(rowLimit):
                line, renderedWidth = self.parser.rowTextAndWidth(startRow + i)
                k = startCol
                if k == 0:
                    # When rendering from column 0 the grammar index is always
                    # zero.
                    grammarIndex = 0
                else:
                    # When starting mid-line, find starting grammar index.
                    grammarIndex = self.parser.grammarIndexFromRowCol(
                        startRow + i, k)
                while k < endCol:
                    (node, preceding, remaining, eol) = self.parser.grammarAtIndex(
                        startRow + i, k, grammarIndex)
                    grammarIndex += 1
                    if remaining == 0 and not eol:
                        continue
                    remaining = min(renderedWidth - k, remaining)
                    length = min(endCol - k, remaining)
                    color = colorPref(
                        node.grammar.get(u'colorIndex', defaultColor),
                        colorDelta)
                    if eol or length <= 0:
                        window.addStr(top + i, left + k - startCol,
                                      u' ' * (endCol - k), color)
                        break
                    window.addStr(
                        top + i, left + k - startCol,
                        app.curses_util.renderedSubStr(line, k, k + length),
                        color)
                    subStart = k - preceding
                    subEnd = k + remaining
                    subLine = line[subStart:subEnd]
                    if spellChecking and node.grammar.get(u'spelling', True):
                        # Highlight spelling errors
                        grammarName = node.grammar.get(u'name', 'unknown')
                        misspellingColor = colorPref(
                            u'misspelling', colorDelta)
                        for found in re.finditer(app.regex.kReSubwords,
                                                 subLine):
                            reg = found.regs[0]  # Mispelllled word
                            offsetStart = subStart + reg[0]
                            offsetEnd = subStart + reg[1]
                            if startCol < offsetEnd and offsetStart < endCol:
                                word = line[offsetStart:offsetEnd]
                                if not spelling.isCorrect(word, grammarName):
                                    if startCol > offsetStart:
                                        offsetStart += startCol - offsetStart
                                    wordFragment = line[offsetStart:min(
                                        endCol, offsetEnd)]
                                    window.addStr(
                                        top + i, left + offsetStart - startCol,
                                        wordFragment, misspellingColor)
                    k += length
        else:
            # For testing, draw without parser.
            rowLimit = min(max(self.parser.rowCount() - startRow, 0), rows)
            for i in range(rowLimit):
                line = self.parser.rowText(startRow + i)[startCol:endCol]
                window.addStr(top + i, left, line + ' ' * (cols - len(line)),
                              colorPref(u'default', colorDelta))
        self.drawOverlays(window, top, left, rows, cols, colorDelta)
        if 0:  # Experiment: draw our own cursor.
            if (startRow <= self.penRow < endRow and
                    startCol <= self.penCol < endCol):
                window.addStr(self.penRow - startRow, self.penCol - startCol,
                              u'X', 200)

    def drawOverlays(self, window, top, left, maxRow, maxCol, colorDelta):
        startRow = self.view.scrollRow + top
        endRow = self.view.scrollRow + top + maxRow
        startCol = self.view.scrollCol + left
        endCol = self.view.scrollCol + left + maxCol
        rowLimit = min(max(self.parser.rowCount() - startRow, 0), maxRow)
        colorPref = self.view.colorPref
        if 1:
            # Highlight brackets.
            # Highlight numbers.
            # Highlight space ending lines.
            colors = (colorPref(u'bracket', colorDelta),
                      colorPref(u'number', colorDelta),
                      colorPref(u'trailing_space', colorDelta))
            for i in range(rowLimit):
                line = self.parser.rowText(startRow + i)
                highlightTrailingWhitespace = (
                    self.highlightTrailingWhitespace and
                    not (startRow + i == self.penRow and
                         self.penCol == len(line)))
                for s, column, _, index in app.curses_util.renderedFindIter(
                        line, startCol, endCol, (u'[]{}()',), True,
                        highlightTrailingWhitespace):
                    window.addStr(top + i, column - self.view.scrollCol, s,
                                  colors[index])
        if 1:
            # Match brackets.
            if (self.parser.rowCount() > self.penRow and
                    len(self.parser.rowText(self.penRow)) > self.penCol):
                ch = app.curses_util.charAtColumn(
                    self.penCol, self.parser.rowText(self.penRow))
                matchingBracketRowCol = self.getMatchingBracketRowCol()
                if matchingBracketRowCol is not None:
                    matchingBracketRow = matchingBracketRowCol[0]
                    matchingBracketCol = matchingBracketRowCol[1]
                    window.addStr(
                        top + self.penRow - startRow,
                        self.penCol - self.view.scrollCol,
                        ch,
                        colorPref(u'matching_bracket', colorDelta))
                    characterFinder = {
                        u'(': u')',
                        u'[': u']',
                        u'{': u'}',
                        u')': u'(',
                        u']': u'[',
                        u'}': u'{',
                    }
                    oppCharacter = characterFinder[ch]
                    window.addStr(
                        top + matchingBracketRow - startRow,
                        matchingBracketCol - self.view.scrollCol, oppCharacter,
                        colorPref(u'matching_bracket', colorDelta))
        if self.highlightCursorLine:
            # Highlight the whole line at the cursor location.
            if self.view.hasFocus and startRow <= self.penRow < startRow + rowLimit:
                line = self.parser.rowText(self.penRow)[startCol:endCol]
                window.addStr(top + self.penRow - startRow, left, line,
                              colorPref(u'current_line', colorDelta))
        if self.findRe is not None:
            # Highlight find.
            for i in range(rowLimit):
                line = self.parser.rowText(startRow + i)[startCol:endCol]
                for k in self.findRe.finditer(line):
                    reg = k.regs[0]
                    #for ref in k.regs[1:]:
                    window.addStr(top + i, left + reg[0], line[reg[0]:reg[1]],
                                  colorPref('found_find', colorDelta))
        if rowLimit and self.selectionMode != app.selectable.kSelectionNone:
            # Highlight selected text.
            colorSelected = colorPref('selected')
            upperRow, upperCol, lowerRow, lowerCol = self.startAndEnd()
            if 1:
                selStartCol = max(upperCol, startCol)
                selEndCol = min(lowerCol, endCol)
                start = max(0, min(upperRow - startRow, maxRow))
                end = max(0, min(lowerRow - startRow, maxRow))
                if self.selectionMode == app.selectable.kSelectionBlock:
                    if not (lowerRow < startRow or upperRow >= endRow or
                            lowerCol < startCol or upperCol >= endCol):
                        # There is an overlap.
                        for i in range(start, end + 1):
                            line = self.parser.rowText(startRow +
                                                       i)[selStartCol:selEndCol]
                            window.addStr(top + i, selStartCol, line,
                                          colorSelected)
                elif (self.selectionMode == app.selectable.kSelectionAll or
                      self.selectionMode == app.selectable.kSelectionCharacter
                      or self.selectionMode == app.selectable.kSelectionLine or
                      self.selectionMode == app.selectable.kSelectionWord):
                    if not (lowerRow < startRow or upperRow >= endRow):
                        # There is an overlap.
                        # Go one row past the selection or to the last line.
                        for i in range(
                                start,
                                min(end + 1,
                                    self.parser.rowCount() - startRow)):
                            line = self.parser.rowText(startRow + i)
                            # TODO(dschuyler): This is essentially
                            # left + (upperCol or (scrollCol + left)) -
                            #    scrollCol - left
                            # which seems like it could be simplified.
                            paneCol = left + selStartCol - startCol
                            if len(line) == len(
                                    self.parser.rowText(startRow + i)):
                                line += " "  # Maybe do: "\\n".
                            if (i == lowerRow - startRow and
                                    i == upperRow - startRow):
                                # Selection entirely on one line.
                                window.addStr(top + i, paneCol,
                                              line[selStartCol:selEndCol],
                                              colorSelected)
                            elif i == lowerRow - startRow:
                                # End of multi-line selection.
                                window.addStr(top + i, left,
                                              line[startCol:selEndCol],
                                              colorSelected)
                            elif i == upperRow - startRow:
                                # Start of multi-line selection.
                                window.addStr(top + i, paneCol,
                                              line[selStartCol:endCol],
                                              colorSelected)
                            else:
                                # Middle of multi-line selection.
                                window.addStr(top + i, left,
                                              line[startCol:endCol],
                                              colorSelected)
