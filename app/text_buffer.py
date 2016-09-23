# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import third_party.pyperclip as clipboard
import curses.ascii
import os
import re
import sys
import traceback

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
];


kReBrackets = re.compile('[[\]{}()]')
kReNumbers = re.compile('0x[0-9a-fA-F]+|\d+')
kReStrings = re.compile(
    r"(\"\"\".*?(?<!\\)\"\"\")|('''.*?(?<!\\)''')|(\".*?(?<!\\)\")|('.*?(?<!\\)')")
kReWordBoundary = re.compile('(?:\w+)|(?:\W+)')


def addVectors(a, b):
  """Add two list-like objects, pair-wise."""
  return tuple([a[i]+b[i] for i in range(len(a))])


class BufferManager:
  """Manage a set of text buffers. Some text buffers may be hidden."""
  def __init__(self, prg):
    self.prg = prg
    self.buffers = {}

  def loadTextBuffer(self, path):
    expandedPath = os.path.abspath(os.path.expanduser(os.path.expandvars(path)))
    textBuffer = self.buffers.get(path, None)
    self.prg.log('X textBuffer', repr(textBuffer));
    if not textBuffer:
      self.prg.log(' loadTextBuffer new')
      textBuffer = TextBuffer(self.prg)
      if os.path.isfile(expandedPath):
        textBuffer.fileLoad(expandedPath)
      elif os.path.isdir(expandedPath):
        self.prg.log('Tried to open directory as a file', expandedPath)
        return
      else:
        textBuffer.fileCreate(expandedPath)
    self.buffers[expandedPath] = textBuffer
    for i,k in self.buffers.items():
      self.prg.log('  ', i)
      self.prg.log('    ', k)
      self.prg.log('    ', repr(k.lines))
      self.prg.log('    ', len(k.lines) and k.lines[0])
    self.prg.log(' loadTextBuffer')
    self.prg.log(expandedPath)
    self.prg.log(' loadTextBuffer')
    self.prg.log(repr(textBuffer))
    return textBuffer

  def fileClose(self, path):
    pass


