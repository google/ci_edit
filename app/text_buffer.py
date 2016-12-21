# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.log
import app.selectable
import app.prefs
import third_party.pyperclip as clipboard
import curses.ascii
import os
import re
import sys
import traceback


def addVectors(a, b):
  """Add two list-like objects, pair-wise."""
  return tuple([a[i]+b[i] for i in range(len(a))])


class Mutator(app.selectable.Selectable):
  """Track changes to a body of text."""
  def __init__(self):
    app.selectable.Selectable.__init__(self)
    self.debugRedo = False
    self.findRe = None
    self.findBackRe = None
    self.fullPath = ''
    self.relativePath = ''
    self.scrollRow = 0
    self.scrollToRow = 0
    self.scrollCol = 0
    self.redoChain = []
    self.redoIndex = 0
    self.savedAtRedoIndex = 0

  def addLine(self, msg):
    """Direct manipulator for logging to a read-only buffer."""
    self.lines.append(msg)
    self.cursorRow += 1

  def isDirty(self):
    """Whether the buffer contains non-trival changes since the last save."""
    clean = self.savedAtRedoIndex >= 0 and (
        self.savedAtRedoIndex == self.redoIndex or
        (self.redoIndex + 1 == self.savedAtRedoIndex and
          self.redoChain[self.redoIndex][0] == 'm') or
        (self.redoIndex - 1 == self.savedAtRedoIndex and
          self.redoChain[self.redoIndex-1][0] == 'm'))
    return not clean

  def redo(self):
    """Replay the next action on the redoChain."""
    if self.redoIndex < len(self.redoChain):
      change = self.redoChain[self.redoIndex]
      if self.debugRedo:
        app.log.info('redo', self.redoIndex, repr(change))
      self.redoIndex += 1
      if change[0] == 'b':
        line = self.lines[self.cursorRow]
        self.cursorCol -= len(change[1])
        x = self.cursorCol
        self.lines[self.cursorRow] = line[:x] + line[x+len(change[1]):]
      elif change[0] == 'd':
        line = self.lines[self.cursorRow]
        x = self.cursorCol
        self.lines[self.cursorRow] = line[:x] + line[x+len(change[1]):]
      elif change[0] == 'ds':  # Redo delete selection.
        self.doDeleteSelection()
      elif change[0] == 'i':
        line = self.lines[self.cursorRow]
        x = self.cursorCol
        self.lines[self.cursorRow] = line[:x] + change[1] + line[x:]
        self.cursorCol += len(change[1])
        self.goalCol = self.cursorCol
      elif change[0] == 'j':
        # Join lines.
        self.lines[self.cursorRow] += self.lines[self.cursorRow+1]
        del self.lines[self.cursorRow+1]
      elif change[0] == 'm':
        self.cursorRow += change[1][0]
        self.cursorCol += change[1][1]
        self.goalCol += change[1][2]
        self.scrollRow += change[1][3]
        self.scrollCol += change[1][4]
        self.markerRow += change[1][5]
        self.markerCol += change[1][6]
        self.markerEndRow += change[1][7]
        self.markerEndCol += change[1][8]
        self.selectionMode += change[1][9]
      elif change[0] == 'n':
        # Redo split lines.
        line = self.lines[self.cursorRow]
        self.lines.insert(self.cursorRow+1, line[self.cursorCol:])
        self.lines[self.cursorRow] = line[:self.cursorCol]
        for i in range(max(change[1][0] - 1, 0)):
          self.lines.insert(self.cursorRow+1, "")
      elif change[0] == 'v':  # Redo paste.
        self.insertLines(change[1])
      elif change[0] == 'vb':
        self.cursorCol -= len(change[1])
        row = min(self.markerRow, self.cursorRow)
        rowEnd = max(self.markerRow, self.cursorRow)
        for i in range(row, rowEnd+1):
          line = self.lines[i]
          x = self.cursorCol
          self.lines[self.cursorRow] = line[:x] + line[x+len(change[1]):]
      elif change[0] == 'vd':
        upperRow = min(self.markerRow, self.cursorRow)
        lowerRow = max(self.markerRow, self.cursorRow)
        x = self.cursorCol
        for i in range(upperRow, lowerRow+1):
          line = self.lines[i]
          self.lines[i] = line[:x] + line[x+len(change[1]):]
      elif change[0] == 'vi':  # Redo
        text = change[1]
        col = self.cursorCol
        row = min(self.markerRow, self.cursorRow)
        rowEnd = max(self.markerRow, self.cursorRow)
        app.log.info('do vi')
        for i in range(row, rowEnd+1):
          line = self.lines[i]
          self.lines[i] = line[:col] + text + line[col:]
      else:
        app.log.info('ERROR: unknown redo.')
    # Redo again if there is a move next.
    if (self.redoIndex < len(self.redoChain) and
        self.redoChain[self.redoIndex][0] == 'm'):
      self.redo()

  def redoAddChange(self, change):
    """Push a change onto the end of the redoChain. Call redo() to enact the
        change."""
    if self.debugRedo:
      app.log.info('redoAddChange', change)
    # When the redoChain is trimmed we lose the saved at.
    if self.redoIndex < self.savedAtRedoIndex:
      self.savedAtRedoIndex = -1
    self.redoChain = self.redoChain[:self.redoIndex]
    if 1: # optimizer
      if len(self.redoChain) and self.savedAtRedoIndex != self.redoIndex:
        if (self.redoChain[-1][0] == change[0] and
            change[0] in ('d', 'i')):
          change = (change[0], self.redoChain[-1][1] + change[1])
          self.undoOne()
          self.redoChain.pop()
        elif change[0] == 'm':
          if self.redoChain[-1][0] == 'm':
            change = (change[0], addVectors(self.redoChain[-1][1], change[1]))
            self.undoOne()
            self.redoChain.pop()
        elif self.redoChain[-1][0] == change[0] and change[0] == 'n':
          change = (change[0], addVectors(self.redoChain[-1][1], change[1]))
          self.undoOne()
          self.redoChain.pop()
    if 1:
      # Eliminate no-op entries
      noOpInstructions = set([
        ('m', (0,0,0,0,0,0,0,0,0,0)),
      ])
      assert ('m', (0,0,0,0,0,0,0,0,0,0)) in noOpInstructions
      if change in noOpInstructions:
        return
      #app.log.info('opti', change)
    self.redoChain.append(change)
    if self.debugRedo:
      app.log.info('--- redoIndex', self.redoIndex)
      for i,c in enumerate(self.redoChain):
        app.log.info('%2d:'%i, repr(c))

  def undo(self):
    """Undo a set of redo nodes."""
    while self.undoOne():
      pass

  def undoOne(self):
    """Undo the most recent change to the buffer.
    return whether undo should be repeated."""
    app.log.detail('undo')
    if self.redoIndex > 0:
      self.redoIndex -= 1
      change = self.redoChain[self.redoIndex]
      if self.debugRedo:
        app.log.info('undo', self.redoIndex, repr(change))
      if change[0] == 'b':
        line = self.lines[self.cursorRow]
        x = self.cursorCol
        self.lines[self.cursorRow] = line[:x] + change[1] + line[x:]
        self.cursorCol += len(change[1])
      elif change[0] == 'd':
        line = self.lines[self.cursorRow]
        x = self.cursorCol
        self.lines[self.cursorRow] = line[:x] + change[1] + line[x:]
      elif change[0] == 'ds':  # Undo delete selection.
        app.log.detail('undo ds', change[1])
        self.insertLines(change[1])
      elif change[0] == 'i':
        line = self.lines[self.cursorRow]
        x = self.cursorCol
        self.cursorCol -= len(change[1])
        self.lines[self.cursorRow] = line[:x-len(change[1])] + line[x:]
        self.goalCol = self.cursorCol
      elif change[0] == 'j':
        # Join lines.
        line = self.lines[self.cursorRow]
        self.lines.insert(self.cursorRow+1, line[self.cursorCol:])
        self.lines[self.cursorRow] = line[:self.cursorCol]
      elif change[0] == 'm':
        app.log.detail('undo move');
        self.cursorRow -= change[1][0]
        self.cursorCol -= change[1][1]
        self.goalCol -= change[1][2]
        self.scrollRow -= change[1][3]
        self.scrollCol -= change[1][4]
        self.markerRow -= change[1][5]
        self.markerCol -= change[1][6]
        self.markerEndRow -= change[1][7]
        self.markerEndCol -= change[1][8]
        self.selectionMode -= change[1][9]
        return True
      elif change[0] == 'n':
        # Undo split lines.
        self.lines[self.cursorRow] += self.lines[self.cursorRow+change[1][0]]
        for i in range(change[1][0]):
          del self.lines[self.cursorRow+1]
      elif change[0] == 'v':  # undo paste
        clip = change[1]
        row = self.cursorRow
        col = self.cursorCol
        app.log.info('len clip', len(clip))
        if len(clip) == 1:
          self.lines[row] = (
              self.lines[row][:col] +
              self.lines[row][col+len(clip[0]):])
        else:
          self.lines[row] = (self.lines[row][:col]+
              self.lines[row+len(clip)-1][len(clip[-1]):])
          delLineCount = len(clip[1:-1])
          del self.lines[row+1:row+1+delLineCount+1]
      elif change[0] == 'vb':
        row = min(self.markerRow, self.cursorRow)
        endRow = max(self.markerRow, self.cursorRow)
        for i in range(row, endRow+1):
          line = self.lines[self.cursorRow]
          x = self.cursorCol
          self.lines[self.cursorRow] = line[:x] + change[1] + line[x:]
        self.cursorCol += len(change[1])
      elif change[0] == 'vd':
        upperRow = min(self.markerRow, self.cursorRow)
        lowerRow = max(self.markerRow, self.cursorRow)
        x = self.cursorCol
        for i in range(upperRow, lowerRow+1):
          line = self.lines[i]
          self.lines[i] = line[:x] + change[1] + line[x:]
      elif change[0] == 'vi':  # Undo.
        text = change[1]
        col = self.cursorCol
        row = min(self.markerRow, self.cursorRow)
        endRow = max(self.markerRow, self.cursorRow)
        textLen = len(text)
        app.log.info('undo vi', textLen)
        for i in range(row, endRow+1):
          line = self.lines[i]
          self.lines[i] = line[:col] + line[col+textLen:]
      else:
        app.log.info('ERROR: unknown undo.')
    return False


