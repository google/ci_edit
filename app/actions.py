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

import bisect
import curses.ascii
import difflib
import io
import os
import re
import sys
import time
import traceback

import app.bookmark
import app.clipboard
import app.history
import app.log
import app.mutator
import app.parser
import app.prefs
import app.selectable


class Actions(app.mutator.Mutator):
  """This base class to TextBuffer handles the text manipulation (without
  handling the drawing/rendering of the text)."""
  def __init__(self):
    app.mutator.Mutator.__init__(self)
    self.view = None
    self.isBinary = False
    self.rootGrammar = app.prefs.getGrammar(None)
    self.debugUpperChangedRow = -1
    self.parser = app.parser.Parser()

  def setView(self, view):
    self.view = view

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
        self.redoAddChange(('ds', text))
        self.redo()
      self.selectionNone()

  def performDeleteRange(self, upperRow, upperCol, lowerRow, lowerCol):
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
    self.redoAddChange((
      'dr',
      (upperRow, upperCol, lowerRow, lowerCol),
      self.getText(upperRow, upperCol, lowerRow, lowerCol)))
    self.redo()

  def getBookmarkColor(self):
    """
    Returns a new color by cycling through a predefined
    section of the color palette.

    Args:
      None.

    Returns:
      A color (int) for a new bookmark.
    """
    if app.prefs.startup['numColors'] == 8:
      goodColorIndices = [1, 2, 3, 4, 5]
    else:
      goodColorIndices = [97, 98, 113, 117, 127]
    self.nextBookmarkColorPos = (
        self.nextBookmarkColorPos + 1) % len(goodColorIndices)
    return goodColorIndices[self.nextBookmarkColorPos]

  def dataToBookmark(self):
    """
    Args:
      None.

    Returns:
      A Bookmark object containing its range and the current state of the
      cursor and selection mode. The bookmark is also assigned a color, which
      is used to determine the color of the bookmark's line numbers.
    """
    bookmarkData = {
      'cursor': (self.view.cursorRow, self.view.cursorCol),
      'marker': (self.markerRow, self.markerCol),
      'pen': (self.penRow, self.penCol),
      'selectionMode': self.selectionMode,
      'colorIndex': self.getBookmarkColor()
    }
    upperRow, _, lowerRow, _ = self.startAndEnd()
    return app.bookmark.Bookmark(upperRow, lowerRow, bookmarkData)

  def bookmarkAdd(self):
    """
    Adds a bookmark at the cursor's location. If multiple lines are
    selected, all existing bookmarks in those lines are overwritten
    with the new bookmark.

    Args:
      None.

    Returns:
      None.
    """
    newBookmark = self.dataToBookmark()
    self.bookmarkRemove()
    bisect.insort(self.bookmarks, newBookmark)

  def bookmarkGoto(self, bookmark):
    """
    Goes to the bookmark that is passed in.

    Args:
      bookmark (Bookmark): The bookmark you want to jump to. This object is
                           defined in bookmark.py

    Returns:
      None.
    """
    bookmarkData = bookmark.data
    #cursorRow, cursorCol = bookmarkData['cursor']
    penRow, penCol = bookmarkData['pen']
    markerRow, markerCol = bookmarkData['marker']
    selectionMode = bookmarkData['selectionMode']
    self.cursorMoveAndMark(penRow - self.penRow, penCol - self.penCol,
        markerRow - self.markerRow, markerCol - self.markerCol,
        selectionMode - self.selectionMode)
    self.scrollToOptimalScrollPosition()

  def bookmarkNext(self):
    """
    Goes to the closest bookmark after the cursor.

    Args:
      None.

    Returns:
      None.
    """
    if not len(self.bookmarks):
      self.setMessage("No bookmarks to jump to")
      return
    _, _, lowerRow, _ = self.startAndEnd()
    needle = app.bookmark.Bookmark(lowerRow, float('inf'))
    index = bisect.bisect(self.bookmarks, needle)
    self.bookmarkGoto(self.bookmarks[index % len(self.bookmarks)])

  def bookmarkPrior(self):
    """
    Goes to the closest bookmark before the cursor.

    Args:
      None.

    Returns:
      None.
    """
    if not len(self.bookmarks):
      self.setMessage("No bookmarks to jump to")
      return
    upperRow, _, _, _ = self.startAndEnd()
    needle = app.bookmark.Bookmark(upperRow, upperRow)
    index = bisect.bisect_left(self.bookmarks, needle)
    self.bookmarkGoto(self.bookmarks[index - 1])

  def bookmarkRemove(self):
    """
    Removes bookmarks in all selected lines.

    Args:
      None.

    Returns:
      (boolean) Whether any bookmarks were removed.
    """
    upperRow, _, lowerRow, _ = self.startAndEnd()
    rangeList = self.bookmarks
    needle = app.bookmark.Bookmark(upperRow, lowerRow)
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
      index = (high + low) / 2
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
      line = self.lines[self.penRow]
      change = ('b', line[self.penCol - 1:self.penCol])
      self.redoAddChange(change)
      self.redo()

  def carriageReturn(self):
    self.performDelete()
    self.redoAddChange(('n', 1, self.getCursorMove(1, -self.penCol)))
    self.redo()
    if 1:  # TODO(dschuyler): if indent on CR
      line = self.lines[self.penRow - 1]
      commonIndent = len(app.prefs.editor['indentation'])
      indent = 0
      while indent < len(line) and line[indent] == ' ':
        indent += 1
      if len(line):
        stripped = line.rstrip()
        if stripped and line[-1] in [':', '[', '{']:
          indent += commonIndent
        # Good idea or bad idea?
        #elif indent >= 2 and line.lstrip()[:6] == 'return':
        #  indent -= commonIndent
        elif line.count('(') > line.count(')'):
          indent += commonIndent * 2
      if indent:
        self.redoAddChange(('i', ' ' * indent));
        self.redo()
    self.updateBasicScrollPosition()

  def cursorColDelta(self, toRow):
    if toRow >= len(self.lines):
      return
    lineLen = len(self.lines[toRow])
    if self.goalCol <= lineLen:
      return self.goalCol - self.penCol
    return lineLen - self.penCol

  def cursorDown(self):
    self.selectionNone()
    self.cursorMoveDown()

  def cursorDownScroll(self):
    self.selectionNone()
    self.scrollDown()

  def cursorLeft(self):
    self.selectionNone()
    self.cursorMoveLeft()

  def getCursorMove(self, rowDelta, colDelta):
    return self.getCursorMoveAndMark(rowDelta, colDelta, 0, 0, 0)

  def cursorMove(self, rowDelta, colDelta):
    self.cursorMoveAndMark(rowDelta, colDelta, 0, 0, 0)

  def getCursorMoveAndMark(self, rowDelta, colDelta, markRowDelta,
      markColDelta, selectionModeDelta):
    if self.penCol + colDelta < 0:  # Catch cursor at beginning of line.
      colDelta = -self.penCol
    self.goalCol = self.penCol + colDelta
    return ('m', (rowDelta, colDelta,
        markRowDelta, markColDelta, selectionModeDelta))

  def cursorMoveAndMark(self, rowDelta, colDelta, markRowDelta,
      markColDelta, selectionModeDelta):
    change = self.getCursorMoveAndMark(rowDelta, colDelta, markRowDelta,
                                       markColDelta, selectionModeDelta)
    self.redoAddChange(change)
    self.redo()
    if self.selectionMode != app.selectable.kSelectionNone:
      charCount, lineCount = self.countSelected()
      self.setMessage('%d characters (%d lines) selected' % (charCount,
          lineCount))

  def cursorMoveScroll(self, rowDelta, colDelta,
      scrollRowDelta, scrollColDelta):
    self.updateScrollPosition(scrollRowDelta, scrollColDelta)
    self.redoAddChange(('m', (rowDelta, colDelta, 0, 0, 0)))

  def cursorMoveDown(self):
    if self.penRow == len(self.lines) - 1:
      self.setMessage('Bottom of file')
      return
    savedGoal = self.goalCol
    self.cursorMove(1, self.cursorColDelta(self.penRow + 1))
    self.goalCol = savedGoal

  def cursorMoveLeft(self):
    if self.penCol > 0:
      self.cursorMove(0, -1)
    elif self.penRow > 0:
      self.cursorMove(-1, len(self.lines[self.penRow - 1]))

  def cursorMoveRight(self):
    if not self.lines:
      return
    if self.penCol < len(self.lines[self.penRow]):
      self.cursorMove(0, 1)
    elif self.penRow + 1 < len(self.lines):
      self.cursorMove(1, -len(self.lines[self.penRow]))
    else:
      self.setMessage('Bottom of file')

  def cursorMoveUp(self):
    if self.penRow <= 0:
      self.setMessage('Top of file')
      return
    savedGoal = self.goalCol
    lineLen = len(self.lines[self.penRow - 1])
    if self.goalCol <= lineLen:
      self.cursorMove(-1, self.goalCol - self.penCol)
    else:
      self.cursorMove(-1, lineLen - self.penCol)
    self.goalCol = savedGoal

  def cursorMoveSubwordLeft(self):
    self.doCursorMoveLeftTo(app.selectable.kReSubwordBoundaryRvr)

  def cursorMoveSubwordRight(self):
    self.doCursorMoveRightTo(app.selectable.kReSubwordBoundaryFwd)

  def cursorMoveTo(self, row, col):
    cursorRow = min(max(row, 0), len(self.lines)-1)
    self.cursorMove(cursorRow - self.penRow, col - self.penCol)

  def cursorMoveWordLeft(self):
    self.doCursorMoveLeftTo(app.selectable.kReWordBoundary)

  def cursorMoveWordRight(self):
    self.doCursorMoveRightTo(app.selectable.kReWordBoundary)

  def doCursorMoveLeftTo(self, boundary):
    if self.penCol > 0:
      line = self.lines[self.penRow]
      pos = self.penCol
      for segment in re.finditer(boundary, line):
        if segment.start() < pos <= segment.end():
          pos = segment.start()
          break
      self.cursorMove(0, pos - self.penCol)
    elif self.penRow > 0:
      self.cursorMove(-1, len(self.lines[self.penRow - 1]))

  def doCursorMoveRightTo(self, boundary):
    if not self.lines:
      return
    if self.penCol < len(self.lines[self.penRow]):
      line = self.lines[self.penRow]
      pos = self.penCol
      for segment in re.finditer(boundary, line):
        if segment.start() <= pos < segment.end():
          pos = segment.end()
          break
      self.cursorMove(0, pos - self.penCol)
    elif self.penRow + 1 < len(self.lines):
      self.cursorMove(1, -len(self.lines[self.penRow]))

  def cursorRight(self):
    self.selectionNone()
    self.cursorMoveRight()

  def cursorSelectDown(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveDown()

  def cursorSelectDownScroll(self):
    """Move the line below the selection to above the selection."""
    upperRow, _, lowerRow, _ = self.startAndEnd()
    if lowerRow + 1 >= len(self.lines):
      return
    begin = lowerRow + 1
    end = lowerRow + 2
    to = upperRow
    self.redoAddChange(('ml', (begin, end, to)))
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
    self.cursorMoveWordLeft()
    self.cursorMoveAndMark(*self.extendSelection())

  def cursorSelectWordRight(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveWordRight()
    self.cursorMoveAndMark(*self.extendSelection())

  def cursorSelectUp(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveUp()

  def cursorSelectUpScroll(self):
    """Move the line above the selection to below the selection."""
    upperRow, _, lowerRow, _ = self.startAndEnd()
    if upperRow == 0:
      return
    begin = upperRow - 1
    end = upperRow
    to = lowerRow + 1
    self.redoAddChange(('ml', (begin, end, to)))
    self.redo()

  def cursorEndOfLine(self):
    lineLen = len(self.lines[self.penRow])
    self.cursorMove(0, lineLen - self.penCol)

  def cursorSelectToStartOfLine(self):
    self.selectionCharacter()
    self.cursorStartOfLine()

  def cursorSelectToEndOfLine(self):
    self.selectionCharacter()
    self.cursorEndOfLine()

  def __cursorPageDown(self):
    """
    Moves the view and cursor down by a page or stops
    at the bottom of the document if there is less than
    a page left.

    Args:
      None.

    Returns:
      None.
    """
    if self.penRow == len(self.lines) - 1:
      self.setMessage('Bottom of file')
      return
    maxRow = self.view.rows
    penRowDelta = maxRow
    scrollRowDelta = maxRow
    numLines = len(self.lines)
    if self.penRow + maxRow >= numLines:
      penRowDelta = numLines - self.penRow - 1
    if numLines <= maxRow:
      scrollRowDelta = -self.view.scrollRow
    elif numLines <= 2 * maxRow + self.view.scrollRow:
      scrollRowDelta = numLines - self.view.scrollRow - maxRow
    self.cursorMoveScroll(penRowDelta,
        self.cursorColDelta(self.penRow + penRowDelta), scrollRowDelta, 0)
    self.redo()

  def __cursorPageUp(self):
    """
    Moves the view and cursor up by a page or stops
    at the top of the document if there is less than
    a page left.

    Args:
      None.

    Returns:
      None.
    """
    if self.penRow == 0:
      self.setMessage('Top of file')
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
    """
    Performs a page down. This function does not
    select any text and removes all existing highlights.

    Args:
      None.

    Returns:
      None.
    """
    self.selectionNone()
    self.__cursorPageDown()

  def cursorSelectNonePageUp(self):
    """
    Performs a page up. This function does not
    select any text and removes all existing highlights.

    Args:
      None.

    Returns:
      None.
    """
    self.selectionNone()
    self.__cursorPageUp()

  def cursorSelectCharacterPageDown(self):
    """
    Performs a page down. This function selects
    all characters between the previous and current
    cursor position.

    Args:
      None.

    Returns:
      None.
    """
    self.selectionCharacter()
    self.__cursorPageDown()

  def cursorSelectCharacterPageUp(self):
    """
    Performs a page up. This function selects
    all characters between the previous and current
    cursor position.

    Args:
      None.

    Returns:
      None.
    """
    self.selectionCharacter()
    self.__cursorPageUp()

  def cursorSelectBlockPageDown(self):
    """
    Performs a page down. This function sets
    the selection mode to "block."

    Args:
      None.

    Returns:
      None.
    """
    self.selectionBlock()
    self.__cursorPageDown()

  def cursorSelectBlockPageUp(self):
    """
    Performs a page up. This function sets
    the selection mode to "block."

    Args:
      None.

    Returns:
      None.
    """
    self.selectionBlock()
    self.__cursorPageUp()

  def cursorScrollToMiddle(self):
    maxRow = self.view.rows
    rowDelta = min(max(0, len(self.lines) - maxRow),
                   max(0, self.penRow - maxRow / 2)) - self.view.scrollRow
    self.cursorMoveScroll(0, 0, rowDelta, 0)

  def cursorStartOfLine(self):
    self.cursorMove(0, -self.penCol)

  def cursorUp(self):
    self.selectionNone()
    self.cursorMoveUp()

  def cursorUpScroll(self):
    self.selectionNone()
    self.scrollUp()

  def delCh(self):
    line = self.lines[self.penRow]
    change = ('d', line[self.penCol:self.penCol + 1])
    self.redoAddChange(change)
    self.redo()

  def delete(self):
    """Delete character to right of pen i.e. Del key."""
    if self.selectionMode != app.selectable.kSelectionNone:
      self.performDelete()
    elif self.penCol == len(self.lines[self.penRow]):
      if self.penRow + 1 < len(self.lines):
        self.joinLines()
    else:
      self.delCh()

  def deleteToEndOfLine(self):
    line = self.lines[self.penRow]
    if self.penCol == len(self.lines[self.penRow]):
      if self.penRow + 1 < len(self.lines):
        self.joinLines()
    else:
      change = ('d', line[self.penCol:])
      self.redoAddChange(change)
      self.redo()

  def editCopy(self):
    text = self.getSelectedText()
    if len(text):
      data = self.doLinesToData(text)
      app.clipboard.copy(data)
      if len(text) == 1:
        self.setMessage('copied %d characters' % len(text[0]))
      else:
        self.setMessage('copied %d lines' % (len(text),))

  def editCut(self):
    self.editCopy()
    self.performDelete()

  def editPaste(self):
    data = app.clipboard.paste()
    if data is not None:
      self.editPasteData(data)
    else:
      app.log.info('clipboard empty')

  def editPasteData(self, data):
    self.editPasteLines(tuple(self.doDataToLines(data)))

  def editPasteLines(self, clip):
    if self.selectionMode != app.selectable.kSelectionNone:
      self.performDelete()
    self.redoAddChange(('v', clip))
    self.redo()
    rowDelta = len(clip) - 1
    if rowDelta == 0:
      endCol = self.penCol + len(clip[0])
    else:
      endCol = len(clip[-1])
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

  def doLinesToBinaryData(self, lines):
    # TODO(dschuyler): convert lines to binary data.
    return ''

  def doLinesToData(self, lines):
    def encode(line):
      return chr(int(line.groups()[0], 16))
    return re.sub('\x01([0-9a-fA-F][0-9a-fA-F])', encode, "\n".join(lines))

  def doBinaryDataToLines(self, data):
    # TODO(dschuyler): convert binary data to lines.
    return ["Binary file.", "Editing this text won't change the file."]

  def doDataToLines(self, data):
    # Performance: in a 1000 line test it appears fastest to do some simple
    # .replace() calls to minimize the number of calls to parse().
    data = data.replace('\r\n', '\n')
    data = data.replace('\r', '\n')
    data = data.replace('\t', ' ' * 8)
    def parse(sre):
      return "\x01%02x" % ord(sre.groups()[0])
    #data = re.sub('([\0-\x09\x0b-\x1f\x7f-\xff])', parse, data)
    data = re.sub('([\0-\x09\x0b-\x1f])', parse, data)
    return data.split('\n')

  def dataToLines(self):
    if self.isBinary:
      self.lines = self.doBinaryDataToLines(self.data)
    else:
      self.lines = self.doDataToLines(self.data)

  def fileFilter(self, data):
    self.data = data
    self.dataToLines()
    self.upperChangedRow = 0
    self.savedAtRedoIndex = self.redoIndex

  def fileLoad(self):
    app.log.info('fileLoad', self.fullPath)
    inputFile = None
    self.isReadOnly = (os.path.isfile(self.fullPath) and
        not os.access(self.fullPath, os.W_OK))
    if not os.path.exists(self.fullPath):
      self.setMessage('Creating new file')
    else:
      try:
        inputFile = io.open(self.fullPath)
        data = inputFile.read()
        # Hacky detection of binary files.
        unicode(data).decode('utf-8')
        self.fileEncoding = inputFile.encoding
        self.setMessage('Opened existing file')
        self.isBinary = False
      except Exception:
        try:
          inputFile = io.open(self.fullPath, 'rb')
          data = inputFile.read()
          self.fileEncoding = None
          self.isBinary = True
          self.setMessage('Opened file as a binary file')
        except Exception:
          app.log.info('error opening file', self.fullPath)
          self.setMessage('error opening file', self.fullPath)
          return
      self.fileStat = os.stat(self.fullPath)
    self.relativePath = os.path.relpath(self.fullPath, os.getcwd())
    app.log.info('fullPath', self.fullPath)
    app.log.info('cwd', os.getcwd())
    app.log.info('relativePath', self.relativePath)
    if inputFile:
      self.fileFilter(data)
      inputFile.close()
    else:
      self.data = unicode("")
    self.fileExtension = os.path.splitext(self.fullPath)[1]
    self.rootGrammar = app.prefs.getGrammar(self.fileExtension)
    self.parseGrammars()
    self.dataToLines()

    # Restore all user history.
    app.history.loadUserHistory(self.fullPath)
    self.restoreUserHistory()

  def replaceLines(self, clip):
    self.view.textBuffer.selectionAll()
    self.view.textBuffer.editPasteLines(tuple(clip))

  def restoreUserHistory(self):
    """
    This function restores all stored history of the file into the TextBuffer
    object. If there does not exist a stored history of the file, it will
    initialize the variables to default values.

    Args:
      None.

    Returns:
      None.
    """
    # Restore the file history.
    self.fileHistory = app.history.getFileHistory(self.fullPath, self.data)

    # Restore all positions and values of variables.
    self.view.cursorRow, self.view.cursorCol = self.fileHistory.setdefault(
        'cursor', (0, 0))
    self.penRow, self.penCol = self.fileHistory.setdefault('pen', (0, 0))
    self.view.scrollRow, self.view.scrollCol =  self.fileHistory.setdefault(
        'scroll', (0, 0))
    self.doSelectionMode(self.fileHistory.setdefault('selectionMode',
        app.selectable.kSelectionNone))
    self.markerRow, self.markerCol = self.fileHistory.setdefault('marker',
        (0, 0))
    if app.prefs.editor['saveUndo']:
      self.redoChain = self.fileHistory.setdefault('redoChainCompound', [])
      self.savedAtRedoIndex = self.fileHistory.setdefault('savedAtRedoIndexCompound', 0)
      self.redoIndex = self.savedAtRedoIndex
      self.oldRedoIndex = self.savedAtRedoIndex

    # Restore file bookmarks
    self.bookmarks = self.fileHistory.setdefault('bookmarks', [])

    # Store the file's info.
    self.lastChecksum, self.lastFileSize = app.history.getFileInfo(
        self.fullPath)

  def updateBasicScrollPosition(self):
    """
    Sets scrollRow, scrollCol to the closest values that the view's position
    must be in order to see the cursor.

    Args:
      None.

    Returns:
      None.
    """
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
    """
    Args:
      None.

    Returns:
      A tuple of (scrollRow, scrollCol) representing where
      the view's optimal position should be.
    """
    top, left, bottom, right = self.startAndEnd()
    # Row.
    maxRows = self.view.rows
    scrollRow = self.view.scrollRow
    height = bottom - top + 1
    extraRows = maxRows - height
    if extraRows > 0:
      optimalRowRatio = app.prefs.editor['optimalCursorRow']
      scrollRow = max(0, min(len(self.lines) - 1,
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
        optimalColRatio = app.prefs.editor['optimalCursorCol']
        scrollCol = max(0, min(right,
          left - int(optimalColRatio * (maxCols - 1))))
    else:
      scrollCol = left
    self.view.scrollRow = scrollRow
    self.view.scrollCol = scrollCol

  def isSelectionInView(self):
    """
    If there is no selection, checks if the cursor is in the view.

    Args:
      None.

    Returns:
      True if selection is in view. Otherwise, False.
    """
    return self.isInView(*self.startAndEnd())

  def isInView(self, top, left, bottom, right):
    """
    Returns:
      True if selection is in view. Otherwise, False.
    """
    horizontally = (self.view.scrollCol <= left and
            right < self.view.scrollCol + self.view.cols)
    vertically = (self.view.scrollRow <= top and
            bottom < self.view.scrollRow + self.view.rows)
    return horizontally and vertically

  def linesToData(self):
    if self.isBinary:
      # TODO(dschuyler): convert binary data.
      pass #self.data = self.doLinesToBinaryData(self.lines)
    else:
      self.data = self.doLinesToData(self.lines)

  def fileWrite(self):
    # Preload the message with an error that should be overwritten.
    self.setMessage('Error saving file')
    self.isReadOnly = not os.access(self.fullPath, os.W_OK)
    try:
      try:
        if app.prefs.editor['onSaveStripTrailingSpaces']:
          self.stripTrailingWhiteSpace()
          self.compoundChangePush()
        # Save user data that applies to read-only files into history.
        self.fileHistory['pen'] = (self.penRow, self.penCol)
        self.fileHistory['cursor'] = (self.view.cursorRow, self.view.cursorCol)
        self.fileHistory['scroll'] = (self.view.scrollRow, self.view.scrollCol)
        self.fileHistory['marker'] = (self.markerRow, self.markerCol)
        self.fileHistory['selectionMode'] = self.selectionMode
        self.fileHistory['bookmarks'] = self.bookmarks
        self.linesToData()
        if self.fileEncoding is None:
          outputFile = io.open(self.fullPath, 'w+', encoding='UTF-8')
        else:
          outputFile = io.open(self.fullPath, 'w+', encoding=self.fileEncoding)
        outputFile.seek(0)
        outputFile.truncate()
        outputFile.write(self.data)
        outputFile.close()
        # Save user data that applies to writable files.
        self.savedAtRedoIndex = self.redoIndex
        if app.prefs.editor['saveUndo']:
          self.fileHistory['redoChainCompound'] = self.redoChain
          self.fileHistory['savedAtRedoIndexCompound'] = self.savedAtRedoIndex
        app.history.saveUserHistory((self.fullPath, self.lastChecksum,
            self.lastFileSize), self.fileHistory)
        # Store the file's new info
        self.lastChecksum, self.lastFileSize = app.history.getFileInfo(
            self.fullPath)
        self.fileStat = os.stat(self.fullPath)
        # If we're writing this file for the first time, self.isReadOnly will
        # still be True (from when it didn't exist).
        self.isReadOnly = False
        self.setMessage('File saved')
      except Exception as e:
        color = app.color.get('status_line_error')
        if self.isReadOnly:
          self.setMessage("Permission error. Try modifying in sudo mode.",
                          color=color)
        else:
          self.setMessage(
              'Error writing file. The file did not save properly.',
              color=color)
        app.log.error('error writing file')
        app.log.exception(e)
    except Exception:
      app.log.info('except had exception')

  def selectText(self, row, col, length, mode):
    row = max(0, min(row, len(self.lines) - 1))
    col = max(0, min(col, len(self.lines[row])))
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
    app.log.info('find', searchFor, direction)
    if not len(searchFor):
      self.findRe = None
      self.doSelectionMode(app.selectable.kSelectionNone)
      return
    # The saved re is also used for highlighting.
    ignoreCaseFlag = (app.prefs.editor.get('findIgnoreCase') and
                      re.IGNORECASE or 0)
    self.findRe = re.compile('()'+searchFor, ignoreCaseFlag)
    self.findBackRe = re.compile('(.*)'+searchFor, ignoreCaseFlag)
    self.findCurrentPattern(direction)

  def findPlainText(self, text):
    searchFor = re.escape(text)
    self.findRe = re.compile('()^' + searchFor)
    self.findCurrentPattern(0)

  def findReplaceFlags(self, tokens):
    """Map letters in |tokens| to re flags."""
    flags = re.MULTILINE
    if 'i' in tokens:
      flags |= re.IGNORECASE
    if 'l' in tokens:
      # Affects \w, \W, \b, \B.
      flags |= re.LOCALE
    if 'm' in tokens:
      # Affects ^, $.
      flags |= re.MULTILINE
    if 's' in tokens:
      # Affects ..
      flags |= re.DOTALL
    if 'x' in tokens:
      # Affects whitespace and # comments.
      flags |= re.VERBOSE
    if 'u' in tokens:
      # Affects \w, \W, \b, \B.
      flags |= re.UNICODE
    if 0:
      tokens = re.sub('[ilmsxu]', '', tokens)
      if len(tokens):
        self.setMessage('unknown regex flags '+tokens)
    return flags

  def findReplace(self, cmd):
    if not len(cmd):
      return
    separator = cmd[0]
    splitCmd = cmd.split(separator, 3)
    if len(splitCmd) < 4:
      self.setMessage('An exchange needs three ' + separator + ' separators')
      return
    _, find, replace, flags = splitCmd
    self.linesToData()
    data = self.findReplaceText(find, replace, flags, self.data)
    self.applyDocumentUpdate(data)

  def findReplaceText(self, find, replace, flags, input):
    flags = self.findReplaceFlags(flags)
    return re.sub(find, replace, input, flags=flags)

  def applyDocumentUpdate(self, data):
    diff = difflib.ndiff(self.lines, self.doDataToLines(data))
    ndiff = []
    counter = 0
    for i in diff:
      if i[0] != ' ':
        if counter:
          ndiff.append(counter)
          counter = 0
        if i[0] in ['+', '-']:
          ndiff.append(i)
      else:
        counter += 1
    if counter:
      ndiff.append(counter)
    if len(ndiff) == 1 and type(ndiff[0]) is type(0):
      # Nothing was changed. The only entry is a 'skip these lines'
      self.setMessage('No matches found')
      return
    ndiff = tuple(ndiff)
    if 0:
      for i in ndiff:
        app.log.info(i)
    self.redoAddChange(('ld', ndiff))
    self.redo()

  def findCurrentPattern(self, direction):
    localRe = self.findRe
    offset = self.penCol + direction
    if direction < 0:
      localRe = self.findBackRe
    if localRe is None:
      app.log.info('localRe is None')
      return
    # Check part of current line.
    text = self.lines[self.penRow]
    if direction >= 0:
      text = text[offset:]
    else:
      text = text[:self.penCol]
      offset = 0
    #app.log.info('find() searching', repr(text))
    found = localRe.search(text)
    rowFound = self.penRow
    if not found:
      offset = 0
      # To end of file.
      if direction >= 0:
        theRange = range(self.penRow + 1, len(self.lines))
      else:
        theRange = range(self.penRow - 1, -1, -1)
      for i in theRange:
        found = localRe.search(self.lines[i])
        if found:
          if 0:
            for k in found.regs:
              app.log.info('AAA', k[0], k[1])
            app.log.info('b found on line', i, repr(found))
          rowFound = i
          break
      if not found:
        # Wrap around to the opposite side of the file.
        self.setMessage('Find wrapped around.')
        if direction >= 0:
          theRange = range(self.penRow)
        else:
          theRange = range(len(self.lines) - 1, self.penRow, -1)
        for i in theRange:
          found = localRe.search(self.lines[i])
          if found:
            rowFound = i
            break
        if not found:
          # Check the rest of the current line
          if direction >= 0:
            text = self.lines[self.penRow]
          else:
            text = self.lines[self.penRow][self.penCol:]
            offset = self.penCol
          found = localRe.search(text)
          rowFound = self.penRow
    if found:
      #app.log.info('c found on line', rowFound, repr(found))
      start = found.regs[1][1]
      end = found.regs[0][1]
      self.selectText(rowFound, offset + start, end - start,
                      app.selectable.kSelectionCharacter)
      return
    app.log.info('find not found')
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
    indentation = app.prefs.editor['indentation']
    indentationLength = len(indentation)
    if self.selectionMode == app.selectable.kSelectionNone:
      self.verticalInsert(self.penRow, self.penRow, self.penCol, indentation)
    else:
      self.indentLines()
    self.cursorMoveAndMark(0, indentationLength, 0, indentationLength, 0)

  def indentLines(self):
    """
    Indents all selected lines. Do not use for when the selection mode
    is kSelectionNone since markerRow/markerCol currently do not get
    updated alongside penRow/penCol.
    """
    col = 0
    row = min(self.markerRow, self.penRow)
    endRow = max(self.markerRow, self.penRow)
    indentation = app.prefs.editor['indentation']
    self.verticalInsert(row, endRow, col, indentation)

  def verticalDelete(self, row, endRow, col, text):
    self.redoAddChange(('vd', (text, row, endRow, col)))
    self.redo()
    if row <= self.markerRow <= endRow:
      self.cursorMoveAndMark(0, 0, 0, -len(text), 0)
    if row <= self.penRow <= endRow:
      self.cursorMoveAndMark(0, -len(text), 0, 0, 0)

  def verticalInsert(self, row, endRow, col, text):
    self.redoAddChange(('vi', (text, row, endRow, col)))
    self.redo()

  def insert(self, text):
    self.performDelete()
    self.redoAddChange(('i', text))
    self.redo()
    self.updateBasicScrollPosition()

  def insertPrintable(self, ch, meta):
    #app.log.info(ch, meta)
    if curses.ascii.isprint(ch):
      self.insert(unichr(ch))
    elif ch is app.curses_util.BRACKETED_PASTE:
      self.editPasteData(meta.decode('utf-8'))
    elif ch is app.curses_util.UNICODE_INPUT:
      self.insert(meta)

  def joinLines(self):
    """join the next line onto the current line."""
    self.redoAddChange(('j',))
    self.redo()

  def markerPlace(self):
    self.redoAddChange(('m', (0, 0, self.penRow - self.markerRow,
        self.penCol - self.markerCol, 0)))
    self.redo()

  def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
    if 0:
      if ctrl:
        app.log.info('click at', paneRow, paneCol)
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
    app.log.info('double click', paneRow, paneCol)
    row = self.view.scrollRow + paneRow
    if row < len(self.lines) and len(self.lines[row]):
      self.selectWordAt(row, self.view.scrollCol + paneCol)

  def mouseMoved(self, paneRow, paneCol, shift, ctrl, alt):
    app.log.info(' mouseMoved', paneRow, paneCol, shift, ctrl, alt)
    self.mouseClick(paneRow, paneCol, True, ctrl, alt)

  def mouseRelease(self, paneRow, paneCol, shift, ctrl, alt):
    app.log.info(' mouse release', paneRow, paneCol)
    if not self.lines:
      return
    virtualRow = self.view.scrollRow + paneRow
    if virtualRow >= len(self.lines):
      # Off the bottom of document.
      lastLine = len(self.lines) - 1
      self.cursorMove(lastLine - self.penRow,
          len(self.lines[lastLine]) - self.penCol)
      return
    row = max(0, min(virtualRow, len(self.lines)))
    col = max(0, self.view.scrollCol + paneCol)
    if self.selectionMode == app.selectable.kSelectionBlock:
      self.cursorMoveAndMark(0, 0, row - self.markerRow, col - self.markerCol,
          0)
      return
    markerRow = 0
    # If not block selection, restrict col to the chars on the line.
    col = min(col, len(self.lines[row]))
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
          if (row < self.penRow and
              self.penCol > self.markerCol):
            markerCol = 1
          elif (row > self.penRow and
              self.penCol < self.markerCol):
            markerCol = -1
      elif row == self.markerRow:
        if col < self.markerCol and row < self.penRow:
          markerCol = 1
        elif col >= self.markerCol and row > self.penRow:
          markerCol = -1
    self.cursorMoveAndMark(row - self.penRow, col - self.penCol,
        markerRow, markerCol, 0)
    if self.selectionMode == app.selectable.kSelectionLine:
      self.cursorMoveAndMark(*self.extendSelection())
    elif self.selectionMode == app.selectable.kSelectionWord:
      if (self.penRow < self.markerRow or
         (self.penRow == self.markerRow and
          self.penCol < self.markerCol)):
        self.cursorSelectWordLeft()
      elif paneCol < len(self.lines[row]):
        self.cursorSelectWordRight()

  def mouseTripleClick(self, paneRow, paneCol, shift, ctrl, alt):
    app.log.info('triple click', paneRow, paneCol)
    self.mouseRelease(paneRow, paneCol, shift, ctrl, alt)
    self.selectLineAt(self.view.scrollRow + paneRow)

  def scrollWindow(self, rows, cols):
    self.cursorMoveScroll(rows, self.cursorColDelta(self.penRow - rows), -1, 0)
    self.redo()

  def mouseWheelDown(self, shift, ctrl, alt):
    if not shift:
      self.selectionNone()
    if app.prefs.editor['naturalScrollDirection']:
      self.scrollUp()
    else:
      self.scrollDown()

  def scrollUp(self):
    if self.view.scrollRow == 0:
      self.setMessage('Top of file')
      return
    maxRow = self.view.rows
    cursorDelta = 0
    if self.penRow >= self.view.scrollRow + maxRow - 2:
      cursorDelta = self.view.scrollRow + maxRow - 2 - self.penRow
    self.updateScrollPosition(-1, 0)
    if self.view.hasCaptiveCursor:
      self.cursorMoveScroll(cursorDelta,
          self.cursorColDelta(self.penRow + cursorDelta), 0, 0)
      self.redo()

  def mouseWheelUp(self, shift, ctrl, alt):
    if not shift:
      self.selectionNone()
    if app.prefs.editor['naturalScrollDirection']:
      self.scrollDown()
    else:
      self.scrollUp()

  def scrollDown(self):
    maxRow = self.view.rows
    if self.view.scrollRow + maxRow >= len(self.lines):
      self.setMessage('Bottom of file')
      return
    cursorDelta = 0
    if self.penRow <= self.view.scrollRow + 1:
      cursorDelta = self.view.scrollRow - self.penRow + 1
    self.updateScrollPosition(1, 0)
    if self.view.hasCaptiveCursor:
      self.cursorMoveScroll(cursorDelta,
          self.cursorColDelta(self.penRow + cursorDelta), 0, 0)
      self.redo()

  def nextSelectionMode(self):
    nextMode = self.selectionMode + 1
    nextMode %= app.selectable.kSelectionModeCount
    self.doSelectionMode(nextMode)
    app.log.info('nextSelectionMode', self.selectionMode)

  def noOp(self, ignored):
    pass

  def noOpDefault(self, ignored, ignored2=None):
    pass

  def normalize(self):
    self.selectionNone()
    self.findRe = None
    self.view.normalize()

  def doParse(self, begin, end):
    self.linesToData()
    self.parser.parse(self.data, self.rootGrammar, begin, end)
    self.upperChangedRow = len(self.parser.rows)

  def parseDocument(self):
    begin = min(len(self.parser.rows), self.upperChangedRow)
    end = len(self.lines)
    self.doParse(begin, end)

  def parseScreenMaybe(self):
    begin = min(len(self.parser.rows), self.upperChangedRow)
    end = self.view.scrollRow + self.view.rows + 1
    if end > begin + 100:
      # Call doParse with an empty range.
      end = begin
    self.doParse(begin, end)

  def parseGrammars(self):
    if not self.parser:
      self.parser = app.parser.Parser()
    scrollRow = self.view.scrollRow
    # If there is a gap, leave it to the background parsing.
    if self.parser.rows < scrollRow or self.upperChangedRow < scrollRow:
      return
    end = self.view.scrollRow + self.view.rows + 1
    # Reset the self.data to get recent changes in self.lines.
    self.linesToData()
    start = time.time()
    self.parser.parse(self.data, self.rootGrammar,
        self.upperChangedRow, end)
    self.debugUpperChangedRow = self.upperChangedRow
    self.upperChangedRow = len(self.lines)
    self.parserTime = time.time() - start

  def doSelectionMode(self, mode):
    if self.selectionMode != mode:
      self.redoAddChange(('m', (0, 0,
          self.penRow - self.markerRow,
          self.penCol - self.markerCol,
          mode - self.selectionMode)))
      self.redo()

  def cursorSelectLine(self):
    """
      This function is used to select the line in which the cursor is in.
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
    """
    Adds the line with the specified row to the current selection.

    Args:
      row (int): the specified line of text that you want to select.

    Returns:
      None
    """
    if row >= len(self.lines):
      self.selectionNone()
      return
    if row + 1 < len(self.lines):
      self.cursorMoveAndMark((row + 1) - self.penRow, -self.penCol,
          0, -self.markerCol,
          app.selectable.kSelectionLine - self.selectionMode)
    else:
      self.cursorMoveAndMark(row - self.penRow,
          len(self.lines[row]) - self.penCol,
          0, -self.markerCol,
          app.selectable.kSelectionLine - self.selectionMode)

  def selectWordAt(self, row, col):
    """row and col may be from a mouse click and may not actually land in the
        document text."""
    self.selectText(row, col, 0, app.selectable.kSelectionWord)
    if col < len(self.lines[self.penRow]):
      self.cursorSelectWordRight()

  def toggleShowTips(self):
    self.view.toggleShowTips()

  def splitLine(self):
    """split the line into two at current column."""
    self.redoAddChange(('n', (1,)))
    self.redo()
    self.updateBasicScrollPosition()

  def swapPenAndMarker(self):
    self.cursorMoveAndMark(self.markerRow - self.penRow,
        self.markerCol - self.penCol,
        self.penRow - self.markerRow,
        self.penCol - self.markerCol, 0)

  def test(self):
    self.insertPrintable(0x00, None)

  def stripTrailingWhiteSpace(self):
    for i in range(len(self.lines)):
      for found in app.selectable.kReEndSpaces.finditer(self.lines[i]):
        self.performDeleteRange(i, found.regs[0][0], i, found.regs[0][1])

  def unindent(self):
    if self.selectionMode != app.selectable.kSelectionNone:
      self.unindentLines()
    else:
      indentation = app.prefs.editor['indentation']
      indentationLength = len(indentation)
      line = self.lines[self.penRow]
      start = self.penCol - indentationLength
      if indentation == line[start:self.penCol]:
        self.verticalDelete(self.penRow, self.penRow, start, indentation)

  def unindentLines(self):
    indentation = app.prefs.editor['indentation']
    indentationLength = len(indentation)
    row = min(self.markerRow, self.penRow)
    endRow = max(self.markerRow, self.penRow)
    begin = 0
    for i, line in enumerate(self.lines[row:endRow + 1]):
      if (len(line) < indentationLength or
          line[:indentationLength] != indentation):
        if begin < i:
          self.verticalDelete(row + begin, row + i - 1, 0, indentation)
        begin = i + 1
    if begin <= i:
      self.verticalDelete(row + begin, row + i, 0, indentation)

  def updateScrollPosition(self, scrollRowDelta, scrollColDelta):
    """
    This function updates the view's scroll position using the optional
    scrollRowDelta and scrollColDelta arguments.

    Args:
      scrollRowDelta (int): The number of rows down to move the view.
      scrollColDelta (int): The number of rows right to move the view.

    Returns:
      None
    """
    self.view.scrollRow += scrollRowDelta
    self.view.scrollCol += scrollColDelta
