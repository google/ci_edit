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

import app.actions
import app.log
import app.parser
import app.prefs
import app.selectable
import app.spelling
import curses
import re
import sys

class TextBuffer(app.actions.Actions):
  """The TextBuffer adds the drawing/rendering to the BackingTextBuffer."""
  def __init__(self):
    app.actions.Actions.__init__(self)
    self.lineLimitIndicator = 0
    self.highlightRe = None
    self.fileHistory = {}
    self.fileEncoding = None
    self.lastChecksum = None
    self.lastFileSize = 0
    self.bookmarks = []

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
    self.updateScrollPosition(rows, cols)

  def draw(self, window):
    if self.view.rows <= 0 or self.view.cols <= 0:
      return
    if 1:
      self.parseGrammars()
    else:
      if self.shouldReparse:
        self.parseGrammars()
        self.shouldReparse = False
    if self.view.hasCaptiveCursor:
      self.checkScrollToCursor(window)
    rows, cols = window.rows, window.cols
    colorDelta = 32 * 4
    #colorDelta = 4
    if 0:
      for i in range(rows):
        window.addStr(i, 0, '?' * cols, app.color.get(120))
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
        self.drawTextArea(window, 0, splitCol, splitRow, cols - splitCol,
            colorDelta)
      else:
        # Draw only right side.
        assert splitCol <= 0
        self.drawTextArea(window, 0, splitCol, splitRow, cols - splitCol,
            colorDelta)
    else:
      # Draw debug checker board.
      splitRow = rows / 2
      splitCol = 17
      self.drawTextArea(window, 0, 0, splitRow, splitCol, 0)
      self.drawTextArea(window, 0, splitCol, splitRow, cols-splitCol, colorDelta)
      self.drawTextArea(window, splitRow, 0, rows - splitRow, splitCol, colorDelta)
      self.drawTextArea(window, splitRow, splitCol, rows - splitRow,
          cols-splitCol, 0)
    # Blank screen past the end of the buffer.
    color = app.color.get('outside_document')
    endOfText = min(max(len(self.lines) - self.view.scrollRow, 0), rows)
    for i in range(endOfText, rows):
      window.addStr(i, 0, ' ' * cols, color)

  def drawTextArea(self, window, top, left, rows, cols, colorDelta):
    startRow = self.view.scrollRow + top
    endRow = startRow + rows
    startCol = self.view.scrollCol + left
    endCol = startCol + cols
    colors = app.prefs.color
    spellChecking = app.prefs.editor.get('spellChecking', True)
    if self.parser:
      # Highlight grammar.
      rowLimit = min(max(len(self.lines) - startRow, 0), rows)
      for i in range(rowLimit):
        k = startCol
        if k == 0:
          # When rendering from column 0 the grammar index is always zero.
          grammarIndex = 0
        else:
          # When starting mid-line, find starting grammar index.
          grammarIndex = self.parser.grammarIndexFromRowCol(startRow + i, k)
        while k < endCol:
          node, preceding, remaining = self.parser.grammarAtIndex(
              startRow + i, k, grammarIndex)
          grammarIndex += 1
          if remaining == 0:
            continue
          line = self.lines[startRow + i]
          assert remaining >= 0, remaining
          remaining = min(len(line) - k, remaining)
          length = min(endCol - k, remaining)
          color = app.color.get(node.grammar['colorIndex'] + colorDelta)
          if length <= 0:
            window.addStr(top + i, left + k - startCol, ' ' * (endCol - k),
                color)
            break
          window.addStr(top + i, left + k - startCol, line[k:k + length], color)
          subStart = k - preceding
          subEnd = k + remaining
          subLine = line[subStart:subEnd]
          if spellChecking and node.grammar.get('spelling', True):
            # Highlight spelling errors
            grammarName = node.grammar.get('name', 'unknown')
            misspellingColor = app.color.get(colors['misspelling'] + colorDelta)
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
          k += length
    else:
      # Draw to screen.
      rowLimit = min(max(len(self.lines) - startRow, 0), rows)
      for i in range(rowLimit):
        line = self.lines[startRow + i][startCol:endCol]
        window.addStr(top + i, left, line + ' ' * (cols - len(line)),
            app.color.get(app.prefs.color['default'] + colorDelta))
    self.drawOverlays(window, top, left, rows, cols, colorDelta)
    if 0: # Experiment: draw our own cursor.
      if startRow <= self.penRow < endRow and  startCol <= self.penCol < endCol:
        window.addStr(self.penRow - startRow, self.penCol - startCol, 'X', 200)

  def drawOverlays(self, window, top, left, maxRow, maxCol, colorDelta):
    startRow = self.view.scrollRow + top
    endRow = self.view.scrollRow + top + maxRow
    startCol = self.view.scrollCol + left
    endCol = self.view.scrollCol + left + maxCol
    rowLimit = min(max(len(self.lines) - startRow, 0), maxRow)
    colors = app.prefs.color
    if 1:
      # Highlight brackets.
      color = app.color.get(colors['bracket'] + colorDelta)
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
                      app.color.get(colors['matching_bracket'] + colorDelta))
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
                      app.color.get(colors['matching_bracket'] + colorDelta))
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
              app.color.get(colors['matching_bracket'] + colorDelta))
    if 1:
      # Highlight numbers.
      for i in range(rowLimit):
        line = self.lines[startRow + i][startCol:endCol]
        for k in re.finditer(app.selectable.kReNumbers, line):
          for f in k.regs:
            window.addStr(top + i, left + f[0], line[f[0]:f[1]],
                app.color.get(colors['number'] + colorDelta))
    if 1:
      # Highlight space ending lines.
      for i in range(rowLimit):
        line = self.lines[startRow + i]
        if startRow + i == self.penRow and self.penCol == len(line):
          continue
        line = line[startCol:]
        for k in app.selectable.kReEndSpaces.finditer(line):
          for f in k.regs:
            window.addStr(top + i, left + f[0], line[f[0]:f[1]],
                app.color.get(colors['trailing_space'] + colorDelta))
    if 0:
      lengthLimit = self.lineLimitIndicator
      if endCol >= lengthLimit:
        # Highlight long lines.
        for i in range(rowLimit):
          line = self.lines[startRow + i]
          if len(line) < lengthLimit or startCol > lengthLimit:
            continue
          window.addStr(top + i, left + lengthLimit - startCol,
              line[lengthLimit:endCol], app.color.get(96 + colorDelta))
    if self.findRe is not None:
      # Highlight find.
      for i in range(rowLimit):
        line = self.lines[startRow + i][startCol:endCol]
        for k in self.findRe.finditer(line):
          reg = k.regs[0]
          #for ref in k.regs[1:]:
          window.addStr(top + i, left + reg[0], line[reg[0]:reg[1]],
              app.color.get(colors['found_find'] + colorDelta))
    if rowLimit and self.selectionMode != app.selectable.kSelectionNone:
      # Highlight selected text.
      colorSelected = app.color.get('selected')
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