class BackingTextBuffer(Mutator):
  """This base class to TextBuffer handles the text manipulation (without
  handling the drawing/rendering of the text)."""
  def __init__(self):
    Mutator.__init__(self)
    self.view = None
    self.clipList = []

  def setView(self, view):
    self.view = view

  def performDelete(self):
    if self.selectionMode != app.selectable.kSelectionNone:
      text = self.getSelectedText()
      if text:
        if (self.cursorRow > self.markerRow or
            (self.cursorRow == self.markerRow and
            self.cursorCol > self.markerCol)):
          self.swapCursorAndMarker()
        self.redoAddChange(('ds', text))
        self.redo()
      self.selectionNone()

  def backspace(self):
    app.log.info('backspace', self.cursorRow > self.markerRow)
    if self.selectionMode != app.selectable.kSelectionNone:
      self.performDelete()
    elif self.cursorCol == 0:
      if self.cursorRow > 0:
        self.cursorLeft()
        self.joinLines()
    else:
      line = self.lines[self.cursorRow]
      change = ('b', line[self.cursorCol-1:self.cursorCol])
      self.redoAddChange(change)
      self.redo()

  def carriageReturn(self):
    self.performDelete()
    self.redoAddChange(('n', (1,)))
    self.redo()
    self.cursorMove(1, -self.cursorCol, -self.goalCol)
    self.redo()
    app.log.debug('carriageReturn d')
    if 1: # todo: if indent on CR
      line = self.lines[self.cursorRow-1]
      commonIndent = 2
      indent = 0
      while indent < len(line) and line[indent] == ' ':
        indent += 1
      if len(line) and line[-1] == ':':
        indent += commonIndent
      if indent:
        self.redoAddChange(('i', ' '*indent));
        self.redo()

  def cursorColDelta(self, toRow):
    if toRow >= len(self.lines):
      return
    lineLen = len(self.lines[toRow])
    if self.goalCol <= lineLen:
      return self.goalCol - self.cursorCol
    return lineLen - self.cursorCol

  def cursorDown(self):
    self.selectionNone()
    self.cursorMoveDown()

  def cursorDownScroll(self):
    #todo:
    self.selectionNone()
    self.cursorMoveDown()

  def cursorLeft(self):
    self.selectionNone()
    self.cursorMoveLeft()

  def cursorMove(self, rowDelta, colDelta, goalColDelta):
    self.cursorMoveAndMark(rowDelta, colDelta, goalColDelta, 0, 0, 0)

  def cursorMoveAndMark(self, rowDelta, colDelta, goalColDelta, markRowDelta,
      markColDelta, selectionModeDelta):
    maxy, maxx = self.view.cursorWindow.getmaxyx()
    scrollRows = 0
    if self.scrollRow > self.cursorRow+rowDelta:
      scrollRows = self.cursorRow+rowDelta - self.scrollRow
    elif self.cursorRow+rowDelta >= self.scrollRow+maxy:
      scrollRows = self.cursorRow+rowDelta - (self.scrollRow+maxy-1)
    scrollCols = 0
    if self.scrollCol > self.cursorCol+colDelta:
      scrollCols = self.cursorCol+colDelta - self.scrollCol
    elif self.cursorCol+colDelta >= self.scrollCol+maxx:
      scrollCols = self.cursorCol+colDelta - (self.scrollCol+maxx-1)
    self.redoAddChange(('m', (rowDelta, colDelta, goalColDelta,
        scrollRows, scrollCols,
        markRowDelta, markColDelta, 0, 0, selectionModeDelta)))

  def cursorMoveScroll(self, rowDelta, colDelta, goalColDelta,
      scrollRowDelta, scrollColDelta):
    self.redoAddChange(('m', (rowDelta, colDelta, goalColDelta, scrollRowDelta,
        scrollColDelta,0,0, 0, 0,0)))

  def cursorMoveDown(self):
    if self.cursorRow+1 < len(self.lines):
      self.cursorMove(1, self.cursorColDelta(self.cursorRow+1), 0)
      self.redo()

  def cursorMoveLeft(self):
    if self.cursorCol > 0:
      self.cursorMove(0, -1, self.cursorCol-1 - self.goalCol)
      self.redo()
    elif self.cursorRow > 0:
      self.cursorMove(-1, len(self.lines[self.cursorRow-1]),
          self.cursorCol - self.goalCol)
      self.redo()

  def cursorMoveRight(self):
    if not self.lines:
      return
    if self.cursorCol < len(self.lines[self.cursorRow]):
      self.cursorMove(0, 1, self.cursorCol+1 - self.goalCol)
      self.redo()
    elif self.cursorRow+1 < len(self.lines):
      self.cursorMove(1, -len(self.lines[self.cursorRow]),
          self.cursorCol - self.goalCol)
      self.redo()

  def cursorMoveUp(self):
    if self.cursorRow > 0:
      lineLen = len(self.lines[self.cursorRow-1])
      if self.goalCol <= lineLen:
        self.cursorMove(-1, self.goalCol - self.cursorCol, 0)
        self.redo()
      else:
        self.cursorMove(-1, lineLen - self.cursorCol, 0)
        self.redo()

  def cursorMoveWordLeft(self):
    if self.cursorCol > 0:
      line = self.lines[self.cursorRow]
      pos = self.cursorCol
      for segment in re.finditer(app.selectable.kReWordBoundary, line):
        if segment.start() < pos <= segment.end():
          pos = segment.start()
          break
      self.cursorMove(0, pos-self.cursorCol, pos-self.cursorCol - self.goalCol)
      self.redo()
    elif self.cursorRow > 0:
      self.cursorMove(-1, len(self.lines[self.cursorRow-1]),
          self.cursorCol - self.goalCol)
      self.redo()

  def cursorMoveWordRight(self):
    if not self.lines:
      return
    if self.cursorCol < len(self.lines[self.cursorRow]):
      line = self.lines[self.cursorRow]
      pos = self.cursorCol
      for segment in re.finditer(app.selectable.kReWordBoundary, line):
        if segment.start() <= pos < segment.end():
          pos = segment.end()
          break
      self.cursorMove(0, pos-self.cursorCol, pos-self.cursorCol - self.goalCol)
      self.redo()
    elif self.cursorRow+1 < len(self.lines):
      self.cursorMove(1, -len(self.lines[self.cursorRow]),
          self.cursorCol - self.goalCol)
      self.redo()

  def cursorRight(self):
    self.selectionNone()
    self.cursorMoveRight()

  def cursorSelectDown(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveDown()

  def cursorSelectDownScroll(self):
    #todo:
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveDown()

  def cursorSelectLeft(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveLeft()

  def cursorSelectLineDown(self):
    """Set line selection and extend selection one row down."""
    self.selectionLine()
    if self.lines and self.cursorRow+1 < len(self.lines):
      self.cursorMove(1, -self.cursorCol, -self.goalCol)
      self.redo()
      self.cursorMoveAndMark(*self.extendSelection())
      self.redo()

  def cursorSelectRight(self):
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveRight()

  def cursorSelectWordLeft(self):
    app.log.info('cursorSelectWordLeft')
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    if self.cursorRow == self.markerRow and self.cursorCol == self.markerCol:
      app.log.info('They match')
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
    #todo:
    if self.selectionMode == app.selectable.kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveUp()

  def cursorEndOfLine(self):
    lineLen = len(self.lines[self.cursorRow])
    self.cursorMove(0, lineLen-self.cursorCol, lineLen-self.goalCol)
    self.redo()

  def cursorPageDown(self):
    if self.cursorRow == len(self.lines):
      return
    maxy, maxx = self.view.cursorWindow.getmaxyx()
    cursorRowDelta = maxy
    scrollDelta = maxy
    if self.cursorRow + 2*maxy >= len(self.lines):
      cursorRowDelta = len(self.lines)-self.cursorRow-1
      scrollDelta = len(self.lines)-maxy-self.scrollRow
    self.cursorMoveScroll(cursorRowDelta,
        self.cursorColDelta(self.cursorRow+cursorRowDelta), 0, scrollDelta, 0)
    self.redo()

  def cursorPageUp(self):
    if self.cursorRow == 0:
      return
    maxy, maxx = self.view.cursorWindow.getmaxyx()
    cursorRowDelta = -maxy
    scrollDelta = -maxy
    if self.cursorRow < 2*maxy:
      cursorRowDelta = -self.cursorRow
      scrollDelta = -self.scrollRow
    self.cursorMoveScroll(cursorRowDelta,
        self.cursorColDelta(self.cursorRow+cursorRowDelta), 0, scrollDelta, 0)
    self.redo()

  def cursorScrollTo(self, goalRow, window):
    maxy, maxx = window.getmaxyx()
    if len(self.lines) < maxy:
      goalRow = 0
    elif goalRow < 0:
      goalRow = len(self.lines)+goalRow-maxy+1
    #scrollTo = min(min(goalRow, len(self.lines)-1), len(self.lines)-maxy-1)
    # self.cursorMoveScroll(scrollTo-self.cursorRow, -self.cursorCol, 0,
    #     scrollTo-self.scrollRow, -self.scrollCol)
    # self.redo()
    self.cursorRow = self.scrollRow = goalRow #hack

  def cursorScrollToMiddle(self):
    maxy, maxx = self.view.cursorWindow.getmaxyx()
    rowDelta = min(len(self.lines)-maxy,
                   max(0, self.cursorRow-maxy/2))-self.scrollRow
    self.cursorMoveScroll(0, 0, 0, rowDelta, 0)

  def cursorStartOfLine(self):
    self.cursorMoveScroll(0, -self.cursorCol, -self.goalCol, 0, -self.scrollCol)
    self.redo()

  def cursorUp(self):
    self.selectionNone()
    self.cursorMoveUp()

  def cursorUpScroll(self):
    #todo:
    self.selectionNone()
    self.cursorMoveUp()

  def delCh(self):
    line = self.lines[self.cursorRow]
    change = ('d', line[self.cursorCol:self.cursorCol+1])
    self.redoAddChange(change)
    self.redo()

  def delete(self):
    """Delete character to right of cursor i.e. Del key."""
    if self.selectionMode != app.selectable.kSelectionNone:
      self.performDelete()
    elif self.cursorCol == len(self.lines[self.cursorRow]):
      if self.cursorRow+1 < len(self.lines):
        self.joinLines()
    else:
      self.delCh()

  def deleteToEndOfLine(self):
    line = self.lines[self.cursorRow]
    if self.cursorCol == len(self.lines[self.cursorRow]):
      if self.cursorRow+1 < len(self.lines):
        self.joinLines()
    else:
      change = ('d', line[self.cursorCol:])
      self.redoAddChange(change)
      self.redo()

  def editCopy(self):
    text = self.getSelectedText()
    if len(text):
      self.clipList.append(text)
      if self.selectionMode == app.selectable.kSelectionLine:
        text = text + ('',)
      clipboard.copy("\n".join(text))

  def editCut(self):
    self.editCopy()
    self.performDelete()

  def editPaste(self):
    osClip = clipboard.paste()
    if len(self.clipList or osClip):
      if self.selectionMode != app.selectable.kSelectionNone:
        self.performDelete()
      if osClip:
        clip = tuple(osClip.split("\n"))
      else:
        clip = self.clipList[-1]
      self.redoAddChange(('v', clip))
      self.redo()
      rowDelta = len(clip)-1
      if rowDelta == 0:
        endCol = self.cursorCol+len(clip[0])
      else:
        endCol = len(clip[-1])
      self.cursorMove(rowDelta, endCol-self.cursorCol,
          endCol-self.goalCol)
      self.redo()
    else:
      app.log.info('clipList empty')

  def fileClose(self):
    app.log.info('fileClose')
    if not self.file.closed:
      self.fileWrite()
      # todo handle error writing
      self.data = ""
      self.fullPath = ""
      self.relativePath = ""
      self.lines = []
      self.file.close()

  def fileFilter(self):
    def parse(line):
      return "\xfe%02x"%ord(line.groups()[0])
    self.data = self.file.read()
    self.lines = self.data.split('\r\n')
    if len(self.lines) == 1:
      self.lines = self.data.split('\n')
    if len(self.lines) == 1:
      self.lines = self.data.split('\r')
    self.lines = [re.sub('([\0-\x1f\x7f-\xff])', parse, i) for i in self.lines]
    self.savedAtRedoIndex = self.redoIndex

  def fileLoad(self, path):
    app.log.info('fileLoad', path)
    fullPath = os.path.expandvars(os.path.expanduser(path))
    try:
      self.file = open(fullPath, 'r+')
    except:
      try:
        # Create a new file.
        self.file = open(fullPath, 'w+')
        self.file.write('')
      except:
        app.log.info('error opening file', fullPath)
        return
    self.fullPath = fullPath
    self.relativePath = os.path.relpath(path, os.getcwd())
    app.log.info('fullPath', self.fullPath)
    app.log.info('cwd', os.getcwd())
    app.log.info('relativePath', self.relativePath)
    self.fileFilter()
    self.file.close()
    self.setKeywordsByFileType(os.path.splitext(fullPath)[1])

  def fileWrite(self):
    try:
      try:
        self.file = open(self.fullPath, 'r+')
        self.stripTrailingWhiteSpace()
        def encode(line):
          return chr(int(line.groups()[0], 16))
        assert re.sub('\xfe([0-9a-fA-F][0-9a-fA-F])', encode,
            "\xfe00") == "\x00"
        self.lines = [re.sub('\xfe([0-9a-fA-F][0-9a-fA-F])', encode, i)
            for i in self.lines]
        self.data = '\n'.join(self.lines)
        self.file.seek(0)
        self.file.truncate()
        self.file.write(self.data)
        self.file.close()
        self.savedAtRedoIndex = self.redoIndex
      except Exception as e:
        type_, value, tb = sys.exc_info()
        app.log.info('error writing file')
        out = traceback.format_exception(type_, value, tb)
        for i in out:
          app.log.info(i)
    except:
      app.log.info('except had exception')

  def selectText(self, lineNumber, start, length, mode):
    scrollTo = self.scrollRow
    maxy, maxx = self.view.cursorWindow.getmaxyx()
    if not (self.scrollRow < lineNumber <= self.scrollRow + maxy):
      scrollTo = max(lineNumber-10, 0)
    self.doSelectionMode(app.selectable.kSelectionNone)
    self.cursorMoveScroll(
        lineNumber-self.cursorRow,
        start+length-self.cursorCol,
        start+length-self.goalCol,
        scrollTo-self.scrollRow, 0)
    self.redo()
    self.doSelectionMode(mode)
    self.cursorMove(0, -length, -length)
    self.redo()

  def find(self, searchFor, direction=0):
    """direction is -1 for findPrior, 0 for at cursor, 1 for findNext."""
    app.log.info('find', searchFor, direction)
    if not len(searchFor):
      self.findRe = None
      self.doSelectionMode(app.selectable.kSelectionNone)
      return
    # The saved re is also used for highlighting.
    self.findRe = re.compile('()'+searchFor)
    self.findBackRe = re.compile('(.*)'+searchFor)
    self.findCurrentPattern(direction)

  def findCurrentPattern(self, direction):
    localRe = self.findRe
    if direction < 0:
      localRe = self.findBackRe
    if localRe is None:
      app.log.info('localRe is None')
      return
    # Current line.
    text = self.lines[self.cursorRow]
    if direction >= 0:
      text = text[self.cursorCol+direction:]
      offset = self.cursorCol+direction
    else:
      text = text[:self.cursorCol]
      offset = 0
    #app.log.info('find() searching', repr(text))
    found = localRe.search(text)
    if found:
      start = found.regs[1][1]
      end = found.regs[0][1]
      #app.log.info('found on line', self.cursorRow, start)
      self.selectText(self.cursorRow, offset+start, end-start,
          app.selectable.kSelectionCharacter)
      return
    # To end of file.
    if direction >= 0:
      theRange = range(self.cursorRow+1, len(self.lines))
    else:
      theRange = range(self.cursorRow-1, -1, -1)
    for i in theRange:
      found = localRe.search(self.lines[i])
      if found:
        if 0:
          for k in found.regs:
            app.log.info('AAA', k[0], k[1])
          app.log.info('b found on line', i, repr(found))
        start = found.regs[1][1]
        end = found.regs[0][1]
        self.selectText(i, start, end-start, app.selectable.kSelectionCharacter)
        return
    # Warp around to the start of the file.
    app.log.info('find hit end of file')
    if direction >= 0:
      theRange = range(self.cursorRow)
    else:
      theRange = range(len(self.lines)-1, self.cursorRow, -1)
    for i in theRange:
      found = localRe.search(self.lines[i])
      if found:
        #app.log.info('c found on line', i, repr(found))
        start = found.regs[1][1]
        end = found.regs[0][1]
        self.selectText(i, start, end-start, app.selectable.kSelectionCharacter)
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
      self.cursorMoveAndMark(0, -self.cursorCol, -self.goalCol,
          self.cursorRow-self.markerRow, self.cursorCol-self.markerCol, 0)
      self.redo()
      self.indentLines()
    elif self.selectionMode == app.selectable.kSelectionAll:
      self.cursorMoveAndMark(len(self.lines)-1-self.cursorRow, -self.cursorCol,
          -self.goalCol,
          -self.markerRow, -self.markerCol, app.selectable.kSelectionLine-self.selectionMode)
      self.redo()
      self.indentLines()
    else:
      self.cursorMoveAndMark(0, -self.cursorCol, -self.goalCol,
          0, -self.markerCol, app.selectable.kSelectionLine-self.selectionMode)
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
    deltaCol = self.cursorCol - self.scrollCol - maxCol + 1
    if deltaCol > 0:
      self.cursorMoveScroll(0, 0, 0, 0, deltaCol);
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
    self.redoAddChange(('m', (0, 0, 0, 0, 0, self.cursorRow-self.markerRow,
        self.cursorCol-self.markerCol, 0, 0, 0)))
    self.redo()

  def mouseClick(self, row, col, shift, ctrl, alt):
    if shift:
      app.log.info(' shift click', row, col, shift, ctrl, alt)
      if self.selectionMode == app.selectable.kSelectionNone:
        self.selectionCharacter()
      self.mouseRelease(row, col, shift, ctrl, alt)
    else:
      app.log.info(' click', row, col, shift, ctrl, alt)
      self.selectionNone()
      self.mouseRelease(row, col, shift, ctrl, alt)

  def mouseDoubleClick(self, row, col, shift, ctrl, alt):
    app.log.info('double click', row, col)
    if len(self.lines[self.scrollRow + row]):
      self.selectWordAt(self.scrollRow + row, self.scrollCol + col)

  def mouseMoved(self, row, col, shift, ctrl, alt):
    app.log.info(' mouseMoved', row, col, shift, ctrl, alt)
    self.mouseClick(row, col, True, ctrl, alt)

  def mouseRelease(self, row, col, shift, ctrl, alt):
    app.log.info(' mouse release', row, col)
    if not self.lines:
      return
    row = max(0, min(self.scrollRow + row, len(self.lines) - 1))
    inLine = col < len(self.lines[row])
    col = max(0, min(self.scrollCol + col, len(self.lines[row])))
    # Adjust the marker column delta when the cursor and marker positions
    # cross over each other.
    markerCol = 0
    if self.selectionMode == app.selectable.kSelectionWord:
      if self.cursorRow == self.markerRow:
        if row == self.cursorRow:
          if self.cursorCol > self.markerCol and col < self.markerCol:
            markerCol = 1
          elif self.cursorCol < self.markerCol and col >= self.markerCol:
            markerCol = -1
          app.log.debug('markerCol', markerCol)
        else:
          if (row < self.cursorRow and
              self.cursorCol > self.markerCol):
            markerCol = 1
          elif (row > self.cursorRow and
              self.cursorCol < self.markerCol):
            markerCol = -1
      elif row == self.markerRow:
        if col < self.markerCol and row < self.cursorRow:
          markerCol = 1
        elif col >= self.markerCol and row > self.cursorRow:
          markerCol = -1

    self.cursorMoveAndMark(row - self.cursorRow, col - self.cursorCol,
        col - self.goalCol, 0, markerCol, 0)
    self.redo()
    if self.selectionMode == app.selectable.kSelectionLine:
      self.cursorMoveAndMark(*self.extendSelection())
      self.redo()
    elif self.selectionMode == app.selectable.kSelectionWord:
      if (self.cursorRow < self.markerRow or
         (self.cursorRow == self.markerRow and
          self.cursorCol < self.markerCol)):
        self.cursorSelectWordLeft()
      elif inLine:
        self.cursorSelectWordRight()

  def mouseTripleClick(self, paneRow, paneCol, shift, ctrl, alt):
    app.log.info('triple click', paneRow, paneCol)
    self.mouseRelease(paneRow, paneCol, shift, ctrl, alt)
    self.selectLineAt(self.scrollRow + paneRow)

  def scrollWindow(self, rows, cols):
    self.cursorMoveScroll(rows, self.cursorColDelta(self.cursorRow-rows),
        0, -1, 0)
    self.redo()

  def mouseWheelDown(self, shift, ctrl, alt):
    if not shift:
      self.selectionNone()
    if self.scrollRow == 0:
      return
    maxy, maxx = self.view.cursorWindow.getmaxyx()
    cursorDelta = 0
    if self.cursorRow >= self.scrollRow + maxy - 2:
      cursorDelta = self.scrollRow + maxy - 2 - self.cursorRow
    self.cursorMoveScroll(cursorDelta,
        self.cursorColDelta(self.cursorRow+cursorDelta), 0, -1, 0)
    self.redo()

  def mouseWheelUp(self, shift, ctrl, alt):
    if not shift:
      self.selectionNone()
    maxy, maxx = self.view.cursorWindow.getmaxyx()
    if self.scrollRow+maxy >= len(self.lines):
      return
    cursorDelta = 0
    if self.cursorRow <= self.scrollRow + 1:
      cursorDelta = self.scrollRow-self.cursorRow + 1
    self.cursorMoveScroll(cursorDelta,
        self.cursorColDelta(self.cursorRow+cursorDelta), 0, 1, 0)
    self.redo()

  def nextSelectionMode(self):
    next = self.selectionMode + 1
    next %= app.selectable.kSelectionModeCount
    self.doSelectionMode(next)
    app.log.info('nextSelectionMode', self.selectionMode)

  def noOp(self, ignored):
    pass

  def doSelectionMode(self, mode):
    if self.selectionMode != mode:
      self.redoAddChange(('m', (0, 0, 0, 0, 0,
          self.cursorRow-self.markerRow,
          self.cursorCol-self.markerCol, 0, 0,
          mode-self.selectionMode)))
      self.redo()

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
    self.selectionLine()
    self.cursorMoveAndMark(*self.extendSelection())
    self.redo()

  def selectWordAt(self, row, col):
    row = max(0, min(row, len(self.lines)-1))
    inLine = col < len(self.lines[row])
    col = max(0, min(col, len(self.lines[row])-1))
    self.selectText(row, col, 0, app.selectable.kSelectionWord)
    if inLine:
      self.cursorSelectWordRight()

  def splitLine(self):
    """split the line into two at current column."""
    self.redoAddChange(('n', (1,)))
    self.redo()

  def swapCursorAndMarker(self):
    app.log.info('swapCursorAndMarker')
    self.cursorMoveAndMark(self.markerRow-self.cursorRow,
        self.markerCol-self.cursorCol,
        self.markerCol-self.goalCol,
        self.cursorRow-self.markerRow,
        self.cursorCol-self.markerCol, 0)
    self.redo()

  def test(self):
    app.log.info('test')
    self.insertPrintable(0x00)

  def stripTrailingWhiteSpace(self):
    for i in range(len(self.lines)):
      self.lines[i] = self.lines[i].rstrip()

  def unindent(self):
    if self.selectionMode == app.selectable.kSelectionAll:
      self.cursorMoveAndMark(len(self.lines)-1-self.cursorRow, -self.cursorCol,
          -self.goalCol,
          -self.markerRow, -self.markerCol, kSelectionLine-self.selectionMode)
      self.redo()
      self.unindentLines()
    else:
      self.cursorMoveAndMark(0, -self.cursorCol, -self.goalCol,
          0, -self.markerCol, app.selectable.kSelectionLine-self.selectionMode)
      self.redo()
      self.unindentLines()

  def unindentLines(self):
    upperRow = min(self.markerRow, self.cursorRow)
    lowerRow = max(self.markerRow, self.cursorRow)
    app.log.info('unindentLines', upperRow, lowerRow)
    for line in self.lines[upperRow:lowerRow+1]:
      if ((len(line) == 1 and line[:1] != ' ') or
          (len(line) >= 2 and line[:2] != '  ')):
        # Handle multi-delete.
        return
    self.redoAddChange(('vd', ('  ')))
    self.redo()



class TextBuffer(BackingTextBuffer):
  """The TextBuffer adds the drawing/rendering to the BackingTextBuffer."""
  def __init__(self):
    BackingTextBuffer.__init__(self)
    self.lineLimitIndicator = sys.maxint
    self.highlightRe = None

  def setKeywordsByFileType(self, extension):
    grammar = app.prefs.util.getGrammar(extension)
    if grammar:
      self.setKeywords(grammar.get('keywords', [])+
          grammar.get('namespaces', [])+
          grammar.get('types', []))

  def setKeywords(self, highlightKeywords):
      keywords = '\\b%s\\b'%('\\b|\\b'.join(highlightKeywords),)
      self.highlightRe = re.compile(keywords)

  def scrollToCursor(self, window):
    """Move the selected view rectangle so that the cursor is visible."""
    maxy, maxx = window.cursorWindow.getmaxyx()
    #     self.cursorRow >= self.scrollRow+maxy 1 0
    rows = 0
    if self.scrollRow > self.cursorRow:
      rows = self.cursorRow - self.scrollRow
      app.log.error('AAA self.scrollRow > self.cursorRow',
          self.scrollRow, self.cursorRow, self)
    elif self.cursorRow >= self.scrollRow+maxy:
      rows = self.cursorRow - (self.scrollRow+maxy-1)
      app.log.error('BBB self.cursorRow >= self.scrollRow+maxy',
          self.cursorRow, self.scrollRow, maxy, self)
    cols = 0
    if self.scrollCol > self.cursorCol:
      cols = self.cursorCol - self.scrollCol
      app.log.error('CCC self.scrollCol > self.cursorCol',
          self.scrollCol, self.cursorCol, self)
    elif self.cursorCol >= self.scrollCol+maxx:
      cols = self.cursorCol - (self.scrollCol+maxx-1)
      app.log.error('DDD self.cursorCol >= self.scrollCol+maxx',
          self.cursorCol, self.scrollCol, maxx, self)
    assert not rows
    assert not cols
    self.scrollRow += rows
    self.scrollCol += cols

  def draw(self, window):
    if 1: #self.scrollRow != self.scrollToRow:
      maxy, maxx = window.cursorWindow.getmaxyx()

      self.scrollToCursor(window)

      startCol = self.scrollCol
      endCol = self.scrollCol+maxx

      # Draw to screen.
      limit = min(max(len(self.lines)-self.scrollRow, 0), maxy)
      for i in range(limit):
        line = self.lines[self.scrollRow+i][startCol:endCol]
        window.addStr(i, 0, line + ' '*(maxx-len(line)), window.color)
      if self.highlightRe:
        # Highlight keywords.
        for i in range(limit):
          line = self.lines[self.scrollRow+i][startCol:endCol]
          for k in self.highlightRe.finditer(line):
            for f in k.regs:
              window.addStr(i, f[0], line[f[0]:f[1]], curses.color_pair(21))
      if 1:
        # Trivia: all English contractions except 'sup, 'tis and 'twas will
        # match this regex (with re.I):  [adegIlnotuwy]'[acdmlsrtv]
        # The prefix part of that is used in the expression below to identify
        # English contractions.
        # r"(\"(\\\"|[^\"])*?\")|(?<![adegIlnotuwy])('(\\\'|[^'])*?')",

        # Highlight strings.
        for i in range(limit):
          line = self.lines[self.scrollRow+i][startCol:endCol]
          for k in re.finditer(app.selectable.kReStrings, line):
            for f in k.regs:
              window.addStr(i, f[0], line[f[0]:f[1]], curses.color_pair(5))
      if 1:
        # Highlight comments.
        for i in range(limit):
          line = self.lines[self.scrollRow+i][startCol:endCol]
          for k in re.finditer(app.selectable.kReComments, line):
            for f in k.regs:
              window.addStr(i, f[0], line[f[0]:f[1]], curses.color_pair(2))
      if 1:
        # Highlight brackets.
        for i in range(limit):
          line = self.lines[self.scrollRow+i][startCol:endCol]
          for k in re.finditer(app.selectable.kReBrackets, line):
            for f in k.regs:
              window.addStr(i, f[0], line[f[0]:f[1]], curses.color_pair(6))
      if 1:
        # Match brackets.
        if (len(self.lines) > self.cursorRow and
            len(self.lines[self.cursorRow]) > self.cursorCol):
          ch = self.lines[self.cursorRow][self.cursorCol]
          def searchBack(closeCh, openCh):
            count = -1
            for row in range(self.cursorRow, self.scrollRow, -1):
              line = self.lines[row]
              if row == self.cursorRow:
                line = line[:self.cursorCol]
              found = [i for i in
                  re.finditer("(\\"+openCh+")|(\\"+closeCh+")", line)]
              for i in reversed(found):
                if i.group() == openCh:
                  count += 1
                else:
                  count -= 1
                if count == 0:
                  if i.start()+self.cursorCol-self.scrollCol < maxx:
                    window.addStr(row-self.scrollRow, i.start(), openCh,
                        curses.color_pair(201))
                  return
          def searchForward(openCh, closeCh):
            count = 1
            colOffset = self.cursorCol+1
            for row in range(self.cursorRow, self.scrollRow+maxy):
              if row != self.cursorRow:
                colOffset = 0
              line = self.lines[row][colOffset:]
              for i in re.finditer("(\\"+openCh+")|(\\"+closeCh+")", line):
                if i.group() == openCh:
                  count += 1
                else:
                  count -= 1
                if count == 0:
                  if i.start()+self.cursorCol-self.scrollCol < maxx:
                    window.addStr(row-self.scrollRow, colOffset+i.start(),
                        closeCh, curses.color_pair(201))
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
            window.addStr(self.cursorRow-self.scrollRow,
                self.cursorCol-self.scrollCol,
                self.lines[self.cursorRow][self.cursorCol],
                curses.color_pair(201))
      if 1:
        # Highlight numbers.
        for i in range(limit):
          line = self.lines[self.scrollRow+i][startCol:endCol]
          for k in re.finditer(app.selectable.kReNumbers, line):
            for f in k.regs:
              window.addStr(i, f[0], line[f[0]:f[1]], curses.color_pair(31))
      lengthLimit = self.lineLimitIndicator
      if endCol >= lengthLimit:
        # Highlight long lines.
        for i in range(limit):
          line = self.lines[self.scrollRow+i]
          if len(line) < lengthLimit or startCol > lengthLimit:
            continue
          length = min(endCol, len(line)-lengthLimit)
          window.addStr(i, lengthLimit-startCol, line[lengthLimit:endCol],
              curses.color_pair(96))
      if self.findRe is not None:
        # Highlight find.
        for i in range(limit):
          line = self.lines[self.scrollRow+i][startCol:endCol]
          for k in self.findRe.finditer(line):
            f = k.regs[0]
            #for f in k.regs[1:]:
            window.addStr(i, f[0], line[f[0]:f[1]], curses.color_pair(32))
      if limit and self.selectionMode != app.selectable.kSelectionNone:
        # Highlight selected text.
        upperRow, upperCol, lowerRow, lowerCol = self.startAndEnd()
        selStartCol = max(upperCol - startCol, 0)
        selEndCol = min(lowerCol - startCol, maxx)
        start = max(0, min(upperRow-self.scrollRow, maxy))
        end = max(0, min(lowerRow-self.scrollRow, maxy))
        if self.selectionMode == app.selectable.kSelectionBlock:
          for i in range(start, end+1):
            line = self.lines[self.scrollRow+i][selStartCol:selEndCol]
            window.addStr(i, selStartCol, line, window.colorSelected)
        elif (self.selectionMode == app.selectable.kSelectionAll or
            self.selectionMode == app.selectable.kSelectionCharacter or
            self.selectionMode == app.selectable.kSelectionWord):
          # Go one row past the selection or to the last line.
          for i in range(start, min(end+1, len(self.lines)-self.scrollRow)):
            line = self.lines[self.scrollRow+i][startCol:endCol]
            if len(line) == len(self.lines[self.scrollRow+i]):
              line += " "  # Maybe do: "\\n".
            if i == end and i == start:
              window.addStr(i, selStartCol,
                  line[selStartCol:selEndCol], window.colorSelected)
            elif i == end:
              window.addStr(i, 0, line[:selEndCol], window.colorSelected)
            elif i == start:
              window.addStr(i, selStartCol, line[selStartCol:],
                  window.colorSelected)
            else:
              window.addStr(i, 0, line, window.colorSelected)
        elif self.selectionMode == app.selectable.kSelectionLine:
          for i in range(start, end+1):
            line = self.lines[self.scrollRow+i][selStartCol:maxx]
            window.addStr(i, selStartCol,
                line+' '*(maxx-len(line)), window.colorSelected)
      for i in range(limit, maxy):
        window.addStr(i, 0, ' '*maxx, window.color)
