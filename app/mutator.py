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

import app.log
import app.parser
import app.prefs
import app.selectable
import os
import re


# If a change is in |noOpInstructions| then it has no real effect.
noOpInstructions = set([
  ('m', (0,0,0,0,0)),
])


def addVectors(a, b):
  """Add two list-like objects, pair-wise."""
  return tuple([a[i]+b[i] for i in range(len(a))])


class Mutator(app.selectable.Selectable):
  """Track and enact changes to a body of text."""
  def __init__(self):
    app.selectable.Selectable.__init__(self)
    self.debugRedo = False
    self.findRe = None
    self.findBackRe = None
    self.fileExtension = ''
    self.fullPath = ''
    self.fileStat = None
    self.isReadOnly = False
    self.penGrammar = None
    self.parser = None
    self.parserTime = .0
    self.relativePath = ''
    self.redoChain = []
    # |tempChange| is used to store cursor view actions without trimming
    # redoChain.
    self.tempChange = None
    # |processTempChange| is True if tempChange is not None and needs to be
    # processed.
    self.processTempChange = False
    # |stallNextRedo| is True if the next call to redo() should do nothing.
    self.stallNextRedo = False
    # |redoIndex| may be equal to len(self.redoChain) (must be <=).
    self.redoIndex = 0
    # |savedAtRedoIndex| may be > len(self.redoChain).
    self.savedAtRedoIndex = 0
    self.shouldReparse = False

  def addLine(self, msg):
    """Direct manipulator for logging to a read-only buffer."""
    self.lines.append(msg)
    self.penRow += 1

  def getPenOffset(self, row, col):
    """inefficient test hack. wip on parser"""
    offset = 0
    for i in range(row):
      offset += len(self.lines[i])
    return offset + row + col

  def cursorGrammarName(self):
    """inefficient test hack. wip on parser"""
    if not self.parser:
      return 'no parser'
    self.penGrammar = self.parser.grammarFromRowCol(
        self.penRow, self.penCol)[0]
    if self.penGrammar is None:
      return 'None'
    return self.penGrammar.grammar.get('name', 'unknown')

  def cursorGrammarRemaining(self):
    """inefficient test hack. wip on parser"""
    if not self.parser:
      return -2
    remaining = self.parser.grammarFromRowCol(
        self.penRow, self.penCol)[1]
    if remaining is None:
      return -1
    return remaining

  def isDirty(self):
    """Whether the buffer contains non-trivial changes since the last save."""
    clean = self.savedAtRedoIndex >= 0 and (
        self.savedAtRedoIndex == self.redoIndex or
        (self.redoIndex + 1 == self.savedAtRedoIndex and
          self.redoIndex < len(self.redoChain) and
          self.redoChain[self.redoIndex][0] == 'm') or
        (self.redoIndex - 1 == self.savedAtRedoIndex and
          self.redoIndex > 0 and
          self.redoChain[self.redoIndex - 1][0] == 'm'))
    return not clean

  def isSafeToWrite(self):
    if not os.path.exists(self.fullPath):
      return True
    self.isReadOnly = not os.access(self.fullPath, os.W_OK)
    s1 = os.stat(self.fullPath)
    s2 = self.fileStat
    app.log.info('st_mode', s1.st_mode, s2.st_mode)
    app.log.info('st_ino', s1.st_ino, s2.st_ino)
    app.log.info('st_dev', s1.st_dev, s2.st_dev)
    app.log.info('st_uid', s1.st_uid, s2.st_uid)
    app.log.info('st_gid', s1.st_gid, s2.st_gid)
    app.log.info('st_size', s1.st_size, s2.st_size)
    app.log.info('st_mtime', s1.st_mtime, s2.st_mtime)
    app.log.info('st_ctime', s1.st_ctime, s2.st_ctime)
    return (s1.st_mode == s2.st_mode and
        s1.st_ino == s2.st_ino and
        s1.st_dev == s2.st_dev and
        s1.st_uid == s2.st_uid and
        s1.st_gid == s2.st_gid and
        s1.st_size == s2.st_size and
        s1.st_mtime == s2.st_mtime and
        s1.st_ctime == s2.st_ctime)

  def doMoveLines(self, begin, end, to):
    lines = self.lines[begin:end]
    del self.lines[begin:end]
    count = end - begin
    if begin < to:
      assert end < to
      assert self.penRow < to
      to -= count
      self.penRow -= count
      if self.selectionMode != app.selectable.kSelectionNone:
        assert self.markerRow < to + count
        assert self.markerRow >= count
        self.markerRow -= count
    else:
      assert end > to
      assert self.penRow >= to
      self.penRow += count
      if self.selectionMode != app.selectable.kSelectionNone:
        assert self.markerRow >= to
        self.markerRow += count
    self.lines = self.lines[:to] + lines + self.lines[to:]

  def redoMove(self, change):
    assert self.penRow + change[1][0] >= 0, "%s %s"%(
        self.penRow, change[1][0])
    assert self.penCol + change[1][1] >= 0, "%s %s"%(
        self.penCol, change[1][1])
    self.penRow += change[1][0]
    self.penCol += change[1][1]
    self.markerRow += change[1][2]
    self.markerCol += change[1][3]
    self.selectionMode += change[1][4]

  def redo(self):
    """Replay the next action on the redoChain."""
    assert 0 <= self.redoIndex <= len(self.redoChain)
    if self.stallNextRedo:
      self.stallNextRedo = False
      return
    if self.processTempChange:
      if self.debugRedo:
        app.log.info('processTempChange', repr(change))
      self.processTempChange = False
      change = self.tempChange
      self.redoMove(change)
      return
    if self.tempChange:
      self.undoMove(self.tempChange)
      self.tempChange = None
    if self.redoIndex < len(self.redoChain):
      change = self.redoChain[self.redoIndex]
      if self.debugRedo:
        app.log.info('redo', self.redoIndex, repr(change))
      if change[0] != 'm':
        self.shouldReparse = True
      self.redoIndex += 1
      if change[0] == 'b':
        line = self.lines[self.penRow]
        self.penCol -= len(change[1])
        x = self.penCol
        self.lines[self.penRow] = line[:x] + line[x + len(change[1]):]
      elif change[0] == 'd':
        line = self.lines[self.penRow]
        x = self.penCol
        self.lines[self.penRow] = line[:x] + line[x + len(change[1]):]
      elif change[0] == 'dr':  # Redo delete range.
        self.doDelete(*change[1])
      elif change[0] == 'ds':  # Redo delete selection.
        self.doDeleteSelection()
      elif change[0] == 'i':  # Redo insert.
        line = self.lines[self.penRow]
        x = self.penCol
        self.lines[self.penRow] = line[:x] + change[1] + line[x:]
        self.penCol += len(change[1])
        self.view.goalCol = self.penCol
      elif change[0] == 'j':  # Redo join lines.
        self.lines[self.penRow] += self.lines[self.penRow + 1]
        del self.lines[self.penRow + 1]
      elif change[0] == 'ld':  # Redo line diff.
        lines = []
        index = 0
        for ii in change[1]:
          if type(ii) is type(0):
            for line in self.lines[index:index + ii]:
              lines.append(line)
            index += ii
          elif ii[0] == '+':
            lines.append(ii[2:])
          elif ii[0] == '-':
            index += 1
        app.log.info('ld', self.lines == lines)
        self.lines = lines
      elif change[0] == 'm':  # Redo move
        self.redoMove(change)
      elif change[0] == 'ml':
        # Redo move lines
        begin, end, to = change[1]
        self.doMoveLines(begin, end, to)
      elif change[0] == 'n':
        # Redo split lines.
        line = self.lines[self.penRow]
        self.lines.insert(self.penRow + 1, line[self.penCol:])
        self.lines[self.penRow] = line[:self.penCol]
        for i in range(max(change[1][0] - 1, 0)):
          self.lines.insert(self.penRow + 1, "")
        self.redoMove(change[1][1])
      elif change[0] == 'v':  # Redo paste.
        self.insertLines(change[1])
      elif change[0] == 'vb':
        self.penCol -= len(change[1])
        row = min(self.markerRow, self.penRow)
        rowEnd = max(self.markerRow, self.penRow)
        for i in range(row, rowEnd + 1):
          line = self.lines[i]
          x = self.penCol
          self.lines[self.penRow] = line[:x] + line[x + len(change[1]):]
      elif change[0] == 'vd':  # Redo vertical delete.
        upperRow = min(self.markerRow, self.penRow)
        lowerRow = max(self.markerRow, self.penRow)
        x = self.penCol
        for i in range(upperRow, lowerRow + 1):
          line = self.lines[i]
          self.lines[i] = line[:x] + line[x + len(change[1]):]
      elif change[0] == 'vi':  # Redo vertical insert.
        text = change[1][0]
        col = change[1][3]
        row = change[1][1]
        endRow = change[1][2]
        app.log.info('do vi')
        for i in range(row, endRow + 1):
          line = self.lines[i]
          self.lines[i] = line[:col] + text + line[col:]
      else:
        app.log.info('ERROR: unknown redo.')
    # Redo again if there is a move next.
    if (self.redoIndex < len(self.redoChain) and
        self.redoChain[self.redoIndex][0] == 'm'):
      self.redo()

  def redoAddChange(self, change):
    """
    Push a change onto the end of the redoChain. Call redo() to enact the
    change.
    """
    newTrivialChange = False
    if self.debugRedo:
      app.log.info('redoAddChange', change)
    # When the redoChain is trimmed we may lose the saved at.
    # Trim only when there is a non-trivial action.
    if change[0] == 'm' and self.redoIndex != len(self.redoChain):
      newTrivialChange = True
    else:
      # Trim and combine main redoChain with tempChange
      # if there is a non-trivial action.
      if self.redoIndex < self.savedAtRedoIndex:
        self.savedAtRedoIndex = -1
      self.redoChain = self.redoChain[:self.redoIndex]
      if self.tempChange:
        if len(self.redoChain) and self.redoChain[-1][0] == 'm':
          combinedChange = ('m', addVectors(self.tempChange[1],
              self.redoChain[-1][1]))
          if combinedChange in noOpInstructions:
            self.redoChain.pop()
            self.redoIndex -= 1
          else:
            self.redoChain[-1] = combinedChange
        else:
          self.redoChain.append(self.tempChange)
          self.redoIndex += 1
        self.tempChange = None
    if 1: # optimizer
      if len(self.redoChain) and self.savedAtRedoIndex != self.redoIndex:
        if (self.redoChain[-1][0] == change[0] and
            change[0] in ('d', 'i')):
          change = (change[0], self.redoChain[-1][1] + change[1])
          self.undoOne()
          self.redoChain.pop()
        elif self.redoChain[-1][0] == change[0] and change[0] == 'n':
          newMouseChange = change[1][1]
          newCarriageReturns = change[1][0]
          oldMouseChange = self.redoChain[-1][1][1]
          oldCarriageReturns = self.redoChain[-1][1][0]
          change = (change[0], (oldCarriageReturns + newCarriageReturns, 
                                ('m', addVectors(newMouseChange[1], oldMouseChange[1]))))
          self.undoOne()
          self.redoChain.pop()
    if newTrivialChange:
      if self.tempChange:
        # Combine new change with the existing tempChange.
        change = (change[0], addVectors(self.tempChange[1], change[1]))
        self.undoOne()
        self.tempChange = change
      if change in noOpInstructions:
        self.stallNextRedo = True
        self.processTempChange = False
        self.tempChange = None
        return
      self.processTempChange = True
      self.tempChange = change
    else:
      if len(self.redoChain) and change[0] == 'm':
        if self.redoChain[-1][0] == 'm':
          change = (change[0], addVectors(self.redoChain[-1][1], change[1]))
          self.undoOne()
          self.redoChain.pop()
        if change in noOpInstructions:
          self.stallNextRedo = True
          return
      self.redoChain.append(change)
    if self.debugRedo:
      app.log.info('--- redoIndex', self.redoIndex)
      for i,c in enumerate(self.redoChain):
        app.log.info('%2d:'%i, repr(c))
      app.log.info('tempChange', repr(self.tempChange))

  def undoMove(self, change):
    """Undo the action of a cursor move"""
    app.log.detail('undo cursor move')
    self.penRow -= change[1][0]
    self.penCol -= change[1][1]
    self.markerRow -= change[1][2]
    self.markerCol -= change[1][3]
    self.selectionMode -= change[1][4]
    assert self.penRow >= 0
    assert self.penCol >= 0

  def undo(self):
    """Undo a set of redo nodes."""
    while self.undoOne():
      pass
    self.tempChange = None
    self.processTempChange = False

  def undoOne(self):
    """Undo the most recent change to the buffer.
    return whether undo should be repeated."""
    app.log.detail('undo')
    assert 0 <= self.redoIndex <= len(self.redoChain)
    # If tempChange is active, undo it first to fix cursor position.
    if self.tempChange:
      self.undoMove(self.tempChange)
      self.tempChange = None
      return True
    elif self.redoIndex > 0:
      self.redoIndex -= 1
      change = self.redoChain[self.redoIndex]
      if change[0] != 'm':
        self.shouldReparse = True
      if self.debugRedo:
        app.log.info('undo', self.redoIndex, repr(change))
      if change[0] == 'b':
        line = self.lines[self.penRow]
        x = self.penCol
        self.lines[self.penRow] = line[:x] + change[1] + line[x:]
        self.penCol += len(change[1])
      elif change[0] == 'd':
        line = self.lines[self.penRow]
        x = self.penCol
        self.lines[self.penRow] = line[:x] + change[1] + line[x:]
      elif change[0] == 'dr':  # Undo delete range.
        app.log.detail('undo dr', change[1])
        self.insertLinesAt(change[1][0], change[1][1], change[2])
      elif change[0] == 'ds':  # Undo delete selection.
        app.log.detail('undo ds', change[1])
        self.insertLines(change[1])
      elif change[0] == 'i':
        line = self.lines[self.penRow]
        x = self.penCol
        self.penCol -= len(change[1])
        self.lines[self.penRow] = line[:x - len(change[1])] + line[x:]
        self.view.goalCol = self.penCol
      elif change[0] == 'j':
        # Join lines.
        line = self.lines[self.penRow]
        self.lines.insert(self.penRow + 1, line[self.penCol:])
        self.lines[self.penRow] = line[:self.penCol]
      elif change[0] == 'ld':  # Undo line diff.
        app.log.info('ld')
        lines = []
        index = 0
        for ii in change[1]:
          if type(ii) is type(0):
            for line in self.lines[index:index + ii]:
              lines.append(line)
            index += ii
          elif ii[0] == '+':
            index += 1
          elif ii[0] == '-':
            lines.append(ii[2:])
        self.lines = lines
      elif change[0] == 'm':
        app.log.detail('undo move')
        self.penRow -= change[1][0]
        self.penCol -= change[1][1]
        self.markerRow -= change[1][2]
        self.markerCol -= change[1][3]
        self.selectionMode -= change[1][4]
        assert self.penRow >= 0
        assert self.penCol >= 0
        return True
      elif change[0] == 'ml':
        # Undo move lines
        begin, end, to = change[1]
        count = end - begin
        if begin < to:
          self.doMoveLines(to - 1, to + count - 1, begin + count - 1)
        else:
          self.doMoveLines(to, to + count, begin + count)
      elif change[0] == 'n':
        # Undo split lines.
        self.undoMove(change[1][1])
        self.lines[self.penRow] += self.lines[self.penRow + change[1][0]]
        for i in range(change[1][0]):
          del self.lines[self.penRow + 1]
      elif change[0] == 'v':  # undo paste
        clip = change[1]
        row = self.penRow
        col = self.penCol
        app.log.info('len clip', len(clip))
        if len(clip) == 1:
          self.lines[row] = (
              self.lines[row][:col] +
              self.lines[row][col + len(clip[0]):])
        else:
          self.lines[row] = (self.lines[row][:col]+
              self.lines[row + len(clip)-1][len(clip[-1]):])
          delLineCount = len(clip[1:-1])
          del self.lines[row + 1:row + 1 + delLineCount + 1]
      elif change[0] == 'vb':
        row = min(self.markerRow, self.penRow)
        endRow = max(self.markerRow, self.penRow)
        for i in range(row, endRow + 1):
          line = self.lines[self.penRow]
          x = self.penCol
          self.lines[self.penRow] = line[:x] + change[1] + line[x:]
        self.penCol += len(change[1])
      elif change[0] == 'vd':
        upperRow = min(self.markerRow, self.penRow)
        lowerRow = max(self.markerRow, self.penRow)
        x = self.penCol
        for i in range(upperRow, lowerRow + 1):
          line = self.lines[i]
          self.lines[i] = line[:x] + change[1] + line[x:]
      elif change[0] == 'vi':  # Undo.
        text = change[1][0]
        col = change[1][3]
        row = change[1][1]
        endRow = change[1][2]
        textLen = len(text)
        app.log.info('undo vi', textLen)
        for i in range(row, endRow + 1):
          line = self.lines[i]
          self.lines[i] = line[:col] + line[col + textLen:]
      else:
        app.log.info('ERROR: unknown undo.')
    return False