class Selectable:
  def __init__(self):
    self.markerRow = 0
    self.markerCol = 0
    self.cursorRow = 0
    self.cursorCol = 0
    self.selectionMode = kSelectionNone

  def getSelection(self):
    upperRow, upperCol, lowerRow, lowerCol = self.startAndEnd()
    return (upperRow, upperCol, lowerRow, lowerCol, self.selectionMode)

  def setSelection(self, other):
    (self.markerRow, self.markerCol, self.cursorRow, self.cursorCol,
        self.selectionMode) = other

  def getSelectedText(self, buffer):
    upperRow, upperCol, lowerRow, lowerCol = self.startAndEnd()
    return self.getText(buffer, upperRow, upperCol, lowerRow, lowerCol)

  def getText(self, buffer, upperRow, upperCol, lowerRow, lowerCol):
    lines = []
    if self.selectionMode == kSelectionAll:
      lines = buffer.lines[:]
    elif self.selectionMode == kSelectionBlock:
      for i in range(upperRow, lowerRow+1):
        lines.append(buffer.lines[i][upperCol:lowerCol])
    elif (self.selectionMode == kSelectionCharacter or
        self.selectionMode == kSelectionWord):
      if upperRow == lowerRow:
        lines.append(buffer.lines[upperRow][upperCol:lowerCol])
      else:
        for i in range(upperRow, lowerRow+1):
          if i == upperRow:
            lines.append(buffer.lines[i][upperCol:])
          elif i == lowerRow:
            lines.append(buffer.lines[i][:lowerCol])
          else:
            lines.append(buffer.lines[i])
    elif self.selectionMode == kSelectionLine:
      for i in range(upperRow, lowerRow+1):
        lines.append(buffer.lines[i])
      if len(lines):
        lines.append('')
    return tuple(lines)

  def doDeleteSelection(self, buffer):
    upperRow, upperCol, lowerRow, lowerCol = self.startAndEnd()
    if self.selectionMode == kSelectionAll:
      buffer.lines = [""]
    elif self.selectionMode == kSelectionBlock:
      for i in range(upperRow, lowerRow+1):
        line = buffer.lines[i]
        buffer.lines[i] = line[:upperCol] + line[lowerCol:]
    elif (self.selectionMode == kSelectionCharacter or
        self.selectionMode == kSelectionWord):
      if upperRow == lowerRow:
        line = buffer.lines[upperRow]
        buffer.lines[upperRow] = line[:upperCol] + line[lowerCol:]
      elif upperCol == 0 and lowerCol == 0:
        del self.lines[upperRow:lowerRow]
      else:
        buffer.lines[upperRow] = (buffer.lines[upperRow][:upperCol] +
            buffer.lines[lowerRow][lowerCol:])
        upperRow += 1
        del self.lines[upperRow:lowerRow+1]
    elif self.selectionMode == kSelectionLine:
      del self.lines[upperRow:lowerRow+1]

  def insertLines(self, buffer, lines):
    if len(lines) == 0:
      return
    if (self.selectionMode == kSelectionNone or
        self.selectionMode == kSelectionCharacter or
        self.selectionMode == kSelectionWord):
      firstLine = buffer.lines[self.cursorRow]
      if len(lines) == 1:
        buffer.lines[self.cursorRow] = (firstLine[:self.cursorCol] + lines[0] +
            firstLine[self.cursorCol:])
        self.cursorCol += len(lines[-1])
      else:
        buffer.lines[self.cursorRow] = firstLine[:self.cursorCol] + lines[0]
        for line in lines[1:-1]:
          self.cursorRow += 1
          buffer.lines.insert(self.cursorRow, line)
        self.cursorRow += 1
        buffer.lines.insert(self.cursorRow,
            lines[-1] + firstLine[self.cursorCol:])
        self.cursorCol = len(lines[-1])
      self.goalCol = self.cursorCol
    elif self.selectionMode == kSelectionAll:
      self.lines = list(lines)
    elif self.selectionMode == kSelectionBlock:
      for line in lines:
        buffer.lines[self.cursorRow] = (
            buffer.lines[self.cursorRow][:self.cursorCol] + line +
            buffer.lines[self.cursorRow][self.cursorCol:])
        self.cursorRow += 1
      self.goalCol = self.cursorCol
    elif self.selectionMode == kSelectionLine:
      for line in lines:
        buffer.lines.insert(self.cursorRow, line)
        self.cursorRow += 1
      self.goalCol = self.cursorCol
    else:
      buffer.log('selection mode not recognized', self.selectionMode)

  def selectUpper(self):
    self.cursorRow, self.cursorCol, a,b = self.startAndEnd()
    self.selectionMode = kSelectionNone

  def selectLower(self):
    a,b, self.cursorRow, self.cursorCol = self.startAndEnd()
    self.selectionMode = kSelectionNone

  def startAndEnd(self):
    upperRow = 0
    upperCol = 0
    lowerRow = 0
    lowerCol = 0
    if self.selectionMode == kSelectionNone:
      upperRow = self.cursorRow
      upperCol = self.cursorCol
      lowerRow = self.cursorRow
      lowerCol = self.cursorCol
    elif self.selectionMode == kSelectionAll:
      upperRow = 0
      upperCol = 0
      lowerRow = len(self.lines)
      lowerCol = lowerRow and len(self.lines[-1])
    elif self.selectionMode == kSelectionBlock:
      upperRow = min(self.markerRow, self.cursorRow)
      upperCol = min(self.markerCol, self.cursorCol)
      lowerRow = max(self.markerRow, self.cursorRow)
      lowerCol = max(self.markerCol, self.cursorCol)
    elif self.selectionMode == kSelectionCharacter:
      upperRow = self.markerRow
      upperCol = self.markerCol
      lowerRow = self.cursorRow
      lowerCol = self.cursorCol
      if upperRow == lowerRow and upperCol > lowerCol:
        upperCol, lowerCol = lowerCol, upperCol
      elif upperRow > lowerRow:
        upperRow, lowerRow = lowerRow, upperRow
        upperCol, lowerCol = lowerCol, upperCol
    elif self.selectionMode == kSelectionLine:
      upperRow = min(self.markerRow, self.cursorRow)
      upperCol = 0
      lowerRow = max(self.markerRow, self.cursorRow)
      lowerCol = sys.maxint
    elif self.selectionMode == kSelectionWord:
      upperRow = self.markerRow
      upperCol = self.markerCol
      lowerRow = self.cursorRow
      lowerCol = self.cursorCol
      if upperRow == lowerRow and upperCol > lowerCol:
        upperCol, lowerCol = lowerCol, upperCol
      elif upperRow > lowerRow:
        upperRow, lowerRow = lowerRow, upperRow
        upperCol, lowerCol = lowerCol, upperCol
      if upperRow == lowerRow:
        line = self.lines[upperRow]
        for segment in re.finditer(kReWordBoundary, line):
          if segment.start() <= upperCol < segment.end():
            upperCol = segment.start()
          if segment.start() < lowerCol < segment.end():
            lowerCol = segment.end()
            break
      else:
        line = self.lines[upperRow]
        for segment in re.finditer(kReWordBoundary, line):
          if segment.start() <= upperCol < segment.end():
            upperCol = segment.start()
            break
        line = self.lines[lowerRow]
        for segment in re.finditer(kReWordBoundary, line):
          if segment.start() < lowerCol < segment.end():
            lowerCol = segment.end()
            break
    return (upperRow, upperCol, lowerRow, lowerCol)

  def highlight(self, maxRow, maxCol):
    upperRow, upperCol, lowerRow, lowerCol = self.startAndEnd()
    selStartCol = max(upperCol - startCol, 0)
    selEndCol = min(lowerCol - startCol, maxCol)
    start = max(0, upperRow-self.scrollRow)
    end = min(lowerRow-self.scrollRow, maxRow)

    if self.selectionMode == kSelectionBlock:
      for i in range(start, end+1):
        line = self.lines[self.scrollRow+i][selStartCol:selEndCol]
        self.cursorWindow.addstr(i, selStartCol, line, curses.color_pair(3))
    elif (self.selectionMode == kSelectionCharacter or
        self.selectionMode == kSelectionWord):
      for i in range(start, end+1):
        line = self.lines[self.scrollRow+i][startCol:endCol]
        try:
          if i == end and i == start:
            self.prg.log('startCol', startCol, 'endCol', endCol, repr(line))
            self.cursorWindow.addstr(i, selStartCol,
                line[selStartCol:selEndCol], curses.color_pair(3))
          elif i == end:
            self.cursorWindow.addstr(i, 0, line[:selEndCol],
                curses.color_pair(3))
          elif i == start:
            self.cursorWindow.addstr(i, selStartCol, line[selStartCol:],
                curses.color_pair(3))
          else:
            self.cursorWindow.addstr(i, 0, line, curses.color_pair(3))
        except:
          pass
    elif self.selectionMode == kSelectionLine:
      for i in range(start, end+1):
        line = self.lines[self.scrollRow+i][selStartCol:selEndCol]
        try:
          self.cursorWindow.addstr(i, selStartCol,
              line+' '*(maxx-len(line)), curses.color_pair(3))
        except:
          pass


