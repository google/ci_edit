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
import app.spelling
import curses.ascii
import difflib
import os
import re
import sys
import time
import traceback


class BackingTextBuffer(app.mutator.Mutator):
  """This base class to TextBuffer handles the text manipulation (without
  handling the drawing/rendering of the text)."""
  def __init__(self):
    app.mutator.Mutator.__init__(self)
    self.view = None
    self.rootGrammar = app.prefs.getGrammar(None)
    self.skipUpdateScroll = False

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
    if self.view.goalCol <= lineLen:
      return self.view.goalCol - self.penCol
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
    self.view.goalCol = self.penCol + colDelta
    maxRow, maxCol = self.view.cursorWindow.getmaxyx()
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
    self.view.goalCol = self.penCol + colDelta
    maxRow, maxCol = self.view.cursorWindow.getmaxyx()
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
    self.redoAddChange(('m', (rowDelta, colDelta,
        markRowDelta, markColDelta, selectionModeDelta)))

  def cursorMoveScroll(self, rowDelta, colDelta,
      scrollRowDelta, scrollColDelta):
    self.view.scrollRow += scrollRowDelta
    self.view.scrollCol += scrollColDelta
    self.redoAddChange(('m', (rowDelta, colDelta,
        0,0, 0)))

  def cursorMoveDown(self):
    if self.penRow + 1 < len(self.lines):
      savedGoal = self.view.goalCol
      self.cursorMove(1, self.cursorColDelta(self.penRow + 1))
      self.redo()
      self.view.goalCol = savedGoal

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
      savedGoal = self.view.goalCol
      lineLen = len(self.lines[self.penRow - 1])
      if self.view.goalCol <= lineLen:
        self.cursorMove(-1, self.view.goalCol - self.penCol)
        self.redo()
      else:
        self.cursorMove(-1, lineLen - self.penCol)
        self.redo()
      self.view.goalCol = savedGoal

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
    maxRow, maxCol = self.view.cursorWindow.getmaxyx()
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
    maxRow, maxCol = self.view.cursorWindow.getmaxyx()
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
    maxRow, maxCol = self.view.cursorWindow.getmaxyx()
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

  def linesToData(self):
    self.data = self.doLinesToData(self.lines)

  def fileWrite(self):
    app.history.set(
        ['files', self.fullPath, 'pen'], (self.penRow, self.penCol))
    # Preload the message with an error that should be overwritten.
    self.setMessage('Error saving file')
    try:
      try:
        self.stripTrailingWhiteSpace()
        self.linesToData()
        file = open(self.fullPath, 'w+')
        file.seek(0)
        file.truncate()
        file.write(self.data)
        file.close()
        # Hmm, could this be hard coded to False here?
        self.isReadOnly = not os.access(self.fullPath, os.W_OK)
        self.fileStat = os.stat(self.fullPath)
        self.setMessage('File saved')
        self.savedAtRedoIndex = self.redoIndex
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

  def selectText(self, row, col, length, mode):
    row = max(0, min(row, len(self.lines) - 1))
    col = max(0, min(col, len(self.lines[row])))
    scrollRow = self.view.scrollRow
    scrollCol = self.view.scrollCol
    maxRow, maxCol = self.view.cursorWindow.getmaxyx()
    if not (self.view.scrollRow < row <= self.view.scrollRow + maxRow):
      scrollRow = max(row - 10, 0)
    if not (self.view.scrollCol < col <= self.view.scrollCol + maxCol):
      scrollCol = max(col - 10, 0)
    self.doSelectionMode(app.selectable.kSelectionNone)
    self.view.scrollRow = scrollRow
    self.view.scrollCol = scrollCol
    self.cursorMoveScroll(
        row - self.penRow,
        col + length - self.penCol,
        0, 0)
    self.redo()
    self.doSelectionMode(mode)
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
    self.findRe = re.compile('()'+searchFor)
    self.findBackRe = re.compile('(.*)'+searchFor)
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
    if direction < 0:
      localRe = self.findBackRe
    if localRe is None:
      app.log.info('localRe is None')
      return
    # Current line.
    text = self.lines[self.penRow]
    if direction >= 0:
      text = text[self.penCol + direction:]
      offset = self.penCol + direction
    else:
      text = text[:self.penCol]
      offset = 0
    #app.log.info('find() searching', repr(text))
    found = localRe.search(text)
    if found:
      start = found.regs[1][1]
      end = found.regs[0][1]
      #app.log.info('found on line', self.penRow, start)
      self.selectText(self.penRow, offset + start, end - start,
          app.selectable.kSelectionCharacter)
      return
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
        start = found.regs[1][1]
        end = found.regs[0][1]
        self.selectText(i, start, end - start,
            app.selectable.kSelectionCharacter)
        return
    # Warp around to the start of the file.
    self.setMessage('Find wrapped around.')
    if direction >= 0:
      theRange = range(self.penRow)
    else:
      theRange = range(len(self.lines) - 1, self.penRow, -1)
    for i in theRange:
      found = localRe.search(self.lines[i])
      if found:
        #app.log.info('c found on line', i, repr(found))
        start = found.regs[1][1]
        end = found.regs[0][1]
        self.selectText(i, start, end - start,
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
    if self.selectionMode == app.selectable.kSelectionNone:
      self.cursorMoveAndMark(0, -self.penCol,
          self.penRow - self.markerRow, self.penCol - self.markerCol, 0)
      self.redo()
      self.indentLines()
    elif self.selectionMode == app.selectable.kSelectionAll:
      self.cursorMoveAndMark(len(self.lines) - 1 - self.penRow, -self.penCol,
          -self.markerRow, -self.markerCol,
          app.selectable.kSelectionLine - self.selectionMode)
      self.redo()
      self.indentLines()
    else:
      self.cursorMoveAndMark(0, -self.penCol, 0, -self.markerCol,
          app.selectable.kSelectionLine - self.selectionMode)
      self.redo()
      self.indentLines()

  def indentLines(self):
    self.redoAddChange(('vi', ('  ')))
    self.redo()

  def verticalInsert(self, row, endRow, col, text):
    self.redoAddChange(('vi', (text)))
    self.redo()

  def insert(self, text):
    self.performDelete()
    self.redoAddChange(('i', text))
    self.redo()
    maxRow, maxCol = self.view.cursorWindow.getmaxyx()
    deltaCol = self.penCol - self.view.scrollCol - maxCol + 1
    if deltaCol > 0:
      self.cursorMoveScroll(0, 0, 0, deltaCol);
      self.redo()

  def insertPrintable(self, ch):
    #app.log.info('insertPrintable')
    if curses.ascii.isprint(ch):
      self.insert(chr(ch))
    # else:
    #   self.insert("\xfe%02x"%(ch,))

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
        self.skipUpdateScroll = True
      return
    maxRow, maxCol = self.view.cursorWindow.getmaxyx()
    cursorDelta = 0
    if self.penRow >= self.view.scrollRow + maxRow - 2:
      cursorDelta = self.view.scrollRow + maxRow - 2 - self.penRow
    self.view.scrollRow -= 1
    if self.view.hasCaptiveCursor:
      self.cursorMoveScroll(cursorDelta,
          self.cursorColDelta(self.penRow + cursorDelta), 0, 0)
      self.redo()
    else:
      self.skipUpdateScroll = True

  def mouseWheelUp(self, shift, ctrl, alt):
    if not shift:
      self.selectionNone()
    self.scrollDown()

  def scrollDown(self):
    maxRow, maxCol = self.view.cursorWindow.getmaxyx()
    if self.view.scrollRow + maxRow >= len(self.lines):
      if not self.view.hasCaptiveCursor:
        self.skipUpdateScroll = True
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
      self.skipUpdateScroll = True

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
    for i in range(len(self.lines)):
      for found in app.selectable.kReEndSpaces.finditer(self.lines[i]):
        self.performDeleteRange(i, found.regs[0][0], i, found.regs[0][1])

  def unindent(self):
    if self.selectionMode == app.selectable.kSelectionAll:
      self.cursorMoveAndMark(len(self.lines) - 1 - self.penRow, -self.penCol,
          -self.markerRow, -self.markerCol,
          app.selectable.kSelectionLine - self.selectionMode)
      self.redo()
      self.unindentLines()
    else:
      self.cursorMoveAndMark(0, -self.penCol, 0, -self.markerCol,
          app.selectable.kSelectionLine - self.selectionMode)
      self.redo()
      self.unindentLines()

  def unindentLines(self):
    upperRow = min(self.markerRow, self.penRow)
    lowerRow = max(self.markerRow, self.penRow)
    app.log.info('unindentLines', upperRow, lowerRow)
    for line in self.lines[upperRow:lowerRow + 1]:
      if ((len(line) == 1 and line[:1] != ' ') or
          (len(line) >= 2 and line[:2] != '  ')):
        # Handle multi-delete.
        return
    self.redoAddChange(('vd', ('  ')))
    self.redo()

  def updateScrollPosition(self):
    """Move the selected view rectangle so that the cursor is visible."""
    if self.skipUpdateScroll:
      self.skipUpdateScroll = False
      return
    maxRow, maxCol = self.view.cursorWindow.getmaxyx()
    if self.view.scrollRow > self.penRow:
      self.view.scrollRow = self.penRow
    elif self.penRow >= self.view.scrollRow + maxRow:
      self.view.scrollRow = self.penRow - (maxRow - 1)
    if self.view.scrollCol > self.penCol:
      self.view.scrollCol = self.penCol
    elif self.penCol >= self.view.scrollCol + maxCol:
      self.view.scrollCol = self.penCol - (maxCol - 1)


class TextBuffer(BackingTextBuffer):
  """The TextBuffer adds the drawing/rendering to the BackingTextBuffer."""
  def __init__(self):
    BackingTextBuffer.__init__(self)
    self.lineLimitIndicator = sys.maxint
    self.highlightRe = None

  def checkScrollToCursor(self, window):
    """Move the selected view rectangle so that the cursor is visible."""
    maxRow, maxCol = window.cursorWindow.getmaxyx()
    #     self.penRow >= self.view.scrollRow + maxRow 1 0
    rows = 0
    if self.view.scrollRow > self.penRow:
      rows = self.penRow - self.view.scrollRow
      app.log.error('AAA self.view.scrollRow > self.penRow',
          self.view.scrollRow, self.penRow, self)
    elif self.penRow >= self.view.scrollRow + maxRow:
      rows = self.penRow - (self.view.scrollRow + maxRow - 1)
      app.log.error('BBB self.penRow >= self.view.scrollRow + maxRow cRow',
          self.penRow, 'sRow', self.view.scrollRow, 'maxRow', maxRow, self)
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
    self.view.scrollRow += rows
    self.view.scrollCol += cols

  def draw(self, window):
    if self.shouldReparse:
      self.parseGrammars()
      self.shouldReparse = False
    if self.view.hasCaptiveCursor:
      self.checkScrollToCursor(window)
    rows, cols = window.cursorWindow.getmaxyx()
    if 0:
      for i in range(rows):
        window.addStr(i, 0, '?' * cols, curses.color_pair(120))
    if 0:
      self.drawTextArea(window, 0, 0, rows, cols, 0)
    elif 1:
      splitRow = rows
      splitCol = min(cols, self.lineLimitIndicator)
      self.drawTextArea(window, 0, 0, splitRow, splitCol, 0)
      if splitCol < cols:
        self.drawTextArea(window, 0, splitCol, splitRow, cols-splitCol, 32*4)
    else:
      splitRow = rows / 2
      splitCol = 17
      self.drawTextArea(window, 0, 0, splitRow, splitCol, 0)
      self.drawTextArea(window, 0, splitCol, splitRow, cols-splitCol, 192)
      self.drawTextArea(window, splitRow, 0, rows - splitRow, splitCol, 192)
      self.drawTextArea(window, splitRow, splitCol, rows - splitRow,
          cols-splitCol, 0)
    # Blank screen past the end of the buffer.
    color = curses.color_pair(app.prefs.outsideOfBufferColorIndex)
    endOfText = min(max(len(self.lines) - self.view.scrollRow, 0), rows)
    for i in range(endOfText, rows):
      window.addStr(i, 0, ' ' * cols, color)

  def drawTextArea(self, window, top, left, rows, cols, colorDelta):
    startRow = self.view.scrollRow + top
    startCol = self.view.scrollCol + left
    endCol = self.view.scrollCol + left + cols
    colors = app.prefs.prefs['color']
    spellChecking = app.prefs.prefs['editor'].get('spellChecking', True)
    if self.parser:
      # Highlight grammar.
      rowLimit = min(max(len(self.lines) - startRow, 0), rows)
      for i in range(rowLimit):
        k = startCol
        while k < endCol:
          node, preceding, remaining = self.parser.grammarFromRowCol(
              startRow + i, k)
          line = self.lines[startRow + i]
          assert remaining >= 0, remaining
          remaining = min(len(line) - k, remaining)
          length = min(endCol - k, remaining)
          color = curses.color_pair(node.grammar.get(
              'colorIndex', app.prefs.defaultColorIndex) + colorDelta)
          if length <= 0:
            window.addStr(top + i, left + k - startCol, ' ' * (endCol - k),
                color)
            break
          window.addStr(top + i, left + k - startCol, line[k:k + length], color)
          subStart = k - preceding
          subEnd = k + remaining
          subLine = line[subStart:subEnd]
          if spellChecking:
            if node.grammar.get('spelling', True):
              # Highlight spelling errors
              grammarName = node.grammar.get('name', 'unknown')
              misspellingColor = curses.color_pair(
                  colors['misspelling'] + colorDelta)
              for found in re.finditer(app.selectable.kReSubwords, subLine):
                reg = found.regs[0]  # Mispelllled word
                offsetStart = subStart + reg[0]
                offsetEnd = subStart + reg[1]
                if startCol < offsetEnd and offsetStart < endCol:
                  word = line[offsetStart:offsetEnd]
                  if not app.spelling.isCorrect(word, grammarName):
                    if startCol > offsetStart:
                      offsetStart += startCol - offsetStart
                    wordFragment = line[offsetStart:min(endCol, offsetEnd)]
                    window.addStr(top + i, left + offsetStart - startCol,
                        wordFragment,
                        misspellingColor | curses.A_BOLD | curses.A_REVERSE)
          if 1:
            # Highlight keywords.
            keywordColor = curses.color_pair(colors['keyword'] + colorDelta)
            regex = node.grammar.get('keywordsRe', app.prefs.kReNonMatching)
            for found in regex.finditer(subLine):
              reg = found.regs[0]
              offsetStart = subStart + reg[0]
              offsetEnd = subStart + reg[1]
              if startCol < offsetEnd and offsetStart < endCol:
                if startCol > offsetStart:
                  offsetStart += startCol - offsetStart
                wordFragment = line[offsetStart:min(endCol, offsetEnd)]
                window.addStr(top + i, left + offsetStart - startCol,
                    wordFragment, keywordColor)
          if 1:
            # Highlight specials.
            keywordColor = curses.color_pair(colors['keyword'] + colorDelta)
            regex = node.grammar.get('specialsRe', app.prefs.kReNonMatching)
            for found in regex.finditer(subLine):
              reg = found.regs[0]
              offsetStart = subStart + reg[0]
              offsetEnd = subStart + reg[1]
              if startCol < offsetEnd and offsetStart < endCol:
                if startCol > offsetStart:
                  offsetStart += startCol - offsetStart
                wordFragment = line[offsetStart:min(endCol, offsetEnd)]
                window.addStr(top + i, left + offsetStart - startCol,
                    wordFragment, keywordColor)
          k += length
    else:
      # Draw to screen.
      rowLimit = min(max(len(self.lines) - startRow, 0), rows)
      for i in range(rowLimit):
        line = self.lines[startRow + i][startCol:endCol]
        window.addStr(top + i, left, line + ' ' * (cols - len(line)),
            curses.color_pair(app.prefs.prefs['color']['default'] + colorDelta))
    self.drawOverlays(window, top, left, rows, cols, colorDelta)

  def drawOverlays(self, window, top, left, maxRow, maxCol, colorDelta):
    startRow = self.view.scrollRow + top
    endRow = self.view.scrollRow + top + maxRow
    startCol = self.view.scrollCol + left
    endCol = self.view.scrollCol + left + maxCol
    rowLimit = min(max(len(self.lines) - startRow, 0), maxRow)
    colors = app.prefs.prefs['color']
    if 1:
      # Highlight brackets.
      color = curses.color_pair(colors['bracket'] + colorDelta)
      for i in range(rowLimit):
        line = self.lines[startRow + i][startCol:endCol]
        for k in re.finditer(app.selectable.kReBrackets, line):
          for f in k.regs:
            window.addStr(top + i, left+f[0], line[f[0]:f[1]], color)
    if 1:
      # Match brackets.
      if (len(self.lines) > self.penRow and
          len(self.lines[self.penRow]) > self.penCol):
        ch = self.lines[self.penRow][self.penCol]
        def searchBack(closeCh, openCh):
          count = -1
          for row in range(self.penRow, -1, -1):
            line = self.lines[row]
            if row == self.penRow:
              line = line[:self.penCol]
            found = [i for i in
                re.finditer("(\\" + openCh + ")|(\\" + closeCh + ")", line)]
            for match in reversed(found):
              if match.group() == openCh:
                count += 1
              else:
                count -= 1
              if count == 0:
                textCol = match.start()
                if not (textCol < startCol or textCol >= endCol):
                  window.addStr(top + row - startRow,
                      textCol - self.view.scrollCol, openCh,
                      curses.color_pair(
                          colors['matching_bracket'] + colorDelta))
                return
        def searchForward(openCh, closeCh):
          count = 1
          textCol = self.penCol + 1
          for row in range(self.penRow, startRow + maxRow):
            if row != self.penRow:
              textCol = 0
            line = self.lines[row][textCol:]
            for match in re.finditer("(\\" + openCh + ")|(\\" + closeCh + ")",
                line):
              if match.group() == openCh:
                count += 1
              else:
                count -= 1
              if count == 0:
                textCol += match.start()
                if not (textCol < startCol or textCol >= endCol):
                  window.addStr(top + row - startRow,
                      textCol - self.view.scrollCol, closeCh,
                      curses.color_pair(
                          colors['matching_bracket'] + colorDelta))
                return
        matcher = {
          '(': (')', searchForward),
          '[': (']', searchForward),
          '{': ('}', searchForward),
          ')': ('(', searchBack),
          ']': ('[', searchBack),
          '}': ('{', searchBack),
        }
        look = matcher.get(ch)
        if look:
          look[1](ch, look[0])
          window.addStr(
              top + self.penRow - startRow,
              self.penCol - self.view.scrollCol,
              self.lines[self.penRow][self.penCol],
              curses.color_pair(colors['matching_bracket'] + colorDelta))
    if 1:
      # Highlight numbers.
      for i in range(rowLimit):
        line = self.lines[startRow + i][startCol:endCol]
        for k in re.finditer(app.selectable.kReNumbers, line):
          for f in k.regs:
            window.addStr(top + i, left + f[0], line[f[0]:f[1]],
                curses.color_pair(colors['number'] + colorDelta))
    if 1:
      # Highlight space ending lines.
      for i in range(rowLimit):
        line = self.lines[startRow + i][startCol:]
        offset = 0
        if startRow + i == self.penRow:
          offset = self.penCol - startCol
          line = line[offset:]
        for k in app.selectable.kReEndSpaces.finditer(line):
          for f in k.regs:
            window.addStr(top + i, left + offset + f[0], line[f[0]:f[1]],
                curses.color_pair(colors['trailing_space'] + colorDelta))
    if 0:
      lengthLimit = self.lineLimitIndicator
      if endCol >= lengthLimit:
        # Highlight long lines.
        for i in range(rowLimit):
          line = self.lines[startRow + i]
          if len(line) < lengthLimit or startCol > lengthLimit:
            continue
          length = min(endCol, len(line) - lengthLimit)
          window.addStr(top + i, left + lengthLimit - startCol,
              line[lengthLimit:endCol], curses.color_pair(96 + colorDelta))
    if self.findRe is not None:
      # Highlight find.
      for i in range(rowLimit):
        line = self.lines[startRow + i][startCol:endCol]
        for k in self.findRe.finditer(line):
          reg = k.regs[0]
          #for ref in k.regs[1:]:
          window.addStr(top + i, left + reg[0], line[reg[0]:reg[1]],
              curses.color_pair(colors['found_find'] + colorDelta))
    if rowLimit and self.selectionMode != app.selectable.kSelectionNone:
      # Highlight selected text.
      colorSelected = curses.color_pair(colors['selected'])
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
              line = self.lines[startRow + i][selStartCol:selEndCol]
              window.addStr(top + i, selStartCol, line, colorSelected)
        elif (self.selectionMode == app.selectable.kSelectionAll or
            self.selectionMode == app.selectable.kSelectionCharacter or
            self.selectionMode == app.selectable.kSelectionWord):
          if not (lowerRow < startRow or upperRow >= endRow):
            # There is an overlap.
            # Go one row past the selection or to the last line.
            for i in range(start, min(end + 1, len(self.lines) - startRow)):
              line = self.lines[startRow + i]
              # TODO(dschuyler): This is essentially
              # left + (upperCol or (scrollCol + left)) - scrollCol - left
              # which seems like it could be simplified.
              paneCol = left + selStartCol - startCol
              if len(line) == len(self.lines[startRow + i]):
                line += " "  # Maybe do: "\\n".
              if i == lowerRow - startRow and i == upperRow - startRow:
                # Selection entirely on one line.
                window.addStr(top + i, paneCol, line[selStartCol:selEndCol],
                    colorSelected)
              elif i == lowerRow - startRow:
                # End of multi-line selection.
                window.addStr(top + i, left, line[startCol:selEndCol],
                    colorSelected)
              elif i == upperRow - startRow:
                # Start of multi-line selection.
                window.addStr(top + i, paneCol, line[selStartCol:endCol],
                    colorSelected)
              else:
                # Middle of multi-line selection.
                window.addStr(top + i, left, line[startCol:endCol],
                    colorSelected)
        elif self.selectionMode == app.selectable.kSelectionLine:
          if not (lowerRow < startRow or upperRow >= endRow):
            # There is an overlap.
            for i in range(start, end + 1):
              line = self.lines[startRow + i][selStartCol:endCol]
              window.addStr(top + i, selStartCol,
                  line + ' ' * (maxCol - len(line)), colorSelected)
