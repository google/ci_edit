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

import os
import re

import app.buffer_file
from app.curses_util import columnWidth
import app.log
import app.selectable

# If a change is in |noOpInstructions| then it has no real effect.
noOpInstructions = set([
    ('m', (0, 0, 0, 0, 0)),
])


def addVectors(a, b):
    """Add two list-like objects, pair-wise."""
    return tuple([a[i] + b[i] for i in range(len(a))])


class Mutator(app.selectable.Selectable):
    """Track and enact changes to a body of text."""

    def __init__(self, program):
        app.selectable.Selectable.__init__(self, program)
        self.__compoundChange = []
        # |oldRedoIndex| is used to store the redo index before an action
        # occurs, so we know where to insert the compound change.
        self.oldRedoIndex = 0
        self.debugRedo = False
        self.findRe = None
        self.findBackRe = None
        self.fileExtension = None
        self.fullPath = u''
        self.fileStat = None
        self.goalCol = 0
        self.isReadOnly = False
        self.penGrammar = None
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

    def compoundChangePush(self):
        # app.log.info('compoundChangePush')
        if self.__compoundChange:
            self.redoIndex = self.oldRedoIndex
            self.redoChain = self.redoChain[:self.redoIndex]
            changes = tuple(self.__compoundChange)
            change = changes[0]
            handledChange = False
            # Combine changes. Assumes d, i, n, and m consist of only 1 change.
            if (len(self.redoChain) and
                    self.redoChain[-1][0][0] == change[0] and
                    len(self.redoChain[-1]) == 1):
                if change[0] in ('d', 'i'):
                    change = (change[0], self.redoChain[-1][0][1] + change[1])
                    self.redoChain[-1] = (change,)
                    handledChange = True
                elif change[0] == 'f':
                    # Fences have no arguments to merge.
                    handledChange = True
                elif change[0] == 'n':
                    newCursorChange = change[2]
                    newCarriageReturns = change[1]
                    oldCursorChange = self.redoChain[-1][0][2]
                    oldCarriageReturns = self.redoChain[-1][0][1]
                    change = (change[0],
                              oldCarriageReturns + newCarriageReturns,
                              ('m',
                               addVectors(newCursorChange[1],
                                          oldCursorChange[1])))
                    self.redoChain[-1] = (change,)
                    handledChange = True
                elif change[0] == 'm':
                    change = (change[0],
                              addVectors(self.redoChain[-1][0][1], change[1]))
                    if change in noOpInstructions:
                        self.redoIndex -= 1
                        self.redoChain.pop()
                    else:
                        self.redoChain[-1] = (change,)
                    handledChange = True
            if not handledChange:
                self.redoChain.append(changes)
                self.redoIndex += 1
        self.__compoundChange = []
        self.oldRedoIndex = self.redoIndex

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
        index = self.parser.grammarIndexFromRowCol(self.penRow, self.penCol)
        self.penGrammar = self.parser.grammarAtIndex(self.penRow, self.penCol,
                                                     index)[0]
        if self.penGrammar is None:
            return 'None'
        return self.penGrammar.grammar.get('name', 'unknown')

    def isDirty(self):
        """Whether the buffer contains non-trivial changes since the last save.
        """
        clean = self.savedAtRedoIndex >= 0 and (
            self.savedAtRedoIndex == self.redoIndex or
            (self.redoIndex + 1 == self.savedAtRedoIndex and
             self.redoIndex < len(self.redoChain) and
             self.redoChain[self.redoIndex][0] == 'm') or
            (self.redoIndex - 1 == self.savedAtRedoIndex and self.redoIndex > 0
             and self.redoChain[self.redoIndex - 1][0] == 'm'))
        return not clean

    def isSafeToWrite(self):
        if not os.path.exists(self.fullPath):
            return True
        if self.fileStat is None:
            return False
        s1 = os.stat(self.fullPath)
        s2 = self.fileStat
        if 0:
            app.log.info('st_mode', s1.st_mode, s2.st_mode)
            app.log.info('st_ino', s1.st_ino, s2.st_ino)
            app.log.info('st_dev', s1.st_dev, s2.st_dev)
            app.log.info('st_uid', s1.st_uid, s2.st_uid)
            app.log.info('st_gid', s1.st_gid, s2.st_gid)
            app.log.info('st_size', s1.st_size, s2.st_size)
            app.log.info('st_mtime', s1.st_mtime, s2.st_mtime)
            app.log.info('st_ctime', s1.st_ctime, s2.st_ctime)
        return (s1.st_mode == s2.st_mode and s1.st_ino == s2.st_ino and
                s1.st_dev == s2.st_dev and s1.st_uid == s2.st_uid and
                s1.st_gid == s2.st_gid and s1.st_size == s2.st_size and
                s1.st_mtime == s2.st_mtime and s1.st_ctime == s2.st_ctime)

    def setFilePath(self, path):
        self.fullPath = app.buffer_file.expandFullPath(path)

    def __doMoveLines(self, begin, end, to):
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
            if self.upperChangedRow > begin:
                self.upperChangedRow = begin
        else:
            assert end > to
            assert self.penRow >= to
            self.penRow += count
            if self.selectionMode != app.selectable.kSelectionNone:
                assert self.markerRow >= to
                self.markerRow += count
            if self.upperChangedRow > to:
                self.upperChangedRow = to
        self.lines = self.lines[:to] + lines + self.lines[to:]

    def __doVerticalInsert(self, change):
        text, row, endRow, col = change[1]
        for i in range(row, endRow + 1):
            line = self.lines[i]
            self.lines[i] = line[:col] + text + line[col:]
        if self.upperChangedRow > row:
            self.upperChangedRow = row

    def __doVerticalDelete(self, change):
        text, row, endRow, col = change[1]
        for i in range(row, endRow + 1):
            line = self.lines[i]
            self.lines[i] = line[:col] + line[col + len(text):]
        if self.upperChangedRow > row:
            self.upperChangedRow = row

    def __redoMove(self, change):
        assert self.penRow + change[1][0] >= 0, "%s %s" % (self.penRow,
                                                           change[1][0])
        assert self.penCol + change[1][1] >= 0, "%s %s" % (self.penCol,
                                                           change[1][1])
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
            self.processTempChange = False
            self.__redoMove(self.tempChange)
            self.updateBasicScrollPosition()
            return
        if self.tempChange:
            self.__undoMove(self.tempChange)
            self.tempChange = None
            self.updateBasicScrollPosition()
        while self.redoIndex < len(self.redoChain):
            changes = self.redoChain[self.redoIndex]
            self.redoIndex += 1
            for change in changes:
                self.__redoChange(change)
            # Stop redoing if we redo a non-trivial action
            if not ((changes[0][0] == 'f' or changes[0][0] == 'm') and
                    len(changes) == 1):
                self.shouldReparse = True
                break
        self.updateBasicScrollPosition()

    def __redoChange(self, change):
        if change[0] == 'b':  # Redo backspace.
            line = self.lines[self.penRow]
            width = columnWidth(change[1])
            self.penCol -= width
            x = self.penCol
            self.lines[self.penRow] = line[:x] + line[x + width:]
            if self.upperChangedRow > self.penRow:
                self.upperChangedRow = self.penRow
        elif change[0] == 'bw':  # Redo backspace word.
            line = self.lines[self.penRow]
            width = columnWidth(change[1])
            self.penCol -= width
            x = self.penCol
            self.lines[self.penRow] = line[:x] + line[x + width:]
            if self.upperChangedRow > self.penRow:
                self.upperChangedRow = self.penRow
        elif change[0] == 'd':  # Redo delete character.
            line = self.lines[self.penRow]
            x = self.penCol
            self.lines[self.penRow] = line[:x] + line[x + columnWidth(change[1]):]
            if self.upperChangedRow > self.penRow:
                self.upperChangedRow = self.penRow
        elif change[0] == 'dr':  # Redo delete range.
            self.doDelete(*change[1])
        elif change[0] == 'ds':  # Redo delete selection.
            self.doDeleteSelection()
        elif change[0] == 'f':  # Redo fence.
            pass
        elif change[0] == 'i':  # Redo insert.
            line = self.lines[self.penRow]
            x = self.penCol
            self.lines[self.penRow] = line[:x] + change[1] + line[x:]
            self.penCol += columnWidth(change[1])
            self.goalCol = self.penCol
            if self.upperChangedRow > self.penRow:
                self.upperChangedRow = self.penRow
        elif change[0] == 'j':  # Redo join lines (delete \n).
            self.lines[self.penRow] += self.lines[self.penRow + 1]
            del self.lines[self.penRow + 1]
            if self.upperChangedRow > self.penRow:
                self.upperChangedRow = self.penRow
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
            self.lines = lines
            firstChangedRow = change[1][0] if type(
                change[1][0]) is type(0) else 0
            if self.upperChangedRow > firstChangedRow:
                self.upperChangedRow = firstChangedRow
        elif change[0] == 'm':  # Redo move
            self.__redoMove(change)
        elif change[0] == 'ml':  # Redo move lines
            begin, end, to = change[1]
            self.__doMoveLines(begin, end, to)
        elif change[0] == 'n':  # Redo split lines (insert \n).
            line = self.lines[self.penRow]
            self.lines.insert(self.penRow + 1, line[self.penCol:])
            self.lines[self.penRow] = line[:self.penCol]
            for i in range(max(change[1] - 1, 0)):
                self.lines.insert(self.penRow + 1, u"")
            if self.upperChangedRow > self.penRow:
                self.upperChangedRow = self.penRow
            self.__redoMove(change[2])
        elif change[0] == 'v':  # Redo paste.
            self.insertLines(change[1])
        elif change[0] == 'vb':  # Redo vertical backspace.
            self.penCol -= columnWidth(change[1])
            row = min(self.markerRow, self.penRow)
            rowEnd = max(self.markerRow, self.penRow)
            for i in range(row, rowEnd + 1):
                line = self.lines[i]
                x = self.penCol
                self.lines[self.penRow] = line[:x] + line[x + columnWidth(change[1]):]
            if self.upperChangedRow > row:
                self.upperChangedRow = row
        elif change[0] == 'vd':  # Redo vertical delete.
            self.__doVerticalDelete(change)
        elif change[0] == 'vi':  # Redo vertical insert.
            self.__doVerticalInsert(change)
        else:
            app.log.info('ERROR: unknown redo.')
        return False

    def redoAddChange(self, change):
        """
        Push a change onto the end of the redoChain. Call redo() to enact the
        change.
        """
        if app.config.strict_debug:
            assert isinstance(change, tuple), change
        if self.debugRedo:
            app.log.info('redoAddChange', change)
        # Handle new trivial actions, which are defined as standalone cursor
        # moves.
        if change[0] == 'm' and not self.__compoundChange:
            if self.tempChange:
                # Combine new change with the existing tempChange.
                change = (change[0], addVectors(self.tempChange[1], change[1]))
                self.__undoChange(self.tempChange)
                self.__tempChange = change
            if change in noOpInstructions:
                self.stallNextRedo = True
                self.processTempChange = False
                self.tempChange = None
                self.updateBasicScrollPosition()
                return
            self.processTempChange = True
            self.tempChange = change
        else:
            # Trim and combine main redoChain with tempChange
            # if there is a non-trivial action.
            # We may lose the saved at when trimming.
            if self.redoIndex < self.savedAtRedoIndex:
                self.savedAtRedoIndex = -1
            self.redoChain = self.redoChain[:self.redoIndex]
            if self.tempChange:
                # If previous action was a cursor move, we can merge it with
                # tempChange.
                if (len(self.redoChain) and self.redoChain[-1][0][0] == 'm' and
                        len(self.redoChain[-1]) == 1):
                    combinedChange = ('m',
                                      addVectors(self.tempChange[1],
                                                 self.redoChain[-1][0][1]))
                    if combinedChange in noOpInstructions:
                        self.redoChain.pop()
                        self.redoIndex -= 1
                        self.oldRedoIndex -= 1
                    else:
                        self.redoChain[-1] = (combinedChange,)
                else:
                    self.redoChain.append((self.tempChange,))
                    self.redoIndex += 1
                    self.oldRedoIndex += 1
                self.tempChange = None
            # Accumulating changes together as a unit.
            self.__compoundChange.append(change)
            self.redoChain.append((change,))
        if self.debugRedo:
            app.log.info('--- redoIndex', self.redoIndex)
            for i, c in enumerate(self.redoChain):
                app.log.info('%2d:' % i, repr(c))
            app.log.info('tempChange', repr(self.tempChange))

    def __undoMove(self, change):
        """Undo the action of a cursor move"""
        self.penRow -= change[1][0]
        self.penCol -= change[1][1]
        self.markerRow -= change[1][2]
        self.markerCol -= change[1][3]
        self.selectionMode -= change[1][4]
        assert self.penRow >= 0, self.penRow
        assert self.penCol >= 0, self.penCol

    def undo(self):
        """Undo a set of redo nodes."""
        assert 0 <= self.redoIndex <= len(self.redoChain)
        # If tempChange is active, undo it first to fix cursor position.
        if self.tempChange:
            self.__undoMove(self.tempChange)
            self.tempChange = None
        while self.redoIndex > 0:
            self.redoIndex -= 1
            changes = self.redoChain[self.redoIndex]
            if self.debugRedo:
                app.log.info('undo', self.redoIndex, repr(changes))
            if ((changes[0][0] == 'f' or changes[0][0] == 'm') and
                    len(changes) == 1):
                # Undo if the last edit was a cursor move.
                self.__undoChange(changes[0])
            else:
                self.shouldReparse = True
                # Undo previous non-trivial edit
                for change in reversed(changes):
                    self.__undoChange(change)
                break
        self.processTempChange = False

    def __undoChange(self, change):
        if change[0] == 'b':
            line = self.lines[self.penRow]
            x = self.penCol
            self.lines[self.penRow] = line[:x] + change[1] + line[x:]
            self.penCol += columnWidth(change[1])
            if self.upperChangedRow > self.penRow:
                self.upperChangedRow = self.penRow
        elif change[0] == 'bw':
            line = self.lines[self.penRow]
            x = self.penCol
            self.lines[self.penRow] = line[:x] + change[1] + line[x:]
            self.penCol += columnWidth(change[1])
            if self.upperChangedRow > self.penRow:
                self.upperChangedRow = self.penRow
        elif change[0] == 'd':
            line = self.lines[self.penRow]
            x = self.penCol
            self.lines[self.penRow] = line[:x] + change[1] + line[x:]
            if self.upperChangedRow > self.penRow:
                self.upperChangedRow = self.penRow
        elif change[0] == 'dr':  # Undo delete range.
            self.insertLinesAt(change[1][0], change[1][1], change[2],
                               app.selectable.kSelectionCharacter)
        elif change[0] == 'ds':  # Undo delete selection.
            self.insertLines(change[1])
        elif change[0] == 'f':  # Undo fence.
            pass
        elif change[0] == 'i':  # Undo insert.
            line = self.lines[self.penRow]
            x = self.penCol
            width = columnWidth(change[1])
            self.penCol -= width
            self.lines[self.penRow] = line[:x - width] + line[x:]
            self.goalCol = self.penCol
            if self.upperChangedRow > self.penRow:
                self.upperChangedRow = self.penRow
        elif change[0] == 'j':  # Undo join lines.
            line = self.lines[self.penRow]
            self.lines.insert(self.penRow + 1, line[self.penCol:])
            self.lines[self.penRow] = line[:self.penCol]
            if self.upperChangedRow > self.penRow:
                self.upperChangedRow = self.penRow
        elif change[0] == 'ld':  # Undo line diff.
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
            firstChangedRow = change[1][0] if type(
                change[1][0]) is type(0) else 0
            if self.upperChangedRow > firstChangedRow:
                self.upperChangedRow = firstChangedRow
        elif change[0] == 'm':
            self.__undoMove(change)
        elif change[0] == 'ml':
            # Undo move lines
            begin, end, to = change[1]
            count = end - begin
            if begin < to:
                self.__doMoveLines(to - 1, to + count - 1, begin + count - 1)
            else:
                self.__doMoveLines(to, to + count, begin + count)
        elif change[0] == 'n':
            # Undo split lines.
            self.__undoMove(change[2])
            self.lines[self.penRow] += self.lines[self.penRow + change[1]]
            for _ in range(change[1]):
                del self.lines[self.penRow + 1]
            if self.upperChangedRow > self.penRow:
                self.upperChangedRow = self.penRow
        elif change[0] == 'v':  # undo paste
            clip = change[1]
            row = self.penRow
            col = self.penCol
            app.log.info('len clip', len(clip))
            if len(clip) == 1:
                self.lines[row] = (self.lines[row][:col] +
                                   self.lines[row][col + len(clip[0]):])
            else:
                self.lines[row] = (
                    self.lines[row][:col] +
                    self.lines[row + len(clip) - 1][len(clip[-1]):])
                delLineCount = len(clip[1:-1])
                del self.lines[row + 1:row + 1 + delLineCount + 1]
            if self.upperChangedRow > row:
                self.upperChangedRow = row
        elif change[0] == 'vb':
            row = min(self.markerRow, self.penRow)
            endRow = max(self.markerRow, self.penRow)
            for _ in range(row, endRow + 1):
                line = self.lines[self.penRow]
                x = self.penCol
                self.lines[self.penRow] = line[:x] + change[1] + line[x:]
            self.penCol += columnWidth(change[1])
            if self.upperChangedRow > row:
                self.upperChangedRow = row
        elif change[0] == 'vd':  # Undo vertical delete
            self.__doVerticalInsert(change)
        elif change[0] == 'vi':  # Undo vertical insert
            self.__doVerticalDelete(change)
        else:
            app.log.info('ERROR: unknown undo.')

    def updateBasicScrollPosition(self):
        pass
