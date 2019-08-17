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

# For Python 2to3 support.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
try:
    unicode
except NameError:
    unicode = str
    unichr = chr

import bisect
import curses.ascii
import difflib
import binascii
import io
import os
import re
import sys
import time
import traceback
import warnings

import app.bookmark
import app.config
import app.curses_util
import app.history
import app.log
import app.mutator
import app.parser
import app.selectable


class Actions(app.mutator.Mutator):
    """This base class to TextBuffer handles the text manipulation (without
    handling the drawing/rendering of the text)."""

    def __init__(self, program):
        app.mutator.Mutator.__init__(self, program)
        self.view = None
        self.bookmarks = []
        self.fileExtension = None
        self.nextBookmarkColorPos = 0
        self.fileEncoding = None
        self.fileHistory = {}
        self.lastChecksum = None
        self.lastFileSize = 0
        self.fileFilter(u'')

    def getMatchingBracketRowCol(self):
        """Gives the position of the bracket which matches
        the bracket at the current position of the cursor.

        Args:
          None.

        Returns:
          None if matching bracket isn't found.
          Position (int row, int col) of the matching bracket otherwise.
        """
        if self.parser.rowCount() <= self.penRow:
            return None
        text, width = self.parser.rowTextAndWidth(self.penRow)
        if width <= self.penCol:
            return None
        ch = app.curses_util.charAtColumn(self.penCol, text)

        def searchForward(openCh, closeCh):
            count = 1
            textCol = self.penCol + 1
            for row in range(self.penRow, self.parser.rowCount()):
                line = self.parser.rowText(row)
                if row == self.penRow:
                    line = app.curses_util.renderedSubStr(line, textCol)
                else:
                    textCol = 0
                for match in re.finditer(
                        u"(\\" + openCh + u")|(\\" + closeCh + u")", line):
                    if match.group() == openCh:
                        count += 1
                    else:
                        count -= 1
                    if count == 0:
                        textCol += app.curses_util.columnWidth(
                            line[:match.start()])
                        return row, textCol

        def searchBack(closeCh, openCh):
            count = -1
            for row in range(self.penRow, -1, -1):
                line = self.parser.rowText(row)
                if row == self.penRow:
                    line = app.curses_util.renderedSubStr(line, 0, self.penCol)
                found = [
                    i for i in re.finditer(
                        u"(\\" + openCh + u")|(\\" + closeCh + u")", line)
                ]
                for match in reversed(found):
                    if match.group() == openCh:
                        count += 1
                    else:
                        count -= 1
                    if count == 0:
                        textCol = app.curses_util.columnWidth(
                            line[:match.start()])
                        return row, textCol

        matcher = {
            u'(': (u')', searchForward),
            u'[': (u']', searchForward),
            u'{': (u'}', searchForward),
            u')': (u'(', searchBack),
            u']': (u'[', searchBack),
            u'}': (u'{', searchBack),
        }
        look = matcher.get(ch)
        if look:
            return look[1](ch, look[0])

    def jumpToMatchingBracket(self):
        matchingBracketRowCol = self.getMatchingBracketRowCol()
        if matchingBracketRowCol is not None:
            self.penRow = matchingBracketRowCol[0]
            self.penCol = matchingBracketRowCol[1]

    def performDelete(self):
        if self.selectionMode != app.selectable.kSelectionNone:
            text = self.getSelectedText()
            if text:
                if self.selectionMode == app.selectable.kSelectionBlock:
                    upper = min(self.penRow, self.markerRow)
                    left = min(self.penCol, self.markerCol)
                    lower = max(self.penRow, self.markerRow)
                    right = max(self.penCol, self.markerCol)
                    self.cursorMoveAndMark(
                        upper - self.penRow, left - self.penCol,
                        lower - self.markerRow, right - self.markerCol, 0)
                elif (self.penRow > self.markerRow or
                      (self.penRow == self.markerRow and
                       self.penCol > self.markerCol)):
                    self.swapPenAndMarker()
                self.redoAddChange((u'ds', text))
                self.redo()
            self.selectionNone()

    def _performDeleteRange(self, upperRow, upperCol, lowerRow, lowerCol):
        if upperRow == self.penRow == lowerRow:
            if upperCol < self.penCol:
                col = upperCol - self.penCol
                if lowerCol <= self.penCol:
                    col = upperCol - lowerCol
                self.cursorMove(0, col)
        elif upperRow <= self.penRow < lowerRow:
            self.cursorMove(upperRow - self.penRow, upperCol - self.penCol)
        elif self.penRow == lowerRow:
            col = upperCol - lowerCol
            self.cursorMove(upperRow - self.penRow, col)
        self.redoAddChange((u'dr', (upperRow, upperCol, lowerRow, lowerCol),
                            self.getText(upperRow, upperCol, lowerRow,
                                         lowerCol)))
        self.redo()

    def getBookmarkColor(self):
        """Returns a new color by cycling through a predefined section of the
        color palette.

        Args:
          None.

        Returns:
          A color (int) for a new bookmark.
        """
        if self.program.prefs.startup[u'numColors'] == 8:
            goodColorIndices = [1, 2, 3, 4, 5]
        else:
            goodColorIndices = [97, 98, 113, 117, 127]
        self.nextBookmarkColorPos = (
            self.nextBookmarkColorPos + 1) % len(goodColorIndices)
        return goodColorIndices[self.nextBookmarkColorPos]

    def dataToBookmark(self):
        """Convert bookmark data to a bookmark.

        Args:
          None.

        Returns:
          A Bookmark object containing its range and the current state of the
          cursor and selection mode. The bookmark is also assigned a color,
          which is used to determine the color of the bookmark's line numbers.
        """
        bookmarkData = {
            u'marker': (self.markerRow, self.markerCol),
            u'pen': (self.penRow, self.penCol),
            u'selectionMode': self.selectionMode,
            u'colorIndex': self.getBookmarkColor()
        }
        upperRow, _, lowerRow, _ = self.startAndEnd()
        return app.bookmark.Bookmark(upperRow, lowerRow, bookmarkData)

    def bookmarkAdd(self):
        """Adds a bookmark at the cursor's location. If multiple lines are
        selected, all existing bookmarks in those lines are overwritten with the
        new bookmark.

        Args:
          None.

        Returns:
          None.
        """
        newBookmark = self.dataToBookmark()
        self.bookmarkRemove()
        bisect.insort_right(self.bookmarks, newBookmark)

    def bookmarkGoto(self, bookmark):
        """Goes to the bookmark that is passed in.

        Args:
          bookmark (Bookmark): The bookmark you want to jump to. This object is
                               defined in bookmark.py

        Returns:
          None.
        """
        bookmarkData = bookmark.data
        penRow, penCol = bookmarkData[u'pen']
        markerRow, markerCol = bookmarkData[u'marker']
        selectionMode = bookmarkData[u'selectionMode']
        self.cursorMoveAndMark(penRow - self.penRow, penCol - self.penCol,
                               markerRow - self.markerRow,
                               markerCol - self.markerCol,
                               selectionMode - self.selectionMode)
        self.scrollToOptimalScrollPosition()

    def bookmarkNext(self):
        """Goes to the closest bookmark after the cursor.

        Args:
          None.

        Returns:
          None.
        """
        if not len(self.bookmarks):
            self.setMessage(u"No bookmarks to jump to")
            return
        _, _, lowerRow, _ = self.startAndEnd()
        needle = app.bookmark.Bookmark(lowerRow + 1, lowerRow + 1, {})
        index = bisect.bisect_left(self.bookmarks, needle)
        self.bookmarkGoto(self.bookmarks[index % len(self.bookmarks)])

    def bookmarkPrior(self):
        """Goes to the closest bookmark before the cursor.

        Args:
          None.

        Returns:
          None.
        """
        if not len(self.bookmarks):
            self.setMessage(u"No bookmarks to jump to")
            return
        upperRow, _, _, _ = self.startAndEnd()
        needle = app.bookmark.Bookmark(upperRow, upperRow, {})
        index = bisect.bisect_left(self.bookmarks, needle)
        self.bookmarkGoto(self.bookmarks[index - 1])

    def bookmarkRemove(self):
        """Removes bookmarks in all selected lines.

        Args:
          None.

        Returns:
          (boolean) Whether any bookmarks were removed.
        """
        upperRow, _, lowerRow, _ = self.startAndEnd()
        rangeList = self.bookmarks
        needle = app.bookmark.Bookmark(upperRow, lowerRow, {})
        # Find the left-hand index.
        begin = bisect.bisect_left(rangeList, needle)
        if begin and needle.begin <= rangeList[begin - 1].end:
            begin -= 1
        # Find the right-hand index.
        low = begin
        index = begin
        high = len(rangeList)
        offset = needle.end
        while True:
            index = (high + low) // 2
            if low == high:
                break
            if offset >= rangeList[index].end:
                low = index + 1
            elif offset < rangeList[index].begin:
                high = index
            else:
                index += 1
                break
        if begin == index:
            return False
        self.bookmarks = rangeList[:begin] + rangeList[index:]
        return True

    def backspace(self):
        #app.log.info('backspace', self.penRow > self.markerRow)
        if self.selectionMode != app.selectable.kSelectionNone:
            self.performDelete()
        elif self.penCol == 0:
            if self.penRow > 0:
                self.cursorLeft()
                self.joinLines()
        else:
            line = self.parser.rowText(self.penRow)
            change = (u'b', line[self.penCol - 1:self.penCol])
            self.redoAddChange(change)
            self.redo()

    def backspaceWord(self):
        if self.selectionMode != app.selectable.kSelectionNone:
            self.performDelete()
        elif self.penCol == 0:
            if self.penRow > 0:
                self.cursorLeft()
                self.joinLines()
        else:
            line = self.parser.rowText(self.penRow)
            colDelta = self.getCursorMoveLeftTo(app.regex.kReWordBoundary)[1][1]
            change = (u'bw', line[self.penCol + colDelta:self.penCol])
            self.redoAddChange(change)
            self.redo()

    def carriageReturn(self):
        self.performDelete()
        grammar = self.parser.grammarAt(self.penRow, self.penCol)
        self.redoAddChange((u'n', 1, self.getCursorMove(1, -self.penCol)))
        self.redo()
        grammarIndent = grammar.get(u'indent')
        if grammarIndent:
            # TODO(): Hack fix. Reconsider how it should be done.
            self.doParse(self.penRow - 1, self.penRow + 1)
            line, width = self.parser.rowTextAndWidth(self.penRow - 1)
            #commonIndent = len(self.program.prefs.editor['indentation'])
            nonSpace = 0
            while nonSpace < width and line[nonSpace].isspace():
                nonSpace += 1
            indent = line[:nonSpace]
            if width:
                lastChar = line.rstrip()[-1:]
                if lastChar == u':':
                    indent += grammarIndent
                elif lastChar in [u'[', u'{']:
                    # Check whether a \n is inserted in {} or []; if so add
                    # another line and unindent the closing character.
                    splitLine = self.parser.rowText(self.penRow)
                    if splitLine[self.penCol:self.penCol + 1] in [u']', u'}']:
                        self.redoAddChange((u'i', indent))
                        self.redo()
                        self.cursorMove(0, -len(indent))
                        self.redo()
                        self.redoAddChange((u'n', 1, self.getCursorMove(0, 0)))
                        self.redo()
                    indent += grammarIndent
                elif lastChar in [u'=', u'+', u'-', u'/', u'*']:
                    indent += grammarIndent * 2
                # Good idea or bad idea?
                #elif indent >= 2 and line.lstrip()[:6] == 'return':
                #  indent -= grammarIndent
                elif line.count(u'(') > line.count(u')'):
                    indent += grammarIndent * 2
            if indent:
                self.redoAddChange((u'i', indent))
                self.redo()
        self.updateBasicScrollPosition()

    def cursorColDelta(self, toRow):
        if app.config.strict_debug:
            assert isinstance(toRow, int)
            assert 0 <= toRow < self.parser.rowCount()
        lineLen = self.parser.rowWidth(toRow)
        if self.goalCol <= lineLen:
            return self.goalCol - self.penCol
        return lineLen - self.penCol

    def cursorDown(self):
        self.selectionNone()
        self.cursorMoveDownOrEnd()

    def cursorDownScroll(self):
        self.selectionNone()
        self.scrollDown()

    def cursorLeft(self):
        self.selectionNone()
        self.cursorMoveLeft()

    def getCursorMove(self, rowDelta, colDelta):
        if app.config.strict_debug:
            assert isinstance(rowDelta, int)
            assert isinstance(colDelta, int)
        return self.getCursorMoveAndMark(rowDelta, colDelta, 0, 0, 0)

    def cursorMove(self, rowDelta, colDelta):
        self.cursorMoveAndMark(rowDelta, colDelta, 0, 0, 0)

    def getCursorMoveAndMark(self, rowDelta, colDelta, markRowDelta,
                             markColDelta, selectionModeDelta):
        if app.config.strict_debug:
            assert isinstance(rowDelta, int)
            assert isinstance(colDelta, int)
            assert isinstance(markRowDelta, int)
            assert isinstance(markColDelta, int)
            assert isinstance(selectionModeDelta, int)
        if self.penCol + colDelta < 0:  # Catch cursor at beginning of line.
            colDelta = -self.penCol
        self.goalCol = self.penCol + colDelta
        return ('m', (rowDelta, colDelta, markRowDelta, markColDelta,
                      selectionModeDelta))

    def cursorMoveAndMark(self, rowDelta, colDelta, markRowDelta, markColDelta,
                          selectionModeDelta):
        if app.config.strict_debug:
            assert isinstance(rowDelta, int)
            assert isinstance(colDelta, int)
        change = self.getCursorMoveAndMark(rowDelta, colDelta, markRowDelta,
                                           markColDelta, selectionModeDelta)
        self.redoAddChange(change)
        self.redo()

    def cursorMoveScroll(self, rowDelta, colDelta, scrollRowDelta,
                         scrollColDelta):
        self.updateScrollPosition(scrollRowDelta, scrollColDelta)
        self.redoAddChange((u'm', (rowDelta, colDelta, 0, 0, 0)))

    def unused_____cursorMoveDown(self):
        if self.penRow == self.parser.rowCount() - 1:
            self.setMessage(u'Bottom of file')
            return
        savedGoal = self.goalCol
        self.cursorMove(1, self.cursorColDelta(self.penRow + 1))
        self.goalCol = savedGoal
        self.adjustHorizontalScroll()

    def cursorMoveDownOrEnd(self):
        savedGoal = self.goalCol
        if self.penRow == self.parser.rowCount() - 1:
            self.setMessage(u'End of file')
            width = self.parser.rowWidth(self.penRow)
            self.cursorMove(0, width - self.penCol)
        else:
            self.cursorMove(1, self.cursorColDelta(self.penRow + 1))
        self.goalCol = savedGoal
        self.adjustHorizontalScroll()

    def adjustHorizontalScroll(self):
        if self.view.scrollCol:
            width = self.parser.rowWidth(self.penRow)
            if width < self.view.cols:
                # The whole line fits on screen.
                self.view.scrollCol = 0
            elif (self.view.scrollCol == self.penCol and
                  self.penCol == width):
                self.view.scrollCol = max(
                    0, self.view.scrollCol - self.view.cols // 4)

    def cursorMoveLeft(self):
        if not self.parser.rowCount():
            return
        rowCol = self.parser.priorCharRowCol(self.penRow, self.penCol)
        if rowCol is None:
            self.setMessage(u'Top of file')
        else:
            self.cursorMove(*rowCol)

    def cursorMoveRight(self):
        if not self.parser.rowCount():
            return
        rowCol = self.parser.nextCharRowCol(self.penRow, self.penCol)
        if rowCol is None:
            self.setMessage(u'Bottom of file')
        else:
            self.cursorMove(*rowCol)

    def unused_____cursorMoveUp(self):
        if self.penRow <= 0:
            self.setMessage(u'Top of file')
            return
        savedGoal = self.goalCol
        lineLen = self.parser.rowWidth(self.penRow - 1)
        if self.goalCol <= lineLen:
            self.cursorMove(-1, self.goalCol - self.penCol)
        else:
            self.cursorMove(-1, lineLen - self.penCol)
        self.goalCol = savedGoal
        self.adjustHorizontalScroll()

    def cursorMoveToBegin(self):
        savedGoal = self.goalCol
        self.setMessage(u'Top of file')
        self.cursorMove(-self.penRow, -self.penCol)
        self.goalCol = savedGoal
        self.updateBasicScrollPosition()

    def cursorMoveUpOrBegin(self):
        savedGoal = self.goalCol
        if self.penRow <= 0:
            self.setMessage(u'Top of file')
            self.cursorMove(0, -self.penCol)
        else:
            lineLen = self.parser.rowWidth(self.penRow - 1)
            if self.goalCol <= lineLen:
                self.cursorMove(-1, self.goalCol - self.penCol)
            else:
                self.cursorMove(-1, lineLen - self.penCol)
        self.goalCol = savedGoal
        self.adjustHorizontalScroll()

    def cursorMoveSubwordLeft(self):
        self.selectionNone()
        self.doCursorMoveLeftTo(app.regex.kReSubwordBoundaryRvr)

    def cursorMoveSubwordRight(self):
        self.selectionNone()
        self.doCursorMoveRightTo(app.regex.kReSubwordBoundaryFwd)

    def cursorMoveTo(self, row, col):
        penRow = min(max(row, 0), self.parser.rowCount() - 1)
        self.cursorMove(penRow - self.penRow, col - self.penCol)

    def cursorMoveWordLeft(self):
        self.selectionNone()
        self.doCursorMoveLeftTo(app.regex.kReWordBoundary)

    def cursorMoveWordRight(self):
        self.selectionNone()
        self.doCursorMoveRightTo(app.regex.kReWordBoundary)

    def getCursorMoveLeftTo(self, boundary):
        if self.penCol > 0:
            line = self.parser.rowText(self.penRow)
            pos = self.penCol
            for segment in re.finditer(boundary, line):
                if segment.start() < pos <= segment.end():
                    pos = segment.start()
                    break
            return self.getCursorMove(0, pos - self.penCol)
        elif self.penRow > 0:
            return self.getCursorMove(-1, self.parser.rowWidth(self.penRow - 1))
        return self.getCursorMove(0, 0)

    def doCursorMoveLeftTo(self, boundary):
        change = self.getCursorMoveLeftTo(boundary)
        self.redoAddChange(change)
        self.redo()

    def doCursorMoveRightTo(self, boundary):
        if not self.parser.rowCount():
            return
        line, lineWidth = self.parser.rowTextAndWidth(self.penRow)
        if self.penCol < lineWidth:
            pos = self.penCol
            for segment in re.finditer(boundary, line):
                if segment.start() <= pos < segment.end():
                    pos = segment.end()
                    break
            self.cursorMove(0, pos - self.penCol)
        elif self.penRow + 1 < self.parser.rowCount():
            self.cursorMove(1, -lineWidth)

    def cursorRight(self):
        self.selectionNone()
        self.cursorMoveRight()

    def cursorSelectDown(self):
        if self.selectionMode == app.selectable.kSelectionNone:
            self.selectionCharacter()
        self.cursorMoveDownOrEnd()

    def cursorSelectDownScroll(self):
        """Move the line below the selection to above the selection."""
        upperRow, _, lowerRow, _ = self.startAndEnd()
        if lowerRow + 1 >= self.parser.rowCount():
            return
        begin = lowerRow + 1
        end = lowerRow + 2
        to = upperRow
        self.redoAddChange((u'ml', (begin, end, to)))
        self.redo()

    def cursorSelectLeft(self):
        if self.selectionMode == app.selectable.kSelectionNone:
            self.selectionCharacter()
        self.cursorMoveLeft()

    def cursorSelectRight(self):
        if self.selectionMode == app.selectable.kSelectionNone:
            self.selectionCharacter()
        self.cursorMoveRight()

    def cursorSelectSubwordLeft(self):
        if self.selectionMode == app.selectable.kSelectionNone:
            self.selectionCharacter()
        self.cursorMoveSubwordLeft()
        self.cursorMoveAndMark(*self.extendSelection())

    def cursorSelectSubwordRight(self):
        if self.selectionMode == app.selectable.kSelectionNone:
            self.selectionCharacter()
        self.cursorMoveSubwordRight()
        self.cursorMoveAndMark(*self.extendSelection())

    def cursorSelectWordLeft(self):
        if self.selectionMode == app.selectable.kSelectionNone:
            self.selectionCharacter()
        self.doCursorMoveLeftTo(app.regex.kReWordBoundary)
        self.cursorMoveAndMark(*self.extendSelection())

    def cursorSelectWordRight(self):
        if self.selectionMode == app.selectable.kSelectionNone:
            self.selectionCharacter()
        self.doCursorMoveRightTo(app.regex.kReWordBoundary)
        self.cursorMoveAndMark(*self.extendSelection())

    def cursorSelectUp(self):
        if self.selectionMode == app.selectable.kSelectionNone:
            self.selectionCharacter()
        self.cursorMoveUpOrBegin()

    def cursorSelectUpScroll(self):
        """Move the line above the selection to below the selection."""
        upperRow, _, lowerRow, _ = self.startAndEnd()
        if upperRow == 0:
            return
        begin = upperRow - 1
        end = upperRow
        to = lowerRow + 1
        self.redoAddChange((u'ml', (begin, end, to)))
        self.redo()

    def cursorEndOfLine(self):
        lineLen = self.parser.rowWidth(self.penRow)
        self.cursorMove(0, lineLen - self.penCol)

    def cursorSelectToStartOfLine(self):
        self.selectionCharacter()
        self.cursorStartOfLine()

    def cursorSelectToEndOfLine(self):
        self.selectionCharacter()
        self.cursorEndOfLine()

    def __cursorPageDown(self):
        """Moves the view and cursor down by a page or stops at the bottom of
        the document if there is less than a page left.

        Args:
          None.

        Returns:
          None.
        """
        if self.penRow == self.parser.rowCount() - 1:
            self.setMessage(u'Bottom of file')
            return
        maxRow = self.view.rows
        penRowDelta = maxRow
        scrollRowDelta = maxRow
        numLines = self.parser.rowCount()
        if self.penRow + maxRow >= numLines:
            penRowDelta = numLines - self.penRow - 1
        if numLines <= maxRow:
            scrollRowDelta = -self.view.scrollRow
        elif numLines <= 2 * maxRow + self.view.scrollRow:
            scrollRowDelta = numLines - self.view.scrollRow - maxRow
        self.cursorMoveScroll(penRowDelta,
                              self.cursorColDelta(self.penRow + penRowDelta),
                              scrollRowDelta, 0)
        self.redo()

    def __cursorPageUp(self):
        """Moves the view and cursor up by a page or stops at the top of the
        document if there is less than a page left.

        Args:
          None.

        Returns:
          None.
        """
        if self.penRow == 0:
            self.setMessage(u'Top of file')
            return
        maxRow = self.view.rows
        penRowDelta = -maxRow
        scrollRowDelta = -maxRow
        if self.penRow < maxRow:
            penRowDelta = -self.penRow
        if self.view.scrollRow + scrollRowDelta < 0:
            scrollRowDelta = -self.view.scrollRow
        cursorColDelta = self.cursorColDelta(self.penRow + penRowDelta)
        self.cursorMoveScroll(penRowDelta, cursorColDelta, scrollRowDelta, 0)
        self.redo()

    def cursorSelectNonePageDown(self):
        """Performs a page down. This function does not select any text and
        removes all existing highlights.

        Args:
          None.

        Returns:
          None.
        """
        self.selectionNone()
        self.__cursorPageDown()

    def cursorSelectNonePageUp(self):
        """Performs a page up. This function does not select any text and
        removes all existing highlights.

        Args:
          None.

        Returns:
          None.
        """
        self.selectionNone()
        self.__cursorPageUp()

    def cursorSelectCharacterPageDown(self):
        """Performs a page down. This function selects all characters between
        the previous and current cursor position.

        Args:
          None.

        Returns:
          None.
        """
        self.selectionCharacter()
        self.__cursorPageDown()

    def cursorSelectCharacterPageUp(self):
        """Performs a page up. This function selects all characters between the
        previous and current cursor position.

        Args:
          None.

        Returns:
          None.
        """
        self.selectionCharacter()
        self.__cursorPageUp()

    def cursorSelectBlockPageDown(self):
        """Performs a page down. This function sets the selection mode to
        "block.".

        Args:
          None.

        Returns:
          None.
        """
        self.selectionBlock()
        self.__cursorPageDown()

    def cursorSelectBlockPageUp(self):
        """Performs a page up. This function sets the selection mode to
        "block.".

        Args:
          None.

        Returns:
          None.
        """
        self.selectionBlock()
        self.__cursorPageUp()

    def cursorScrollToMiddle(self):
        maxRow = self.view.rows
        rowDelta = min(
            max(0,
                self.parser.rowCount() - maxRow), max(
                    0, self.penRow - maxRow // 2)) - self.view.scrollRow
        self.cursorMoveScroll(0, 0, rowDelta, 0)

    def cursorStartOfLine(self):
        self.cursorMove(0, -self.penCol)

    def cursorUp(self):
        self.selectionNone()
        self.cursorMoveUpOrBegin()

    def cursorUpScroll(self):
        self.selectionNone()
        self.scrollUp()

    def delCh(self):
        line = self.parser.rowText(self.penRow)
        change = (u'd', line[self.penCol:self.penCol + 1])
        self.redoAddChange(change)
        self.redo()

    def delete(self):
        """Delete character to right of pen i.e. Del key."""
        if self.selectionMode != app.selectable.kSelectionNone:
            self.performDelete()
        elif self.penCol == self.parser.rowWidth(self.penRow):
            if self.penRow + 1 < self.parser.rowCount():
                self.joinLines()
        else:
            self.delCh()

    def deleteToEndOfLine(self):
        line, lineWidth = self.parser.rowTextAndWidth(self.penRow)
        if self.penCol == lineWidth:
            if self.penRow + 1 < self.parser.rowCount():
                self.joinLines()
        else:
            change = (u'd', line[self.penCol:])
            self.redoAddChange(change)
            self.redo()

    def editCopy(self):
        text = self.getSelectedText()
        if len(text):
            data = self.doLinesToData(text)
            self.program.clipboard.copy(data)
            if len(text) == 1:
                self.setMessage(u'copied %d characters' % len(text[0]))
            else:
                self.setMessage(u'copied %d lines' % (len(text),))

    def editCut(self):
        self.editCopy()
        self.performDelete()

    def editPaste(self):
        data = self.program.clipboard.paste()
        if not isinstance(data, unicode) and hasattr(data, 'decode'):
            data = data.decode('utf-8')
        if data is not None:
            self.editPasteData(data)
        else:
            app.log.info(u'clipboard empty')

    def editPasteData(self, data):
        self.editPasteLines(tuple(self.doDataToLines(data)))

    def editPasteLines(self, clip):
        if self.selectionMode != app.selectable.kSelectionNone:
            self.performDelete()
        self.redoAddChange((u'v', clip))
        self.redo()
        rowDelta = len(clip) - 1
        if rowDelta == 0:
            endCol = self.penCol + app.curses_util.columnWidth(clip[0])
        else:
            endCol = app.curses_util.columnWidth(clip[-1])
        app.log.info(self.goalCol, endCol, self.penCol, endCol - self.penCol)
        self.cursorMove(rowDelta, endCol - self.penCol)

    def editRedo(self):
        """Undo a set of redo nodes."""
        self.redo()
        if not self.isSelectionInView():
            self.scrollToOptimalScrollPosition()

    def editUndo(self):
        """Undo a set of redo nodes."""
        self.undo()
        if not self.isSelectionInView():
            self.scrollToOptimalScrollPosition()

    def fileFilter(self, data):
        self.data = data
        self.dataToLines()
        self.upperChangedRow = 0
        self.savedAtRedoIndex = self.redoIndex

    def fileLoad(self):
        app.log.info(u'fileLoad', self.fullPath)
        inputFile = None
        self.isReadOnly = (os.path.isfile(self.fullPath) and
                           not os.access(self.fullPath, os.W_OK))
        if not os.path.exists(self.fullPath):
            data = u''
            self.setMessage(u'Creating new file')
        else:
            try:
                inputFile = io.open(self.fullPath)
                data = unicode(inputFile.read())
                self.fileEncoding = inputFile.encoding
                self.setMessage(u'Opened existing file')
                self.isBinary = False
            except Exception as e:
                #app.log.info(unicode(e))
                try:
                    inputFile = io.open(self.fullPath, 'rb')
                    if 1:
                        binary_data = inputFile.read()
                        long_hex = binascii.hexlify(binary_data).decode('utf-8')
                        hex_list = []
                        i = 0
                        width = 32
                        while i < len(long_hex):
                            hex_list.append(long_hex[i:i + width] + u'\n')
                            i += width
                        data = u''.join(hex_list)
                    else:
                        data = inputFile.read()
                    self.isBinary = True
                    self.fileEncoding = None
                    app.log.info(u'Opened file as a binary file')
                    self.setMessage(u'Opened file as a binary file')
                except Exception as e:
                    app.log.info(unicode(e))
                    app.log.info(u'error opening file', self.fullPath)
                    self.setMessage(u'error opening file', self.fullPath)
                    return
            self.fileStat = os.stat(self.fullPath)
        self.relativePath = os.path.relpath(self.fullPath, os.getcwd())
        app.log.info(u'fullPath', self.fullPath)
        app.log.info(u'cwd', os.getcwd())
        app.log.info(u'relativePath', self.relativePath)
        self.fileFilter(data)
        if inputFile:
            inputFile.close()
        self.determineFileType()

    def _determineRootGrammar(self, name, extension):
        if extension == u"" and self.parser.rowCount() > 0:
            line = self.parser.rowText(0)
            if line.startswith(u'#!'):
                if u'python' in line:
                    extension = u'.py'
                elif u'bash' in line:
                    extension = u'.sh'
                elif u'node' in line:
                    extension = u'.js'
                elif u'sh' in line:
                    extension = u'.sh'
        if self.fileExtension != extension:
            self.fileExtension = extension
            self.upperChangedRow = 0
        return self.program.prefs.getGrammar(name + extension)

    def determineFileType(self):
        self.rootGrammar = self._determineRootGrammar(
            *os.path.splitext(self.fullPath))
        self.parseGrammars()
        self.dataToLines()

        # Restore all user history.
        self.restoreUserHistory()

    def replaceLines(self, clip):
        self.selectionAll()
        self.editPasteLines(tuple(clip))

    def restoreUserHistory(self):
        """This function restores all stored history of the file into the
        TextBuffer object. If there does not exist a stored history of the file,
        it will initialize the variables to default values.

        Args:
          None.

        Returns:
          None.
        """
        # Restore the file history.
        self.fileHistory = self.program.history.getFileHistory(
            self.fullPath, self.data)

        # Restore all positions and values of variables.
        self.penRow, self.penCol = self.fileHistory.setdefault(u'pen', (0, 0))
        # Need to initialize goalCol since we set the cursor position directly
        # instead of performing a chain of redoes (which sets goalCol).
        self.goalCol = self.penCol
        # Do not restore the scroll position here because the view may not be
        # set. the scroll position is handled in the InputWindow.setTextBuffer.
        # self.view.scrollRow, self.view.scrollCol =
        #     self.fileHistory.setdefault(
        #     'scroll', (0, 0))
        self.doSelectionMode(
            self.fileHistory.setdefault(u'selectionMode',
                                        app.selectable.kSelectionNone))
        self.markerRow, self.markerCol = self.fileHistory.setdefault(
            u'marker', (0, 0))
        if self.program.prefs.editor[u'saveUndo']:
            self.redoChain = self.fileHistory.setdefault(
                u'redoChainCompound', [])
            self.savedAtRedoIndex = self.fileHistory.setdefault(
                u'savedAtRedoIndexCompound', 0)
            self.tempChange = self.fileHistory.setdefault(u'tempChange', None)
            self.redoIndex = self.savedAtRedoIndex
            self.oldRedoIndex = self.savedAtRedoIndex
        if app.config.strict_debug:
            assert self.penRow < self.parser.rowCount(), self.penRow
            assert self.markerRow < self.parser.rowCount(), self.markerRow

        # Restore file bookmarks
        self.bookmarks = self.fileHistory.setdefault(u'bookmarks', [])

        # Store the file's info.
        self.lastChecksum, self.lastFileSize = app.history.getFileInfo(
            self.fullPath)

    def updateBasicScrollPosition(self):
        """Sets scrollRow, scrollCol to the closest values that the view's
        position must be in order to see the cursor.

        Args:
          None.

        Returns:
          None.
        """
        if self.view is None:
            return
        # Row.
        maxRow = self.view.rows
        if self.view.scrollRow > self.penRow:
            self.view.scrollRow = self.penRow
        elif self.penRow >= self.view.scrollRow + maxRow:
            self.view.scrollRow = self.penRow - maxRow + 1
        # Column.
        maxCol = self.view.cols
        if self.view.scrollCol > self.penCol:
            self.view.scrollCol = self.penCol
        elif self.penCol >= self.view.scrollCol + maxCol:
            self.view.scrollCol = self.penCol - maxCol + 1

    def scrollToOptimalScrollPosition(self):
        """Put the selection in the 'optimal' position in the view. What is
        optimal is defined by the "optimalCursorRow" and "optimalCursorCol"
        preferences.

        Args:
          None.

        Returns:
          A tuple of (scrollRow, scrollCol) representing where the view's
          optimal position should be.
        """
        if self.view is None:
            return
        top, left, bottom, right = self.startAndEnd()
        # Row.
        maxRows = self.view.rows
        scrollRow = self.view.scrollRow
        height = bottom - top + 1
        extraRows = maxRows - height
        if extraRows > 0:
            optimalRowRatio = self.program.prefs.editor[u'optimalCursorRow']
            scrollRow = max(
                0,
                min(
                    self.parser.rowCount() - 1,
                    top - int(optimalRowRatio * (maxRows - 1))))
        else:
            scrollRow = top
        # Column.
        maxCols = self.view.cols
        scrollCol = self.view.scrollCol
        length = right - left + 1
        extraCols = maxCols - length
        if extraCols > 0:
            if right < maxCols:
                scrollCol = 0
            else:
                optimalColRatio = self.program.prefs.editor[u'optimalCursorCol']
                scrollCol = max(
                    0, min(right, left - int(optimalColRatio * (maxCols - 1))))
        else:
            scrollCol = left
        self.view.scrollRow = scrollRow
        self.view.scrollCol = scrollCol

    def isSelectionInView(self):
        """If there is no selection, checks if the cursor is in the view.

        Args:
          None.

        Returns:
          True if selection is in view. Otherwise, False.
        """
        return self.isInView(*self.startAndEnd())

    def isInView(self, top, left, bottom, right):
        """Determine if the rectangle is visible in the view. Returns:

        True if selection is in view. Otherwise, False.
        """
        if self.view is None:
            return False
        horizontally = (self.view.scrollCol <= left and
                        right < self.view.scrollCol + self.view.cols)
        vertically = (self.view.scrollRow <= top and
                      bottom < self.view.scrollRow + self.view.rows)
        return horizontally and vertically

    def fenceRedoChain(self):
        self.redoAddChange((u'f',))
        self.redo()

    def fileWrite(self):
        # Preload the message with an error that should be overwritten.
        self.setMessage(u'Error saving file')
        self.isReadOnly = not os.access(self.fullPath, os.W_OK)
        self.fenceRedoChain()
        try:
            try:
                if self.program.prefs.editor[u'onSaveStripTrailingSpaces']:
                    self.stripTrailingWhiteSpace()
                    self.compoundChangePush()
                # Save user data that applies to read-only files into history.
                self.fileHistory[u'path'] = self.fullPath
                self.fileHistory[u'pen'] = (self.penRow, self.penCol)
                if self.view is not None:
                    self.fileHistory[u'scroll'] = (self.view.scrollRow,
                                                   self.view.scrollCol)
                self.fileHistory[u'marker'] = (self.markerRow, self.markerCol)
                self.fileHistory[u'selectionMode'] = self.selectionMode
                self.fileHistory[u'bookmarks'] = self.bookmarks
                self.linesToData()
                if self.isBinary:
                    removeWhitespace = {
                        ord(u' '): None,
                        ord(u'\n'): None,
                        ord(u'\r'): None,
                        ord(u'\t'): None,
                    }
                    outputData = binascii.unhexlify(
                        self.data.translate(removeWhitespace))
                    outputFile = io.open(self.fullPath, u'wb+')
                elif self.fileEncoding is None:
                    outputData = self.data
                    outputFile = io.open(
                        self.fullPath, u'w+', encoding=u'UTF-8')
                else:
                    outputData = self.data
                    outputFile = io.open(
                        self.fullPath, 'w+', encoding=self.fileEncoding)
                outputFile.seek(0)
                outputFile.truncate()
                outputFile.write(outputData)
                outputFile.close()
                # Save user data that applies to writable files.
                self.savedAtRedoIndex = self.redoIndex
                if self.program.prefs.editor[u'saveUndo']:
                    self.fileHistory[u'redoChainCompound'] = self.redoChain
                    self.fileHistory[
                        u'savedAtRedoIndexCompound'] = self.savedAtRedoIndex
                    self.fileHistory[u'tempChange'] = self.tempChange
                self.program.history.saveUserHistory(
                    (self.fullPath, self.lastChecksum, self.lastFileSize),
                    self.fileHistory)
                # Store the file's new info
                self.lastChecksum, self.lastFileSize = app.history.getFileInfo(
                    self.fullPath)
                self.fileStat = os.stat(self.fullPath)
                # If we're writing this file for the first time, self.isReadOnly
                # will still be True (from when it didn't exist).
                self.isReadOnly = False
                self.setMessage(u'File saved')
            except Exception as e:
                color = self.program.prefs.color.get(u'status_line_error')
                if self.isReadOnly:
                    self.setMessage(
                        u"Permission error. Try modifying in sudo mode.",
                        color=color)
                else:
                    self.setMessage(
                        u'Error writing file. The file did not save properly.',
                        color=color)
                app.log.error(u'error writing file')
                app.log.exception(e)
        except Exception:
            app.log.info(u'except had exception')
        self.determineFileType()

    def selectText(self, row, col, length, mode):
        if app.config.strict_debug:
            assert isinstance(row, int)
            assert isinstance(col, int)
            assert isinstance(length, int)
            assert isinstance(mode, int)
        row = max(0, min(row, self.parser.rowCount() - 1))
        rowWidth = self.parser.rowWidth(row)
        col = max(0, min(col, rowWidth))
        endCol = col + length
        inView = self.isInView(row, endCol, row, endCol)
        self.doSelectionMode(app.selectable.kSelectionNone)
        self.cursorMove(row - self.penRow, endCol - self.penCol)
        self.doSelectionMode(mode)
        self.cursorMove(0, -length)
        if not inView:
            self.scrollToOptimalScrollPosition()

    def find(self, searchFor, direction=0):
        """direction is -1 for findPrior, 0 for at pen, 1 for findNext."""
        if app.config.strict_debug:
            assert isinstance(searchFor, unicode)
            assert isinstance(direction, int)
        app.log.info(searchFor, direction)
        if not len(searchFor):
            self.findRe = None
            self.doSelectionMode(app.selectable.kSelectionNone)
            return
        editorPrefs = self.program.prefs.editor
        flags = 0
        flags |= (editorPrefs.get(u'findIgnoreCase') and re.IGNORECASE or 0)
        flags |= (editorPrefs.get(u'findMultiLine') and re.MULTILINE or 0)
        flags |= (editorPrefs.get(u'findLocale') and re.LOCALE or 0)
        flags |= (editorPrefs.get(u'findDotAll') and re.DOTALL or 0)
        flags |= (editorPrefs.get(u'findVerbose') and re.VERBOSE or 0)
        flags |= (editorPrefs.get(u'findUnicode') and re.UNICODE or 0)
        if not editorPrefs.get(u'findUseRegex'):
            searchFor = re.escape(searchFor)
        if editorPrefs.get(u'findWholeWord'):
            searchFor = r"\b%s\b" % searchFor
        #app.log.info(searchFor, flags)
        with warnings.catch_warnings():
            # Ignore future warning with '[[' regex.
            warnings.simplefilter("ignore")
            # The saved re is also used for highlighting.
            self.findRe = re.compile(searchFor, flags)
            self.findBackRe = re.compile(u"%s(?!.*%s.*)" % (searchFor, searchFor),
                                         flags)
        self.findCurrentPattern(direction)

    def replaceFound(self, replaceWith):
        """direction is -1 for findPrior, 0 for at pen, 1 for findNext."""
        if app.config.strict_debug:
            assert isinstance(replaceWith, unicode)
        if not self.findRe:
            return
        if self.program.prefs.editor.get(u'findUseRegex'):
            toReplace = "\n".join(self.getSelectedText())
            try:
                toReplace = self.findRe.sub(replaceWith, toReplace)
            except re.error as e:
                # TODO(dschuyler): This is stomped by another setMessage().
                self.setMessage(str(e))
            self.editPasteData(toReplace)
        else:
            self.editPasteData(replaceWith)

    def findPlainText(self, text):
        searchFor = re.escape(text)
        self.findRe = re.compile(u'()^' + searchFor)
        self.findCurrentPattern(0)

    def findReplaceFlags(self, tokens):
        """Map letters in |tokens| to re flags."""
        flags = re.MULTILINE
        if u'i' in tokens:
            flags |= re.IGNORECASE
        if u'l' in tokens:
            # Affects \w, \W, \b, \B.
            flags |= re.LOCALE
        if u'm' in tokens:
            # Affects ^, $.
            flags |= re.MULTILINE
        if u's' in tokens:
            # Affects ..
            flags |= re.DOTALL
        if u'x' in tokens:
            # Affects whitespace and # comments.
            flags |= re.VERBOSE
        if u'u' in tokens:
            # Affects \w, \W, \b, \B.
            flags |= re.UNICODE
        if 0:
            tokens = re.sub(u'[ilmsxu]', u'', tokens)
            if len(tokens):
                self.setMessage(u'unknown regex flags ' + tokens)
        return flags

    def findReplace(self, cmd):
        """Replace (substitute) text using regex in entire document.

        In a command such as `substitute/a/b/flags`, the `substitute` should
        already be removed. The remaining |cmd| of `/a/b/flags` implies a
        separator of '/' since that is the first character. The values between
        separators are:
          - 'a': search string (regex)
          - 'b': replacement string (may contain back references into the regex)
          - 'flags': regex flags string to be parsed by |findReplaceFlags()|.
        """
        if not len(cmd):
            return
        separator = cmd[0]
        splitCmd = cmd.split(separator, 3)
        if len(splitCmd) < 4:
            self.setMessage(u'An exchange needs three ' + separator +
                            u' separators')
            return
        _, find, replace, flags = splitCmd
        self.linesToData()
        data = self.findReplaceText(find, replace, flags, self.data)
        self.applyDocumentUpdate(data)

    def findReplaceText(self, find, replace, flags, text):
        flags = self.findReplaceFlags(flags)
        return re.sub(find, replace, text, flags=flags)

    def applyDocumentUpdate(self, data):
        diff = difflib.ndiff(self.lines, self.doDataToLines(data))
        ndiff = []
        counter = 0
        for i in diff:
            if i[0] != u' ':
                if counter:
                    ndiff.append(counter)
                    counter = 0
                if i[0] in [u'+', u'-']:
                    ndiff.append(i)
            else:
                counter += 1
        if counter:
            ndiff.append(counter)
        if len(ndiff) == 1 and type(ndiff[0]) is type(0):
            # Nothing was changed. The only entry is a 'skip these lines'
            self.setMessage(u'No matches found')
            return
        ndiff = tuple(ndiff)
        if 0:
            for i in ndiff:
                app.log.info(i)
        self.redoAddChange((u'ld', ndiff))
        self.redo()

    def findCurrentPattern(self, direction):
        localRe = self.findRe
        offset = self.penCol + direction
        if direction < 0:
            localRe = self.findBackRe
        if localRe is None:
            app.log.info(u'localRe is None')
            return
        # Check part of current line.
        text = self.parser.rowText(self.penRow)
        if direction >= 0:
            text = text[offset:]
        else:
            text = text[:self.penCol]
            offset = 0
        #app.log.info(u'find() searching', repr(text))
        found = localRe.search(text)
        rowFound = self.penRow
        if not found:
            offset = 0
            rowCount = self.parser.rowCount()
            # To end of file.
            if direction >= 0:
                theRange = range(self.penRow + 1, rowCount)
            else:
                theRange = range(self.penRow - 1, -1, -1)
            for i in theRange:
                found = localRe.search(self.parser.rowText(i))
                if found:
                    if 0:
                        for k in found.regs:
                            app.log.info(u'AAA', k[0], k[1])
                        app.log.info(u'b found on line', i, repr(found))
                    rowFound = i
                    break
            if not found:
                # Wrap around to the opposite side of the file.
                self.setMessage(u'Find wrapped around.')
                if direction >= 0:
                    theRange = range(self.penRow)
                else:
                    theRange = range(rowCount - 1, self.penRow, -1)
                for i in theRange:
                    found = localRe.search(self.parser.rowText(i))
                    if found:
                        rowFound = i
                        break
                if not found:
                    # Check the rest of the current line
                    if direction >= 0:
                        text = self.parser.rowText(self.penRow)
                    else:
                        text = self.parser.rowText(self.penRow)[self.penCol:]
                        offset = self.penCol
                    found = localRe.search(text)
                    rowFound = self.penRow
        if found:
            #app.log.info(u'c found on line', rowFound, repr(found.regs))
            start = found.regs[0][0]
            end = found.regs[0][1]
            self.selectText(rowFound, offset + start, end - start,
                            app.selectable.kSelectionCharacter)
            return
        app.log.info(u'find not found')
        self.doSelectionMode(app.selectable.kSelectionNone)

    def findAgain(self):
        """Find the current pattern, searching down the document."""
        self.findCurrentPattern(1)

    def findBack(self):
        """Find the current pattern, searching up the document."""
        self.findCurrentPattern(-1)

    def findNext(self, searchFor):
        """Find a new pattern, searching down the document."""
        self.find(searchFor, 1)

    def findPrior(self, searchFor):
        """Find a new pattern, searching up the document."""
        self.find(searchFor, -1)

    def indent(self):
        grammar = self.parser.grammarAt(self.penRow, self.penCol)
        indentation = (grammar.get(u'indent') or
                       self.program.prefs.editor[u'indentation'])
        indentationLength = len(indentation)
        if self.selectionMode == app.selectable.kSelectionNone:
            self.verticalInsert(self.penRow, self.penRow, self.penCol,
                                indentation)
        else:
            self.indentLines()
        self.cursorMoveAndMark(0, indentationLength, 0, indentationLength, 0)

    def indentLines(self):
        """Indents all selected lines.

        Do not use for when the selection mode is kSelectionNone since
        markerRow/markerCol currently do not get updated alongside
        penRow/penCol.
        """
        col = 0
        row = min(self.markerRow, self.penRow)
        endRow = max(self.markerRow, self.penRow)
        indentation = self.program.prefs.editor[u'indentation']
        self.verticalInsert(row, endRow, col, indentation)

    def verticalDelete(self, row, endRow, col, text):
        self.redoAddChange((u'vd', (text, row, endRow, col)))
        self.redo()
        if row <= self.markerRow <= endRow:
            self.cursorMoveAndMark(0, 0, 0, -len(text), 0)
        if row <= self.penRow <= endRow:
            self.cursorMoveAndMark(0, -len(text), 0, 0, 0)

    def verticalInsert(self, row, endRow, col, text):
        self.redoAddChange((u'vi', (text, row, endRow, col)))
        self.redo()

    def insert(self, text):
        if app.config.strict_debug:
            assert isinstance(text, unicode)
        self.performDelete()
        self.redoAddChange((u'i', text))
        self.redo()
        self.updateBasicScrollPosition()

    def insertPrintable(self, ch, meta):
        #app.log.info(ch, meta)
        if ch is app.curses_util.BRACKETED_PASTE:
            self.editPasteData(meta)
        elif ch is app.curses_util.UNICODE_INPUT:
            self.insert(meta)
        elif type(ch) is int and curses.ascii.isprint(ch):
            self.insert(unichr(ch))

    def insertPrintableWithPairing(self, ch, meta):
        #app.log.info(ch, meta)
        if type(ch) is int and curses.ascii.isprint(ch):
            if self.program.prefs.editor['autoInsertClosingCharacter']:
                pairs = {
                    ord(u"'"): u"'",
                    ord(u'"'): u'"',
                    ord(u'('): u')',
                    ord(u'{'): u'}',
                    ord(u'['): u']',
                }
                skips = pairs.values()
                mate = pairs.get(ch)
                nextChr = self.parser.charAt(self.penRow, self.penCol)
                if unichr(ch) in skips and unichr(ch) == nextChr:
                    self.cursorMove(0, 1)
                elif mate is not None and (nextChr is None or
                                           nextChr.isspace()):
                    self.insert(unichr(ch) + mate)
                    self.compoundChangePush()
                    self.cursorMove(0, -1)
                else:
                    self.insert(unichr(ch))
            else:
                self.insert(unichr(ch))
        elif ch is app.curses_util.BRACKETED_PASTE:
            self.editPasteData(meta)
        elif ch is app.curses_util.UNICODE_INPUT:
            self.insert(meta)

    def joinLines(self):
        """join the next line onto the current line."""
        self.redoAddChange((u'j',))
        self.redo()

    def markerPlace(self):
        self.redoAddChange((u'm', (0, 0, self.penRow - self.markerRow,
                                   self.penCol - self.markerCol, 0)))
        self.redo()

    def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
        if 0:
            if ctrl:
                app.log.info(u'click at', paneRow, paneCol)
                self.view.presentModal(self.view.contextMenu, paneRow, paneCol)
                return
        if shift:
            if alt:
                self.selectionBlock()
            elif self.selectionMode == app.selectable.kSelectionNone:
                self.selectionCharacter()
        else:
            self.selectionNone()
        self.mouseRelease(paneRow, paneCol, shift, ctrl, alt)

    def mouseDoubleClick(self, paneRow, paneCol, shift, ctrl, alt):
        app.log.info(u'double click', paneRow, paneCol)
        row = self.view.scrollRow + paneRow
        if row < self.parser.rowCount() and self.parser.rowWidth(row):
            self.selectWordAt(row, self.view.scrollCol + paneCol)

    def mouseMoved(self, paneRow, paneCol, shift, ctrl, alt):
        app.log.info(u' mouseMoved', paneRow, paneCol, shift, ctrl, alt)
        self.mouseClick(paneRow, paneCol, True, ctrl, alt)

    def mouseRelease(self, paneRow, paneCol, shift, ctrl, alt):
        app.log.info(u' mouse release', paneRow, paneCol)
        if not self.parser.rowCount():
            return
        virtualRow = self.view.scrollRow + paneRow
        rowCount = self.parser.rowCount()
        if virtualRow >= rowCount:
            # Off the bottom of document.
            lastLine = rowCount - 1
            self.cursorMove(lastLine - self.penRow,
                            self.parser.rowWidth(lastLine) - self.penCol)
            return
        row = max(0, min(virtualRow, rowCount))
        col = max(0, self.view.scrollCol + paneCol)
        if self.selectionMode == app.selectable.kSelectionBlock:
            self.cursorMoveAndMark(0, 0, row - self.markerRow,
                                   col - self.markerCol, 0)
            return
        markerRow = 0
        # If not block selection, restrict col to the chars on the line.
        rowWidth = self.parser.rowWidth(row)
        col = min(col, rowWidth)
        # Adjust the marker column delta when the pen and marker positions
        # cross over each other.
        markerCol = 0
        if self.selectionMode == app.selectable.kSelectionLine:
            if self.penRow + 1 == self.markerRow and row > self.penRow:
                markerRow = -1
            elif self.penRow == self.markerRow + 1 and row < self.penRow:
                markerRow = 1
        elif self.selectionMode == app.selectable.kSelectionWord:
            if self.penRow == self.markerRow:
                if row == self.penRow:
                    if self.penCol > self.markerCol and col < self.markerCol:
                        markerCol = 1
                    elif self.penCol < self.markerCol and col >= self.markerCol:
                        markerCol = -1
                else:
                    if (row < self.penRow and self.penCol > self.markerCol):
                        markerCol = 1
                    elif (row > self.penRow and self.penCol < self.markerCol):
                        markerCol = -1
            elif row == self.markerRow:
                if col < self.markerCol and row < self.penRow:
                    markerCol = 1
                elif col >= self.markerCol and row > self.penRow:
                    markerCol = -1
        self.cursorMoveAndMark(row - self.penRow, col - self.penCol, markerRow,
                               markerCol, 0)
        if self.selectionMode == app.selectable.kSelectionLine:
            self.cursorMoveAndMark(*self.extendSelection())
        elif self.selectionMode == app.selectable.kSelectionWord:
            if (self.penRow < self.markerRow or
                (self.penRow == self.markerRow and
                 self.penCol < self.markerCol)):
                self.cursorSelectWordLeft()
            elif paneCol < rowWidth:
                self.cursorSelectWordRight()

    def mouseTripleClick(self, paneRow, paneCol, shift, ctrl, alt):
        app.log.info(u'triple click', paneRow, paneCol)
        self.mouseRelease(paneRow, paneCol, shift, ctrl, alt)
        self.selectLineAt(self.view.scrollRow + paneRow)

    def scrollWindow(self, rows, cols):
        self.cursorMoveScroll(rows, self.cursorColDelta(self.penRow - rows), -1,
                              0)
        self.redo()

    def mouseWheelDown(self, shift, ctrl, alt):
        if not shift:
            self.selectionNone()
        if self.program.prefs.editor[u'naturalScrollDirection']:
            self.scrollUp()
        else:
            self.scrollDown()

    def scrollUp(self):
        if self.view.scrollRow == 0:
            self.setMessage(u'Top of file')
            return
        maxRow = self.view.rows
        cursorDelta = 0
        if self.penRow >= self.view.scrollRow + maxRow - 2:
            cursorDelta = self.view.scrollRow + maxRow - 2 - self.penRow
        self.updateScrollPosition(-1, 0)
        if self.view.hasCaptiveCursor:
            self.cursorMoveScroll(
                cursorDelta, self.cursorColDelta(self.penRow + cursorDelta), 0,
                0)
            self.redo()

    def mouseWheelUp(self, shift, ctrl, alt):
        if not shift:
            self.selectionNone()
        if self.program.prefs.editor[u'naturalScrollDirection']:
            self.scrollDown()
        else:
            self.scrollUp()

    def scrollDown(self):
        maxRow = self.view.rows
        if self.view.scrollRow + maxRow >= self.parser.rowCount():
            self.setMessage(u'Bottom of file')
            return
        cursorDelta = 0
        if self.penRow <= self.view.scrollRow + 1:
            cursorDelta = self.view.scrollRow - self.penRow + 1
        self.updateScrollPosition(1, 0)
        if self.view.hasCaptiveCursor:
            self.cursorMoveScroll(
                cursorDelta, self.cursorColDelta(self.penRow + cursorDelta), 0,
                0)
            self.redo()

    def openFileAtCursor(self):
        """
        Opens the file under cursor.
        """

        def openFile(path):
            textBuffer = self.view.program.bufferManager.loadTextBuffer(path)
            inputWindow = self.view.controller.currentInputWindow()
            inputWindow.setTextBuffer(textBuffer)
            self.changeTo(inputWindow)
            self.setMessage('Opened file {}'.format(path))

        text, linkType = self.parser.grammarTextAt(self.penRow, self.penCol)
        if linkType is None:
            self.setMessage(u"Text is not a recognized file.")
            return
        if linkType in (u"c<", u"c\""):
            # These link types include the outer quotes or brackets.
            text = text[1:-1]
        # Give the raw text a try (current working directory or a full path).
        if os.access(text, os.R_OK):
            return openFile(text)
        # Try the path in the same directory as the current file.
        path = os.path.join(os.path.dirname(self.fullPath), text)
        if os.access(path, os.R_OK):
            return openFile(path)
        # TODO(): try a list of path prefixes. Maybe from project, prefs, build
        # information, or another tool.
        # Ran out of tries.
        self.setMessage(u"No readable file \"{}\"".format(text))

    def nextSelectionMode(self):
        nextMode = self.selectionMode + 1
        nextMode %= app.selectable.kSelectionModeCount
        self.doSelectionMode(nextMode)
        app.log.info(u'nextSelectionMode', self.selectionMode)

    def noOp(self, ignored):
        pass

    def noOpDefault(self, ignored, ignored2=None):
        pass

    def normalize(self):
        self.selectionNone()
        self.findRe = None
        self.view.normalize()

    def parseScreenMaybe(self):
        begin = min(self.parser.fullyParsedToLine, self.upperChangedRow)
        end = self.view.scrollRow + self.view.rows + 1
        if end > begin + 100:
            # Call doParse with an empty range.
            end = begin
        self.doParse(begin, end)

    def parseGrammars(self):
        if not self.view:
            return
        scrollRow = self.view.scrollRow
        # If there is a gap, leave it to the background parsing.
        if (self.parser.fullyParsedToLine < scrollRow or
                self.upperChangedRow < scrollRow):
            return
        end = self.view.scrollRow + self.view.rows + 1
        self.doParse(self.upperChangedRow, end)

    def doSelectionMode(self, mode):
        if self.selectionMode != mode:
            self.redoAddChange((u'm', (0, 0, self.penRow - self.markerRow,
                                       self.penCol - self.markerCol,
                                       mode - self.selectionMode)))
            self.redo()

    def cursorSelectLine(self):
        """This function is used to select the line in which the cursor is in.

        Consecutive calls to this function will select subsequent lines.
        """
        if self.selectionMode != app.selectable.kSelectionLine:
            self.selectionLine()
        self.selectLineAt(self.penRow)

    def selectionAll(self):
        self.doSelectionMode(app.selectable.kSelectionAll)
        self.cursorMoveAndMark(*self.extendSelection())

    def selectionBlock(self):
        self.doSelectionMode(app.selectable.kSelectionBlock)

    def selectionCharacter(self):
        self.doSelectionMode(app.selectable.kSelectionCharacter)

    def selectionLine(self):
        self.doSelectionMode(app.selectable.kSelectionLine)

    def selectionNone(self):
        self.doSelectionMode(app.selectable.kSelectionNone)

    def selectionWord(self):
        self.doSelectionMode(app.selectable.kSelectionWord)

    def selectLineAt(self, row):
        """Adds the line with the specified row to the current selection.

        Args:
          row (int): the specified line of text that you want to select.

        Returns:
          None
        """
        if row >= self.parser.rowCount():
            self.selectionNone()
            return
        if row + 1 < self.parser.rowCount():
            self.cursorMoveAndMark(
                (row + 1) - self.penRow, -self.penCol, 0, -self.markerCol,
                app.selectable.kSelectionLine - self.selectionMode)
        else:
            self.cursorMoveAndMark(
                row - self.penRow,
                self.parser.rowWidth(row) - self.penCol, 0, -self.markerCol,
                app.selectable.kSelectionLine - self.selectionMode)

    def selectWordAt(self, row, col):
        """row and col may be from a mouse click and may not actually land in
        the document text."""
        self.selectText(row, col, 0, app.selectable.kSelectionWord)
        rowWidth = self.parser.rowWidth(row)
        if col < rowWidth:
            self.cursorSelectWordRight()

    def setView(self, view):
        self.view = view

    def toggleShowTips(self):
        self.view.toggleShowTips()

    def splitLine(self):
        """split the line into two at current column."""
        self.redoAddChange((u'n', (1,)))
        self.redo()
        self.updateBasicScrollPosition()

    def swapPenAndMarker(self):
        self.cursorMoveAndMark(
            self.markerRow - self.penRow, self.markerCol - self.penCol,
            self.penRow - self.markerRow, self.penCol - self.markerCol, 0)

    def test(self):
        self.insertPrintable(0x00, None)

    def stripTrailingWhiteSpace(self):
        for i in range(self.parser.rowCount()):
            for found in app.regex.kReEndSpaces.finditer(self.parser.rowText(i)):
                self._performDeleteRange(i, found.regs[0][0], i,
                                         found.regs[0][1])

    def unindent(self):
        if self.selectionMode != app.selectable.kSelectionNone:
            self.unindentLines()
        else:
            indentation = self.program.prefs.editor[u'indentation']
            indentationLength = len(indentation)
            line = self.parser.rowText(self.penRow)
            start = self.penCol - indentationLength
            if indentation == line[start:self.penCol]:
                self.verticalDelete(self.penRow, self.penRow, start,
                                    indentation)

    def unindentLines(self):
        indentation = self.program.prefs.editor[u'indentation']
        indentationLength = len(indentation)
        row = min(self.markerRow, self.penRow)
        endRow = max(self.markerRow, self.penRow)
        # Collect a run of lines that can be unindented as a group.
        begin = 0
        i = 0
        for i in range(endRow + 1 - row):
            line, lineWidth = self.parser.rowTextAndWidth(row + i)
            if (lineWidth < indentationLength or
                    line[:indentationLength] != indentation):
                if begin < i:
                    # There is a run of lines that should be unindented.
                    self.verticalDelete(row + begin, row + i - 1, 0,
                                        indentation)
                # Skip this line (don't unindent).
                begin = i + 1
        if begin <= i:
            # There is one last run of lines that should be unindented.
            self.verticalDelete(row + begin, row + i, 0, indentation)

    def updateScrollPosition(self, scrollRowDelta, scrollColDelta):
        """This function updates the view's scroll position using the optional
        scrollRowDelta and scrollColDelta arguments.

        Args:
          scrollRowDelta (int): The number of rows down to move the view.
          scrollColDelta (int): The number of rows right to move the view.

        Returns:
          None
        """
        self.view.scrollRow += scrollRowDelta
        self.view.scrollCol += scrollColDelta
