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

import app.bookmarks
import app.buffer_manager
import app.clipboard
import app.log
import app.history
import app.mutator
import app.parser
import app.prefs
import app.selectable
import curses.ascii
import difflib
import os
import re
import sys
import time
import traceback


class Actions(app.mutator.Mutator):
  """This base class to TextBuffer handles the text manipulation (without
  handling the drawing/rendering of the text)."""
  def __init__(self):
    app.mutator.Mutator.__init__(self)
    self.view = None
    self.rootGrammar = app.prefs.getGrammar(None)
    self.__skipUpdateScroll = False
    self.__skipCursorScroll = False

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
          self.redo()
        elif (self.penRow > self.markerRow or
            (self.penRow == self.markerRow and
            self.penCol > self.markerCol)):
          self.swapPenAndMarker()
        self.redoAddChange(('ds', text))
        self.redo()
      self.selectionNone()

  def performDeleteRange(self, upperRow, upperCol, lowerRow, lowerCol):
    app.log.info(upperRow, upperCol, lowerRow, lowerCol)
    if upperRow == self.penRow == lowerRow:
      app.log.info()
      if upperCol < self.penCol:
        app.log.info()
        col = upperCol - self.penCol
        if lowerCol <= self.penCol:
          col = upperCol - lowerCol
        app.log.info(col)
        self.cursorMove(0, col)
        self.redo()
    elif upperRow <= self.penRow < lowerRow:
      app.log.info()
      self.cursorMove(upperRow - self.penRow, upperCol - self.penCol)
      self.redo()
    elif self.penRow == lowerRow:
      app.log.info()
      col = upperCol - lowerCol
      self.cursorMove(upperRow - self.penRow, col)
      self.redo()
    if 1:
      self.redoAddChange((
        'dr',
        (upperRow, upperCol, lowerRow, lowerCol),
        self.getText(upperRow, upperCol, lowerRow, lowerCol)))
      self.redo()

  def bookmarkAdd(self):
    app.bookmarks.add(self.fullPath, self.penRow, self.penCol, 0,
        app.selectable.kSelectionNone)

  def bookmarkGoto(self):
    app.log.debug()
    bookmark = app.bookmarks.get(self.view.bookmarkIndex)
    if bookmark:
      self.selectText(bookmark['row'], bookmark['col'], bookmark['length'],
          bookmark['mode'])

  def bookmarkNext(self):
    app.log.debug()
    self.view.bookmarkIndex += 1
    self.bookmarkGoto()

  def bookmarkPrior(self):
    app.log.debug()
    self.view.bookmarkIndex -= 1
    self.bookmarkGoto()

  def bookmarkRemove(self):
    app.log.debug()
    return app.bookmarks.remove(self.view.bookmarkIndex)

  def backspace(self):
    app.log.info('backspace', self.penRow > self.markerRow)
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
    self.redoAddChange(('n', (1, self.getCursorMove(1, -self.penCol))))
    self.redo()
    if 1: # todo: if indent on CR
      line = self.lines[self.penRow - 1]
      commonIndent = 2
      indent = 0
      while indent < len(line) and line[indent] == ' ':
        indent += 1
      if len(line):
        if line[-1] in [':', '[', '{']:
          indent += commonIndent
        elif line.count('(') > line.count(')'):
          indent += commonIndent * 2
      if indent:
        self.redoAddChange(('i', ' '*indent));
        self.redo()

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
    maxRow, maxCol = self.view.rows, self.view.cols
    if self.__skipCursorScroll:
      self.__skipCursorScroll = False
    else:
      scrollRows = 0
      if self.view.scrollRow > self.penRow + rowDelta:
        scrollRows = self.penRow + rowDelta - self.view.scrollRow
      elif self.penRow + rowDelta >= self.view.scrollRow + maxRow:
        scrollRows = self.penRow + rowDelta - (self.view.scrollRow + maxRow - 1)
      scrollCols = 0
      if self.view.scrollCol > self.penCol + colDelta:
        scrollCols = self.penCol + colDelta - self.view.scrollCol
      elif self.penCol + colDelta >= self.view.scrollCol + maxCol:
        scrollCols = self.penCol + colDelta - (self.view.scrollCol + maxCol - 1)
      self.view.scrollRow += scrollRows
      self.view.scrollCol += scrollCols
    return ('m', (rowDelta, colDelta,
        markRowDelta, markColDelta, selectionModeDelta))

  def cursorMoveAndMark(self, rowDelta, colDelta, markRowDelta,
      markColDelta, selectionModeDelta):
    change = self.getCursorMoveAndMark(rowDelta, colDelta, markRowDelta,
                                       markColDelta, selectionModeDelta)
    self.redoAddChange(change)
 
  def cursorMoveScroll(self, rowDelta, colDelta,
      scrollRowDelta, scrollColDelta):
    self.view.scrollRow += scrollRowDelta
    self.view.scrollCol += scrollColDelta
    self.redoAddChange(('m', (rowDelta, colDelta,
        0,0, 0)))

  def cursorMoveDown(self):
    if self.penRow + 1 < len(self.lines):
      savedGoal = self.goalCol
      self.cursorMove(1, self.cursorColDelta(self.penRow + 1))
      self.redo()
      self.goalCol = savedGoal

  def cursorMoveLeft(self):
    if self.penCol > 0:
      self.cursorMove(0, -1)
      self.redo()
    elif self.penRow > 0:
      self.cursorMove(-1, len(self.lines[self.penRow - 1]))
      self.redo()

  def cursorMoveRight(self):
    if not self.lines:
      return
    if self.penCol < len(self.lines[self.penRow]):
      self.cursorMove(0, 1)
      self.redo()
    elif self.penRow + 1 < len(self.lines):
      self.cursorMove(1, -len(self.lines[self.penRow]))
      self.redo()

  def cursorMoveUp(self):
    if self.penRow > 0:
      savedGoal = self.goalCol
      lineLen = len(self.lines[self.penRow - 1])
      if self.goalCol <= lineLen:
        self.cursorMove(-1, self.goalCol - self.penCol)
        self.redo()
      else:
        self.cursorMove(-1, lineLen - self.penCol)
        self.redo()
      self.goalCol = savedGoal

  def cursorMoveSubwordLeft(self):
    self.doCursorMoveLeftTo(app.selectable.kReSubwordBoundaryRvr)

  def cursorMoveSubwordRight(self):
    self.doCursorMoveRightTo(app.selectable.kReSubwordBoundaryFwd)

  def cursorMoveTo(self, row, col):
    cursorRow = min(max(row, 0), len(self.lines)-1)
    self.cursorMove(cursorRow - self.penRow, col - self.penCol)
    self.redo()

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
      self.redo()
    elif self.penRow > 0:
      self.cursorMove(-1, len(self.lines[self.penRow - 1]))
      self.redo()

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
      self.redo()
    elif self.penRow + 1 < len(self.lines):
      self.cursorMove(1, -len(self.lines[self.penRow]))
      self.redo()

  def cursorRight(self):
    self.selectionNone()
    self.cursorMoveRight()

  def cursorSelectDown(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveDown()

  def cursorSelectDownScroll(self):
    """Move the line below the selection to above the selection."""
    upperRow, upperCol, lowerRow, lowerCol = self.startAndEnd()
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

  def cursorSelectLineDown(self):
    """Set line selection and extend selection one row down."""
    self.selectionLine()
    if self.lines and self.penRow + 1 < len(self.lines):
      self.cursorMove(1, -self.penCol)
      self.redo()
      self.cursorMoveAndMark(*self.extendSelection())
      self.redo()

  def cursorSelectRight(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveRight()

  def cursorSelectSubwordLeft(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveSubwordLeft()
    self.cursorMoveAndMark(*self.extendSelection())
    self.redo()

  def cursorSelectSubwordRight(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveSubwordRight()
    self.cursorMoveAndMark(*self.extendSelection())
    self.redo()

  def cursorSelectWordLeft(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveWordLeft()
    self.cursorMoveAndMark(*self.extendSelection())
    self.redo()

  def cursorSelectWordRight(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveWordRight()
    self.cursorMoveAndMark(*self.extendSelection())
    self.redo()

  def cursorSelectUp(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveUp()

  def cursorSelectUpScroll(self):
    """Move the line above the selection to below the selection."""
    upperRow, upperCol, lowerRow, lowerCol = self.startAndEnd()
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
    self.redo()

  def cursorPageDown(self):
    if self.penRow == len(self.lines):
      return
    maxRow, maxCol = self.view.rows, self.view.cols
    penRowDelta = maxRow
    scrollDelta = maxRow
    numLines = len(self.lines)
    if self.penRow + maxRow >= numLines:
      penRowDelta = numLines - self.penRow - 1
    if numLines <= maxRow:
      scrollDelta = -self.view.scrollRow
    elif numLines <= 2*maxRow + self.view.scrollRow:
      scrollDelta = numLines - self.view.scrollRow - maxRow

    self.view.scrollRow += scrollDelta
    self.cursorMoveScroll(penRowDelta,
        self.cursorColDelta(self.penRow + penRowDelta), 0, 0)
    self.redo()

  def cursorPageUp(self):
    if self.penRow == 0:
      return
    maxRow, maxCol = self.view.rows, self.view.cols
    penRowDelta = -maxRow
    scrollDelta = -maxRow
    if self.penRow < maxRow:
      penRowDelta = -self.penRow
    if self.view.scrollRow + scrollDelta < 0:
      scrollDelta = -self.view.scrollRow
    self.view.scrollRow += scrollDelta
    self.cursorMoveScroll(penRowDelta,
        self.cursorColDelta(self.penRow + penRowDelta), 0, 0)
    self.redo()

  def cursorScrollToMiddle(self):
    maxRow, maxCol = self.view.rows, self.view.cols
    rowDelta = min(max(0, len(self.lines)-maxRow),
                   max(0, self.penRow - maxRow / 2)) - self.view.scrollRow
    self.cursorMoveScroll(0, 0, rowDelta, 0)

  def cursorStartOfLine(self):
    self.cursorMoveScroll(0, -self.penCol, 0, -self.view.scrollCol)
    self.redo()

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
      if self.selectionMode == app.selectable.kSelectionLine:
        text = text + ('',)
      data = self.doLinesToData(text)
      app.clipboard.copy(data)

  def editCut(self):
    self.editCopy()
    self.performDelete()

  def editPaste(self):
    data = app.clipboard.paste()
    if data is not None:
      self.editPasteLines(tuple(self.doDataToLines(data)))
    else:
      app.log.info('clipboard empty')

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
      self.redo()

  def doLinesToData(self, data):
    def encode(line):
      return chr(int(line.groups()[0], 16))
    return re.sub('\x01([0-9a-fA-F][0-9a-fA-F])', encode, "\n".join(data))

  def doDataToLines(self, data):
    # Performance: in a 1000 line test it appears fastest to do some simple
    # .replace() calls to minimize the number of calls to parse().
    data = data.replace('\r\n', '\n')
    data = data.replace('\r', '\n')
    data = data.replace('\t', ' '*8)
    def parse(sre):
      return "\x01%02x"%ord(sre.groups()[0])
    data = re.sub('([\0-\x09\x0b-\x1f\x7f-\xff])', parse, data)
    return data.split('\n')

  def dataToLines(self):
    self.lines = self.doDataToLines(self.data)

  def fileFilter(self, data):
    self.data = data
    self.dataToLines()
    self.savedAtRedoIndex = self.redoIndex

  def setFilePath(self, path):
    app.buffer_manager.buffers.renameBuffer(self, path)

  def fileLoad(self):
    app.log.info('fileLoad', self.fullPath)
    file = None
    try:
      file = open(self.fullPath, 'r')
      self.setMessage('Opened existing file')
      self.isReadOnly = not os.access(self.fullPath, os.W_OK)
      self.fileStat = os.stat(self.fullPath)
    except:
      try:
        # Create a new file.
        self.setMessage('Creating new file')
      except:
        app.log.info('error opening file', self.fullPath)
        self.setMessage('error opening file', self.fullPath)
        return
    self.relativePath = os.path.relpath(self.fullPath, os.getcwd())
    app.log.info('fullPath', self.fullPath)
    app.log.info('cwd', os.getcwd())
    app.log.info('relativePath', self.relativePath)
    if file:
      self.fileFilter(file.read())
      file.close()
    else:
      self.data = ""
    self.fileExtension = os.path.splitext(self.fullPath)[1]
    self.rootGrammar = app.prefs.getGrammar(self.fileExtension)
    if self.data:
      self.parseGrammars()
      self.dataToLines()
    else:
      self.parser = None
    app.history.loadUserHistory(self.fullPath)
    self.restoreUserHistory()

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
    self.view.scrollRow, self.view.scrollCol = self.optimalScrollPosition(
        self.penRow, self.penCol)
    self.doSelectionMode(self.fileHistory.setdefault('selectionMode',
        app.selectable.kSelectionNone))
    self.markerRow, self.markerCol = self.fileHistory.setdefault('marker',
        (0, 0))
    self.redoChain = self.fileHistory.setdefault('redoChain', [])
    self.savedAtRedoIndex = self.fileHistory.setdefault('savedAtRedoIndex', 0)
    self.redoIndex = self.savedAtRedoIndex

    # Store the file's info.
    self.lastChecksum, self.lastFileSize = app.history.getFileInfo(
        self.fullPath)

  def optimalScrollPosition(self, row=None, col=None):
    """
    Calculates the optimal position for the view.

    Args:
      row (int): The cursor's row position.
      col (int): The cursor's column position.

    Returns:
      A tuple of (row, col) representing where
      the view should be placed.
    """
    optimalRowRatio = app.prefs.editor['optimalCursorRow']
    optimalColRatio = app.prefs.editor['optimalCursorCol']
    maxRows = self.view.rows
    maxCols = self.view.cols
    scrollRow = self.view.scrollRow
    scrollCol = self.view.scrollCol
    # if not (scrollRow <= row < scrollRow + maxRows and
    #     scrollCol <= col < scrollCol + maxCols):
    #   # Use optimal position preferences set in default_prefs.py
    #   # or $HOME/.ci_edit/prefs/editor.py
    #   scrollRow = max(0, min(len(self.lines) - 1,
    #     row - int(optimalRowRatio * (maxRows - 1))))
    #   if col < maxCols:
    #     scrollCol = 0
    #   else:
    #     scrollCol = max(0, col - int(optimalColRatio * (maxCols - 1)))
    top, left, bottom, right = self.startAndEnd()
    height = bottom - top + 1
    length = right - left + 1
    extraRows = maxRows - height
    extraCols = maxCols - length
    if extraRows > 0:
      if not (scrollRow <= top and bottom < scrollRow + maxRows):
        scrollRow = max(0, min(len(self.lines) - 1,
          top - int(optimalRowRatio * (maxRows - 1))))
    else:
      scrollRow = top
    if extraCols > 0:
      if not (scrollCol <= left and right < scrollCol + maxCols):
        if right < maxCols:
          scrollCol = 0
        else:
          scrollCol = max(0, min(right, 
            left - int(optimalColRatio * (maxCols - 1))))
    else:
      scrollCol = left
    return (scrollRow, scrollCol)


  def linesToData(self):
    self.data = self.doLinesToData(self.lines)

  def fileWrite(self):
    # Preload the message with an error that should be overwritten.
    self.setMessage('Error saving file')
    try:
      try:
        if app.prefs.editor['onSaveStripTrailingSpaces']:
          self.stripTrailingWhiteSpace()
        # Save user data that applies to read-only files into history.
        self.fileHistory['pen'] = (self.penRow, self.penCol)
        self.fileHistory['cursor'] = (self.view.cursorRow, self.view.cursorCol)
        self.fileHistory['scroll'] = (self.view.scrollRow, self.view.scrollCol)
        self.fileHistory['marker'] = (self.markerRow, self.markerCol)
        self.fileHistory['selectionMode'] = self.selectionMode
        self.linesToData()
        file = open(self.fullPath, 'w+')
        file.seek(0)
        file.truncate()
        file.write(self.data)
        file.close()
        # Save user data that applies to writable files.
        self.savedAtRedoIndex = self.redoIndex
        self.fileHistory['redoChain'] = self.redoChain
        self.fileHistory['savedAtRedoIndex'] = self.savedAtRedoIndex
        # Hmm, could this be hard coded to False here?
        self.isReadOnly = not os.access(self.fullPath, os.W_OK)
        self.fileStat = os.stat(self.fullPath)
        self.setMessage('File saved')
      except Exception as e:
        type_, value, tb = sys.exc_info()
        self.setMessage(
            'Error writing file. The file did not save properly.',
            color=3)
        app.log.info('error writing file')
        out = traceback.format_exception(type_, value, tb)
        for i in out:
          app.log.info(i)
    except:
      app.log.info('except had exception')
    app.history.saveUserHistory((self.fullPath, self.lastChecksum,
        self.lastFileSize), self.fileHistory)
    # Store the file's new info
    self.lastChecksum, self.lastFileSize = app.history.getFileInfo(
        self.fullPath)

  def selectText(self, row, col, length, mode):
    row = max(0, min(row, len(self.lines) - 1))
    col = max(0, min(col, len(self.lines[row])))
    scrollRow = self.view.scrollRow
    scrollCol = self.view.scrollCol
    maxRow, maxCol = self.view.rows, self.view.cols
    self.doSelectionMode(app.selectable.kSelectionNone)
    self.cursorMoveScroll(
        row - self.penRow,
        col + length - self.penCol,
        0, 0)
    self.redo()
    self.doSelectionMode(mode)
    self.__skipCursorScroll = True
    self.cursorMove(0, -length)
    self.redo()

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
    self.findRe = re.compile('()'+searchFor)
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
    start, find, replace, flags = splitCmd
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
    self.redo()

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

  def verticalInsert(self, row, endRow, col, text):
    self.redoAddChange(('vi', (text, row, endRow, col)))
    self.redo()

  def insert(self, text):
    self.performDelete()
    self.redoAddChange(('i', text))
    self.redo()
    maxRow, maxCol = self.view.rows, self.view.cols
    deltaCol = self.penCol - self.view.scrollCol - maxCol + 1
    if deltaCol > 0:
      self.cursorMoveScroll(0, 0, 0, deltaCol);
      self.redo()

  def insertPrintable(self, ch):
    if curses.ascii.isprint(ch):
      self.insert(chr(ch))

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
    row = max(0, min(self.view.scrollRow + paneRow, len(self.lines) - 1))
    col = max(0, self.view.scrollCol + paneCol)
    if self.selectionMode == app.selectable.kSelectionBlock:
      self.cursorMoveAndMark(0, 0, row - self.markerRow, col - self.markerCol,
          0)
      self.redo()
      return
    # If not block selection, restrict col to the chars on the line.
    col = min(col, len(self.lines[row]))
    # Adjust the marker column delta when the pen and marker positions
    # cross over each other.
    markerCol = 0
    if self.selectionMode == app.selectable.kSelectionWord:
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
        0, markerCol, 0)
    self.redo()
    inLine = paneCol < len(self.lines[row])
    if self.selectionMode == app.selectable.kSelectionLine:
      self.cursorMoveAndMark(*self.extendSelection())
      self.redo()
    elif self.selectionMode == app.selectable.kSelectionWord:
      if (self.penRow < self.markerRow or
         (self.penRow == self.markerRow and
          self.penCol < self.markerCol)):
        self.cursorSelectWordLeft()
      elif inLine:
        self.cursorSelectWordRight()

  def mouseTripleClick(self, paneRow, paneCol, shift, ctrl, alt):
    app.log.info('triple click', paneRow, paneCol)
    self.mouseRelease(paneRow, paneCol, shift, ctrl, alt)
    self.selectLineAt(self.view.scrollRow + paneRow)

  def scrollWindow(self, rows, cols):
    self.cursorMoveScroll(rows, self.cursorColDelta(self.penRow - rows),
        -1, 0)
    self.redo()

  def mouseWheelDown(self, shift, ctrl, alt):
    if not shift:
      self.selectionNone()
    self.scrollUp()

  def scrollUp(self):
    if self.view.scrollRow == 0:
      if not self.view.hasCaptiveCursor:
        self.__skipUpdateScroll = True
      return
    maxRow, maxCol = self.view.rows, self.view.cols
    cursorDelta = 0
    if self.penRow >= self.view.scrollRow + maxRow - 2:
      cursorDelta = self.view.scrollRow + maxRow - 2 - self.penRow
    self.view.scrollRow -= 1
    if self.view.hasCaptiveCursor:
      self.cursorMoveScroll(cursorDelta,
          self.cursorColDelta(self.penRow + cursorDelta), 0, 0)
      self.redo()
    else:
      self.__skipUpdateScroll = True

  def mouseWheelUp(self, shift, ctrl, alt):
    if not shift:
      self.selectionNone()
    self.scrollDown()

  def scrollDown(self):
    maxRow, maxCol = self.view.rows, self.view.cols
    if self.view.scrollRow + maxRow >= len(self.lines):
      if not self.view.hasCaptiveCursor:
        self.__skipUpdateScroll = True
      return
    cursorDelta = 0
    if self.penRow <= self.view.scrollRow + 1:
      cursorDelta = self.view.scrollRow - self.penRow + 1
    self.view.scrollRow += 1
    if self.view.hasCaptiveCursor:
      self.cursorMoveScroll(cursorDelta,
          self.cursorColDelta(self.penRow + cursorDelta), 0, 0)
      self.redo()
    else:
      self.__skipUpdateScroll = True

  def nextSelectionMode(self):
    next = self.selectionMode + 1
    next %= app.selectable.kSelectionModeCount
    self.doSelectionMode(next)
    app.log.info('nextSelectionMode', self.selectionMode)

  def noOp(self, ignored):
    pass

  def normalize(self):
    self.selectionNone()
    self.findRe = None
    self.view.normalize()

  def parseGrammars(self):
    # Reset the self.data to get recent changes in self.lines.
    self.linesToData()
    if not self.parser:
      self.parser = app.parser.Parser()
    start = time.time()
    self.parser.parse(self.data, self.rootGrammar)
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
      self.selectLineAt(self.penRow)
    else:
      if self.penRow + 1 < len(self.lines):
        self.selectLineAt(self.penRow + 1)

  def selectionAll(self):
    self.doSelectionMode(app.selectable.kSelectionAll)
    self.cursorMoveAndMark(*self.extendSelection())
    self.redo()

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
    if row < len(self.lines):
      if 1:
        self.cursorMove(row - self.penRow, 0)
        self.redo()
        self.selectionLine()
        self.cursorMoveAndMark(*self.extendSelection())
        self.redo()
      else:
        # TODO(dschuyler): reverted to above to fix line selection in the line
        # numbers column. To be investigated further.
        self.selectText(row, 0, 0, app.selectable.kSelectionLine)

  def selectWordAt(self, row, col):
    """row and col may be from a mouse click and may not actually land in the
        document text."""
    self.selectText(row, col, 0, app.selectable.kSelectionWord)
    if col < len(self.lines[self.penRow]):
      self.cursorSelectWordRight()

  def splitLine(self):
    """split the line into two at current column."""
    self.redoAddChange(('n', (1,)))
    self.redo()

  def swapPenAndMarker(self):
    app.log.info('swapPenAndMarker')
    self.cursorMoveAndMark(self.markerRow - self.penRow,
        self.markerCol - self.penCol,
        self.penRow - self.markerRow,
        self.penCol - self.markerCol, 0)
    self.redo()

  def test(self):
    app.log.info('test')
    self.insertPrintable(0x00)

  def stripTrailingWhiteSpace(self):
    self.compoundChangeBegin()
    for i in range(len(self.lines)):
      for found in app.selectable.kReEndSpaces.finditer(self.lines[i]):
        self.performDeleteRange(i, found.regs[0][0], i, found.regs[0][1])
    self.compoundChangeEnd()

  def unindent(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      pass
    else:
      self.unindentLines()

  def unindentLines(self):
    indentation = app.prefs.editor['indentation']
    indentationLength = len(indentation)
    row = min(self.markerRow, self.penRow)
    endRow = max(self.markerRow, self.penRow)
    col = 0
    app.log.info('unindentLines', indentation, row, endRow, col)
    for line in self.lines[row:endRow + 1]:
      if (len(line) < indentationLength or
          (line[:indentationLength] != indentation)):
        # Handle multi-delete.
        return
    self.redoAddChange(('vd', (indentation, row, endRow, col)))
    self.redo()
    self.cursorMoveAndMark(0, -indentationLength, 0, -indentationLength, 0)
    self.redo()

  def updateScrollPosition(self):
    """Move the selected view rectangle so that the cursor is visible."""
    if self.__skipUpdateScroll:
      self.__skipUpdateScroll = False
      return
    maxRow, maxCol = self.view.rows, self.view.cols
    self.view.scrollRow, self.view.scrollCol = self.optimalScrollPosition(
        self.penRow, self.penCol)