class BackingTextBuffer(Selectable):
  def __init__(self, prg):
    Selectable.__init__(self)
    self.prg = prg
    self.clipList = []
    self.debugRedo = False
    self.findRe = None
    self.goalCol = 0
    self.lines = []
    self.scrollRow = 0
    self.scrollToRow = 0
    self.scrollCol = 0
    self.redoChain = []
    self.redoIndex = 0
    self.savedAtRedoIndex = 0

  def addLine(self, msg):
    self.lines.append(msg)
    self.cursorRow += 1

  def isDirty(self):
    return self.savedAtRedoIndex != self.redoIndex

  def backspace(self):
    if self.selectionMode != kSelectionNone:
      self.redoAddChange(('ds', self.getSelection(),
          self.getSelectedText(self)))
      self.redo()
    elif self.cursorCol == 0:
      if self.cursorRow > 0:
        self.cursorLeft()
        self.joinLines()
    else:
      line = self.lines[self.cursorRow]
      change = ('b', line[self.cursorCol-1:self.cursorCol])
      self.redoAddChange(change)
      self.redo()

  def carrageReturn(self):
    self.redoAddChange(('n', (1, -self.cursorCol, -self.goalCol)))
    self.redo()
    if 1: # todo: if indent on CR
      line = self.lines[self.cursorRow-1]
      indent = 0
      while indent < len(line) and line[indent] == ' ':
        indent += 1
      if indent:
        self.redoAddChange(('i', ' '*indent));
        self.redo()

  def cursorCrLf(self):
    maxy, maxx = self.prg.inputWindow.cursorWindow.getmaxyx() #hack
    rows = 0
    if self.cursorRow == self.scrollRow+maxy:
      rows = 1
    self.cursorMoveScroll(1, -self.cursorCol, -self.goalCol, rows,
        -self.scrollCol)
    self.redo()

  def cursorColDelta(self, toRow):
    if toRow >= len(self.lines):
      return
    lineLen = len(self.lines[toRow])
    if self.goalCol <= lineLen:
      return self.goalCol - self.cursorCol
    return lineLen - self.cursorCol

  def cursorDown(self):
    if self.cursorRow+1 < len(self.lines):
      self.cursorMove(1, self.cursorColDelta(self.cursorRow+1), 0)
      self.redo()

  def cursorLeft(self):
    self.selectionNone()
    self.cursorMoveLeft()

  def cursorMove(self, rowDelta, colDelta, goalColDelta):
    self.cursorMoveAndMark(rowDelta, colDelta, goalColDelta, 0, 0, 0)

  def cursorMoveAndMark(self, rowDelta, colDelta, goalColDelta, markRowDelta,
      markColDelta, selectionModeDelta):
    maxy, maxx = self.prg.inputWindow.cursorWindow.getmaxyx() #hack
    rows = 0
    if self.scrollRow > self.cursorRow+rowDelta:
      rows = self.cursorRow+rowDelta - self.scrollRow
    elif self.cursorRow+rowDelta >= self.scrollRow+maxy:
      rows = self.cursorRow+rowDelta - (self.scrollRow+maxy-1)
    cols = 0
    if self.scrollCol > self.cursorCol+colDelta:
      cols = self.cursorCol+colDelta - self.scrollCol
    elif self.cursorCol+colDelta >= self.scrollCol+maxx:
      cols = self.cursorCol+colDelta - (self.scrollCol+maxx-1)
    self.redoAddChange(('m', (rowDelta, colDelta, goalColDelta, rows, cols,
        markRowDelta, markColDelta, selectionModeDelta)))

  def cursorMoveScroll(self, rowDelta, colDelta, goalColDelta,
      scrollRowDelta, scrollColDelta):
    self.redoAddChange(('m', (rowDelta, colDelta, goalColDelta, scrollRowDelta,
        scrollColDelta,0,0,0)))

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

  def cursorRight(self):
    self.selectionNone()
    self.cursorMoveRight()

  def cursorSelectLeft(self):
    if self.selectionMode == kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveLeft()

  def cursorSelectRight(self):
    if self.selectionMode == kSelectionNone:
      self.selectionCharacter()
    self.cursorMoveRight()

  def cursorEndOfLine(self):
    lineLen = len(self.lines[self.cursorRow])
    self.cursorMove(0, lineLen-self.cursorCol, lineLen-self.goalCol)
    self.redo()

  def cursorPageDown(self):
    if self.cursorRow == len(self.lines):
      return
    maxy, maxx = self.prg.inputWindow.cursorWindow.getmaxyx() #hack
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
    maxy, maxx = self.prg.inputWindow.cursorWindow.getmaxyx() #hack
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

  def cursorStartOfLine(self):
    self.cursorMoveScroll(0, -self.cursorCol, -self.goalCol, 0, -self.scrollCol)
    self.redo()

  def cursorUp(self):
    if self.cursorRow > 0:
      lineLen = len(self.lines[self.cursorRow-1])
      if self.goalCol <= lineLen:
        self.cursorMove(-1, self.goalCol - self.cursorCol, 0)
        self.redo()
      else:
        self.cursorMove(-1, lineLen - self.cursorCol, 0)
        self.redo()

  def delCh(self):
    line = self.lines[self.cursorRow]
    change = ('d', line[self.cursorCol:self.cursorCol+1])
    self.redoAddChange(change)
    self.redo()

  def delete(self):
    """Delete character to right of cursor i.e. Del key."""
    if self.selectionMode != kSelectionNone:
      self.redoAddChange(('ds', self.getSelection(),
          self.getSelectedText(self)))
      self.redo()
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
    text = self.getSelectedText(self)
    if len(text):
      self.clipList.append(text)
      clipboard.copy("\n".join(text))

  def editCut(self):
    text = self.getSelectedText(self)
    if len(text):
      self.clipList.append(text)
      self.redoAddChange(('ds', self.getSelection(), text))
      self.redo()

  def editPaste(self):
    osClip = clipboard.paste()
    if len(self.clipList or osClip):
      if self.selectionMode != kSelectionNone:
        self.redoAddChange(('ds', self.getSelection(),
            self.getSelectedText(self)))
        self.redo()
      if osClip:
        clip = tuple(osClip.split("\n"))
      else:
        clip = self.clipList[-1]
      self.redoAddChange(('v', clip))
      self.redo()
    else:
      self.prg.log('clipList empty')

  def fileClose(self):
    self.prg.log('fileClose')
    if not self.file.closed:
      self.fileWrite()
      # todo handle error writing
      self.data = ""
      self.fullPath = ""
      self.lines = []
      self.file.close()

  def fileCreate(self, path):
    self.file = open(os.path.expandvars(os.path.expanduser(path)), 'w+')
    self.fileFilter()
    self.savedAtRedoIndex = self.redoIndex

  def fileFilter(self):
    def parse(line):
      return "\xfe%02x"%ord(line.groups()[0])
    self.data = self.file.read()
    self.lines = self.data.split('\r\n')
    if len(self.lines) == 1:
      self.lines = self.data.split('\n')
    if len(self.lines) == 1:
      self.lines = self.data.split('\r')
    #self.lines[0] += "\x00\x01\x1f\x7f\xff"
    self.lines = [re.sub('([\0-\x1f\x7f-\xff])', parse, i) for i in self.lines]
    #self.prg.log('lines', len(self.lines), self)
    self.savedAtRedoIndex = self.redoIndex

  def fileLoad(self, path):
    self.prg.log('fileLoad', path)
    fullPath = os.path.expandvars(os.path.expanduser(path))
    try:
      self.file = open(fullPath, 'r+')
    except:
      try:
        self.file = open(fullPath, 'w+')
      except:
        self.prg.log('error opening file', fullPath)
        return
    self.fullPath = fullPath
    self.fileFilter()
    self.file.close()

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
        self.prg.log('error writing file')
        out = traceback.format_exception(type_, value, tb)
        for i in out:
          self.prg.log(i)
    except:
      self.prg.log('except had exception')

  def selectText(self, lineNumber, start, length, mode):
    scrollTo = self.scrollRow
    maxy, maxx = self.prg.inputWindow.cursorWindow.getmaxyx() #hack
    if not (self.scrollRow < lineNumber <= self.scrollRow + maxy):
      scrollTo = max(lineNumber-10, 0)
    self.doSelectionMode(kSelectionNone)
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
    self.prg.log('find', searchFor, direction)
    if not len(searchFor):
      self.findRe = None
      self.doSelectionMode(kSelectionNone)
      return
    searchForLen = len(searchFor)
    # Current line.
    text = self.lines[self.cursorRow]
    if direction >= 0:
      searchFor = '('+searchFor+')'
      text = text[self.cursorCol+direction:]
      offset = self.cursorCol+direction
    else:
      searchFor = '(?:.*)('+searchFor+')'
      text = text[:self.cursorCol]
      offset = 0
    self.findRe = re.compile(searchFor)
    found = self.findRe.search(text)
    if found:
      start = found.regs[-1][0]
      end = found.regs[-1][1]
      self.prg.log('a found on line', self.cursorRow, start)
      self.selectText(self.cursorRow, offset+start, end-start,
          kSelectionCharacter)
      return
    # To end of file.
    if direction >= 0:
      theRange = range(self.cursorRow+1, len(self.lines))
    else:
      theRange = range(self.cursorRow-1, -1, -1)
    for i in theRange:
      found = re.search(searchFor, self.lines[i])
      if found:
        self.prg.log('b found on line', i, repr(found))
        start = found.regs[-1][0]
        end = found.regs[-1][1]
        self.selectText(i, start, end-start, kSelectionCharacter)
        return
    # Warp around to the start of the file.
    self.prg.log('find hit end of file')
    if direction >= 0:
      theRange = range(self.cursorRow)
    else:
      theRange = range(len(self.lines)-1, self.cursorRow, -1)
    for i in theRange:
      found = re.search(searchFor, self.lines[i])
      if found:
        self.prg.log('c found on line', i, repr(found))
        start = found.regs[-1][0]
        end = found.regs[-1][1]
        self.selectText(i, start, end-start, kSelectionCharacter)
        return
    self.prg.log('find not found')

  def findNext(self, searchFor):
    self.find(searchFor, 1)

  def findPrior(self, searchFor):
    self.find(searchFor, -1)

  def indent(self):
    if self.selectionMode == kSelectionNone:
      self.cursorMoveAndMark(0, -self.cursorCol, -self.goalCol,
          self.cursorRow-self.markerRow, self.cursorCol-self.markerCol, 0)
      self.redo()
      self.indentLines()
    elif self.selectionMode == kSelectionAll:
      self.cursorMoveAndMark(len(self.lines)-1-self.cursorRow, -self.cursorCol,
          -self.goalCol,
          -self.markerRow, -self.markerCol, kSelectionLine-self.selectionMode)
      self.redo()
      self.indentLines()
    else:
      col = min(self.cursorCol, self.markerCol)
      self.cursorMoveAndMark(0, col-self.cursorCol, col-self.goalCol,
          0, col-self.markerCol, kSelectionLine-self.selectionMode)
      self.redo()
      self.indentLines()

  def indentLines(self):
    self.redoAddChange(('vi', ('  ')))
    self.redo()

  def verticalInsert(self, row, endRow, col, text):
    self.redoAddChange(('vi', (text)))
    self.redo()

  def insert(self, text):
    if self.selectionMode != kSelectionNone:
      self.redoAddChange(('ds', self.getSelection(),
          self.getSelectedText(self)))
      self.redo()
    self.redoAddChange(('i', text))
    self.redo()

  def insertPrintable(self, ch):
    self.prg.log('insertPrintable')
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
        self.cursorCol-self.markerCol, 0)))
    self.redo()

  def mouseClick(self, row, col, shift, ctrl, alt):
    if shift:
      self.prg.log(' shift click', row, col, shift, ctrl, alt)
      if self.selectionMode == kSelectionNone:
        self.selectionCharacter()
      self.mouseRelease(row, col, shift, ctrl, alt)
    else:
      self.prg.log(' click', row, col, shift, ctrl, alt)
      self.mouseRelease(row, col, shift, ctrl, alt)
      self.selectionNone()

  def mouseDoubleClick(self, row, col, shift, ctrl, alt):
    self.prg.log('double click', row, col)
    self.selectWordAt(self.scrollRow + row, self.scrollCol + col)

  def mouseMoved(self, row, col, shift, ctrl, alt):
    self.prg.log(' mouseMoved', row, col, shift, ctrl, alt)
    self.mouseClick(row, col, True, ctrl, alt)

  def mouseRelease(self, row, col, shift, ctrl, alt):
    self.prg.log(' mouse release', row, col)
    if not self.lines:
      return
    row = max(0, min(self.scrollRow + row, len(self.lines) - 1))
    col = max(0, min(self.scrollCol + col, len(self.lines[row])))
    self.cursorMove(row - self.cursorRow, col - self.cursorCol,
        col - self.goalCol)
    self.redo()

  def mouseTripleClick(self, row, col, shift, ctrl, alt):
    self.prg.log('triple click', row, col)
    self.mouseRelease(row, col, shift, ctrl, alt)
    self.selectionLine()

  def scrollWindow(self, rows, cols):
    self.cursorMoveScroll(rows, self.cursorColDelta(self.cursorRow-rows),
        0, -1, 0)
    self.redo()

  def mouseWheelDown(self, shift, ctrl, alt):
    if not shift:
      self.selectionNone()
    if self.scrollRow == 0:
      return
    maxy, maxx = self.prg.inputWindow.cursorWindow.getmaxyx() #hack
    cursorDelta = 0
    if self.cursorRow >= self.scrollRow + maxy - 2:
      cursorDelta = self.scrollRow + maxy - 2 - self.cursorRow
    self.cursorMoveScroll(cursorDelta,
        self.cursorColDelta(self.cursorRow+cursorDelta), 0, -1, 0)
    self.redo()

  def mouseWheelUp(self, shift, ctrl, alt):
    if not shift:
      self.selectionNone()
    maxy, maxx = self.prg.inputWindow.cursorWindow.getmaxyx() #hack
    if self.scrollRow+maxy >= len(self.lines):
      return
    cursorDelta = 0
    if self.cursorRow <= self.scrollRow + 1:
      cursorDelta = self.scrollRow-self.cursorRow + 1
    self.cursorMoveScroll(cursorDelta,
        self.cursorColDelta(self.cursorRow+cursorDelta), 0, 1, 0)
    self.redo()

  def nextSelectionMode(self):
    self.selectionMode += 1
    self.selectionMode %= kSelectionModeCount
    self.prg.log('nextSelectionMode', self.selectionMode)

  def noOp(self, ignored):
    pass

  def doSelectionMode(self, mode):
    if self.selectionMode != mode:
      self.redoAddChange(('m', (0, 0, 0, 0, 0, self.cursorRow-self.markerRow,
          self.cursorCol-self.markerCol, mode-self.selectionMode)))
      self.redo()

  def selectionAll(self):
    self.doSelectionMode(kSelectionAll)

  def selectionBlock(self):
    self.doSelectionMode(kSelectionBlock)

  def selectionCharacter(self):
    self.doSelectionMode(kSelectionCharacter)

  def selectionLine(self):
    self.doSelectionMode(kSelectionLine)

  def selectionNone(self):
    self.doSelectionMode(kSelectionNone)

  def selectionWord(self):
    self.doSelectionMode(kSelectionWord)

  def selectWordAt(self, row, col):
    row = max(0, min(row, len(self.lines)-1))
    col = max(0, min(col, len(self.lines[row])-1))
    self.selectText(row, col, 0, kSelectionWord)

  def splitLine(self):
    """split the line into two at current column."""
    self.redoAddChange(('n', (0, 0, 0)))
    self.redo()

  def test(self):
    self.prg.log('test')
    self.insertPrintable(0x00)

  def stripTrailingWhiteSpace(self):
    for i in range(len(self.lines)):
      self.lines[i] = self.lines[i].rstrip()

  def unindent(self):
    if self.selectionMode == kSelectionAll:
      self.cursorMoveAndMark(len(self.lines)-1-self.cursorRow, -self.cursorCol,
          -self.goalCol,
          -self.markerRow, -self.markerCol, kSelectionLine-self.selectionMode)
      self.redo()
      self.unindentLines()
    else:
      self.cursorMoveAndMark(0, -self.cursorCol, -self.goalCol,
          0, -self.markerCol, kSelectionLine-self.selectionMode)
      self.redo()
      self.unindentLines()

  def unindentLines(self):
    upperRow = min(self.markerRow, self.cursorRow)
    lowerRow = max(self.markerRow, self.cursorRow)
    self.prg.log('unindentLines', upperRow, lowerRow)
    for line in self.lines[upperRow:lowerRow+1]:
      if line[:2] != '  ':
        # Handle multi-delete.
        return
    self.redoAddChange(('vd', ('  ')))
    self.redo()

  def undo(self):
    if self.redoIndex > 0:
      self.redoIndex -= 1
      change = self.redoChain[self.redoIndex]
      if self.debugRedo:
        self.prg.log('undo', self.redoIndex, repr(change))
      if change[0] == 'b':
        line = self.lines[self.cursorRow]
        x = self.cursorCol
        self.lines[self.cursorRow] = line[:x] + change[1] + line[x:]
        self.cursorCol += len(change[1])
      elif change[0] == 'd':
        line = self.lines[self.cursorRow]
        x = self.cursorCol
        self.lines[self.cursorRow] = line[:x] + change[1] + line[x:]
      elif change[0] == 'ds':
        self.selectionMode = change[1][-1]
        self.insertLines(self, change[2])
        self.setSelection(change[1])
        self.goalCol = self.cursorCol
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
        self.cursorRow -= change[1][0]
        self.cursorCol -= change[1][1]
        self.goalCol -= change[1][2]
        self.scrollRow -= change[1][3]
        self.scrollCol -= change[1][4]
        self.markerRow -= change[1][5]
        self.markerCol -= change[1][6]
        self.selectionMode -= change[1][7]
      elif change[0] == 'n':
        # Split lines.
        self.cursorRow -= change[1][0]
        self.cursorCol -= change[1][1]
        self.goalCol -= change[1][2]
        self.lines[self.cursorRow] += self.lines[self.cursorRow+change[1][0]]
        for i in range(change[1][0]):
          del self.lines[self.cursorRow+1]
      elif change[0] == 'v': # undo paste
        lineCount = len(change[1])
        upperRow = self.cursorRow-(lineCount-1)
        if lineCount == 1:
          upperCol = self.cursorCol-(len(change[1][0]))
        else:
          upperCol = len(self.lines[upperRow])-(len(change[1][0]))
        a = (upperRow, upperCol,
            self.cursorRow, self.cursorCol, kSelectionCharacter)
        self.prg.log('undo v', a)
        self.setSelection(a)
        self.doDeleteSelection(self)
        upperRow, upperCol, a,b = self.startAndEnd()
        self.selectionMode = kSelectionNone
        self.cursorRow += upperRow-self.cursorRow
        self.cursorCol += upperCol-self.cursorCol
        self.goalCol = self.cursorCol
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
        for i in range(upperRow, lowerRow+1):
          line = self.lines[self.cursorRow]
          x = self.cursorCol
          self.lines[i] = line[:x] + change[1] + line[x:]
      elif change[0] == 'vi':
        text = change[1]
        col = self.cursorCol
        row = min(self.markerRow, self.cursorRow)
        endRow = max(self.markerRow, self.cursorRow)
        textLen = len(text)
        self.prg.log('undo vi', textLen)
        for i in range(row, endRow+1):
          line = self.lines[i]
          self.lines[i] = line[:col-textLen] + line[col:]
        self.cursorCol -= textLen
        self.goalCol = self.cursorCol
      else:
        self.prg.log('ERROR: unknown undo.')

  def redo(self):
    if self.redoIndex < len(self.redoChain):
      change = self.redoChain[self.redoIndex]
      if self.debugRedo:
        self.prg.log('redo', self.redoIndex, repr(change))
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
      elif change[0] == 'ds':
        self.setSelection(change[1])
        upperRow, upperCol, a,b = self.startAndEnd()
        self.doDeleteSelection(self)
        self.selectionMode = kSelectionNone
        self.cursorRow += upperRow-self.cursorRow
        self.cursorCol += upperCol-self.cursorCol
        self.goalCol = self.cursorCol
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
        self.selectionMode += change[1][7]
        if self.redoIndex == 1:
          self.savedAtRedoIndex = 1
      elif change[0] == 'n':
        # Split lines.
        line = self.lines[self.cursorRow]
        self.lines.insert(self.cursorRow+1, line[self.cursorCol:])
        self.lines[self.cursorRow] = line[:self.cursorCol]
        for i in range(max(change[1][0] - 1, 0)):
          self.lines.insert(self.cursorRow+1, "")
        self.cursorRow += change[1][0]
        self.cursorCol += change[1][1]
        self.goalCol += change[1][2]
      elif change[0] == 'v':
        self.insertLines(self, change[1])
        self.selectionMode = kSelectionNone
        maxy, maxx = self.prg.inputWindow.cursorWindow.getmaxyx() #hack
        if self.cursorRow > self.scrollRow + maxy:
          self.scrollRow = self.cursorRow
        if self.cursorCol > self.scrollCol + maxx:
          self.scrollCol = self.cursorCol
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
        for i in range(upperRow, lowerRow+1):
          line = self.lines[i]
          x = self.cursorCol
          self.lines[i] = line[:x] + line[x+len(change[1]):]
      elif change[0] == 'vi':
        text = change[1]
        col = self.cursorCol
        row = min(self.markerRow, self.cursorRow)
        rowEnd = max(self.markerRow, self.cursorRow)
        self.prg.log('do vi')
        for i in range(row, rowEnd+1):
          line = self.lines[i]
          self.lines[i] = line[:col] + text + line[col:]
        self.cursorCol += len(text)
        self.goalCol = self.cursorCol
      else:
        self.prg.log('ERROR: unknown redo.')

  def redoAddChange(self, change):
    if self.debugRedo:
      self.prg.log('redoAddChange', change)
    self.redoChain = self.redoChain[:self.redoIndex]
    if 1: # optimizer
      if len(self.redoChain):
        if self.redoChain[-1][0] == change[0] and change[0] in ('d', 'i', 'vi'):
          change = (change[0], self.redoChain[-1][1] + change[1])
          self.undo()
          self.redoChain.pop()
        elif change[0] == 'm':
          if self.redoChain[-1][0] == 'm':
            change = (change[0], addVectors(self.redoChain[-1][1], change[1]))
            self.undo()
            self.redoChain.pop()
        elif self.redoChain[-1][0] == change[0] and change[0] == 'n':
          change = (change[0], addVectors(self.redoChain[-1][1], change[1]))
          self.undo()
          self.redoChain.pop()
    if 1:
      # Eliminate no-op entries
      noOpInstructions = set([
        ('m', (0,0,0,0,0,0,0,0)),
      ])
      assert ('m', (0,0,0,0,0,0,0,0)) in noOpInstructions
      if change in noOpInstructions:
        return
      self.prg.log(change)
    self.redoChain.append(change)
    if self.debugRedo:
      self.prg.log('--- redoIndex', self.redoIndex)
      for i,c in enumerate(self.redoChain):
        self.prg.log('%2d:'%i, repr(c))



class TextBuffer(BackingTextBuffer):
  def __init__(self, prg):
    BackingTextBuffer.__init__(self, prg)
    self.highlightKeywords = [
      'and',
      'break',
      'continue',
      'class',
      'def',
      'elif',
      'else',
      'except',
      'except',
      'False',
      'from',
      'function',
      'global',
      'if',
      'import',
      'in',
      'is',
      'None',
      'not',
      'or',
      'raise',
      'range',
      'then',
      'True',
      'try',
      'until',
      'while',
    ]
    self.highlightKeywords += [
      'case',
      'public',
      'private',
      'protected',
      'const',
      'static',
      'switch',
      'throw',
    ]
    self.highlightPreprocessor = [
      'define',
      'elif',
      'endif',
      'if',
      'include',
      'undef',
    ]
    keywords = '\\b%s\\b'%('\\b|\\b'.join(self.highlightKeywords),)
    keywords += '|#\s*%s\\b'%('\\b|#\s*'.join(self.highlightPreprocessor),)
    self.highlightRe = re.compile(keywords)

  def scrollToCursor(self, window):
    maxy, maxx = window.cursorWindow.getmaxyx() #hack
    rows = 0
    if self.scrollRow > self.cursorRow:
      rows = self.cursorRow - self.scrollRow
    elif self.cursorRow >= self.scrollRow+maxy:
      rows = self.cursorRow - (self.scrollRow+maxy-1)
    cols = 0
    if self.scrollCol > self.cursorCol:
      cols = self.cursorCol - self.scrollCol
    elif self.cursorCol >= self.scrollCol+maxx:
      cols = self.cursorCol - (self.scrollCol+maxx-1)
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
      if 1:
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
          for k in re.finditer(kReStrings, line):
            for f in k.regs:
              window.addStr(i, f[0], line[f[0]:f[1]], curses.color_pair(5))
      if 1:
        # Highlight comments.
        for i in range(limit):
          line = self.lines[self.scrollRow+i][startCol:endCol]
          for k in re.finditer('^\s*#.*$', line):
            for f in k.regs:
              window.addStr(i, f[0], line[f[0]:f[1]], curses.color_pair(2))
      if 1:
        # Highlight brackets.
        for i in range(limit):
          line = self.lines[self.scrollRow+i][startCol:endCol]
          for k in re.finditer(kReBrackets, line):
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
          for k in re.finditer(kReNumbers, line):
            for f in k.regs:
              window.addStr(i, f[0], line[f[0]:f[1]], curses.color_pair(31))
      if self.findRe is not None:
        # Highlight find.
        for i in range(limit):
          line = self.lines[self.scrollRow+i][startCol:endCol]
          for k in self.findRe.finditer(line):
            f = k.regs[-1]
            window.addStr(i, f[0], line[f[0]:f[1]], curses.color_pair(64))
      if limit and self.selectionMode != kSelectionNone:
        # Highlight selected text.
        upperRow, upperCol, lowerRow, lowerCol = self.startAndEnd()
        selStartCol = max(upperCol - startCol, 0)
        selEndCol = min(lowerCol - startCol, maxx)
        start = max(0, upperRow-self.scrollRow)
        end = min(lowerRow-self.scrollRow, maxy)

        if self.selectionMode == kSelectionAll:
          for i in range(limit):
            line = self.lines[self.scrollRow+i][startCol:endCol]
            window.addStr(i, 0, line, window.colorSelected)
        elif self.selectionMode == kSelectionBlock:
          for i in range(start, end+1):
            line = self.lines[self.scrollRow+i][selStartCol:selEndCol]
            window.addStr(i, selStartCol, line, window.colorSelected)
        elif (self.selectionMode == kSelectionCharacter or
            self.selectionMode == kSelectionWord):
          for i in range(start, end+1):
            line = self.lines[self.scrollRow+i][startCol:endCol]
            try:
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
            except curses.error:
              pass
        elif self.selectionMode == kSelectionLine:
          for i in range(start, end+1):
            line = self.lines[self.scrollRow+i][selStartCol:selEndCol]
            window.addStr(i, selStartCol,
                line+' '*(maxx-len(line)), window.colorSelected)
      for i in range(limit, maxy):
        window.addStr(i, 0, ' '*maxx, window.color)
