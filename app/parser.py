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

import app.background
import app.log
import app.selectable
import app.prefs
import third_party.pyperclip as clipboard
import curses.ascii
import os
import re
import sys
import time
import traceback


class ParserNode:
  """A parser node represents a span of grammar. i.e. from this point to that
      point is HTML. Another parser node would represent the next segment, of
      grammar (maybe JavaScript, CSS, comment, or quoted string for example."""
  def __init__(self):
    self.grammar = None
    self.prior = None  # Index of prior grammar (like a stack of grammars).
    self.begin = None  # Offset from start of file.

  def debugLog(self, out, indent, data):
    out('%sParserNode %26s prior %4s %4d %s' % (indent,
        self.grammar.get('name', 'None'),
        self.prior, self.begin, repr(data[self.begin:self.begin+15])[1:-1]))


class Parser:
  """A parser generates a set of grammar segments (ParserNode objects)."""
  def __init__(self):
    self.data = ""
    self.emptyNode = ParserNode()
    self.emptyNode.grammar = None
    self.endNode = ParserNode()
    self.endNode.grammar = {}
    self.endNode.begin = sys.maxint
    self.endNode.col = sys.maxint
    self.parserNodes = []
    self.rows = []  # Row parserNodes index.
    app.log.parser('__init__')

  def grammarIndexFromRowCol(self, row, col):
    """
    returns index. |index| may then be passed to grammarNext().
    """
    if row + 1 >= len(self.rows): # or self.rows[row + 1] > len(self.parserNodes):
      # This file is too large. There's other ways to handle this, but for now
      # let's leave the tail un-highlighted.
      return 0
    gl = self.parserNodes[self.rows[row]:self.rows[row + 1]] + [self.endNode]
    offset = gl[0].begin + col
    # Binary search to find the node for the column.
    low = 0
    high = len(gl) - 1
    while True:
      index = (high + low) / 2
      if offset >= gl[index + 1].begin:
        low = index
      elif offset < gl[index].begin:
        high = index
      else:
        return index

  def grammarAtIndex(self, row, col, index):
    """
    Call grammarIndexFromRowCol() to get the index parameter.
    returns (node, preceding, remaining). |index| may then be passed to
        grammarNext(). |proceeding| and |remaining| are relative to the |col|
        parameter.
    """
    finalResult = (self.emptyNode, -col, sys.maxint)
    if row + 1 >= len(self.rows):
      return finalResult
    nextRowIndex = self.rows[row + 1]
    if col >= self.parserNodes[nextRowIndex].begin:
      return finalResult
    rowIndex = self.rows[row]
    if rowIndex + index >= len(self.parserNodes):
      return finalResult
    if index >= nextRowIndex - rowIndex:
      return finalResult
    offset = self.parserNodes[rowIndex].begin + col
    remaining = self.parserNodes[rowIndex + index + 1].begin - offset
    if remaining < 0:
      return finalResult
    node = self.parserNodes[rowIndex + index]
    return node, offset - node.begin, remaining

  def parse(self, data, grammar, beginRow, endRow):
    """
      Args:
        data (string): The file contents. The document.
        grammar (object): The initial grammar (often determined by the file
            extension). If |beginRow| is not zero then grammar is ignored.
        beginRow (int): is the first row (which is line number - 1) in data that
            is has changed since the previous parse of this data. Pass zero to
            parse the entire document. If beginRow >= len(data) then no parse
            is done.
        endRow (int): The last row to parse. This stops the parser from going
            over the entire if, for example, only 100 rows out of a million rows
            are needed (which can save a lot of cpu time).
    """
    app.log.parser('grammar', grammar['name'])
    self.emptyNode.grammar = grammar
    self.data = data
    self.endRow = endRow
    if beginRow > 0 and len(self.rows):
      if beginRow < len(self.rows):
        self.parserNodes = self.parserNodes[:self.rows[beginRow]]
        self.rows = self.rows[:beginRow]
    else:
      node = ParserNode()
      node.grammar = grammar
      node.begin = 0
      node.prior = None
      self.parserNodes = [node]
      self.rows = [0]
    startTime = time.time()
    if self.endRow > len(self.rows):
      self.__buildGrammarList()
    totalTime = time.time() - startTime
    if app.log.enabledChannels.get('parser', False):
      self.debugLog(app.log.parser, data)
    app.log.startup('parsing took', totalTime)

  def __buildGrammarList(self):
    # An arbitrary limit to avoid run-away looping.
    leash = 50000
    topNode = self.parserNodes[-1]
    cursor = topNode.begin
    # If we are at the start of a grammar, skip the 'begin' part of the grammar.
    if (len(self.parserNodes) == 1 or
        topNode.grammar is not self.parserNodes[-2].grammar):
      beginRegex = topNode.grammar.get('begin')
      if beginRegex is not None:
        sre = re.match(beginRegex, self.data[cursor:])
        if sre is not None:
          cursor += sre.regs[0][1]
    while self.endRow > len(self.rows):
      if not leash:
        #app.log.error('grammar likely caught in a loop')
        break
      leash -= 1
      if app.prefs.editor['useBgThread'] and app.background.bg.hasUserEvent():
        break
      subdata = self.data[cursor:]
      found = self.parserNodes[-1].grammar.get('matchRe').search(subdata)
      if not found:
        #app.log.info('parser exit, match not found')
        # todo(dschuyler): mark parent grammars as unterminated (if they expect
        # be terminated). e.g. unmatched string quote or xml tag.
        break
      newGrammarIndexLimit = \
          2 + len(self.parserNodes[-1].grammar.get('contains', []))
      keywordIndexLimit = \
          newGrammarIndexLimit + len(self.parserNodes[-1].grammar.get(
              'keywords', []))
      index = -1
      for i,k in enumerate(found.groups()):
        if k is not None:
          index = i
          break
      assert index >= 0
      reg = found.regs[index + 1]
      if index == 0:
        # Found escaped value.
        cursor += reg[1]
        continue
      child = ParserNode()
      if index == len(found.groups()) - 1:
        # Found new line.
        child.grammar = self.parserNodes[-1].grammar
        child.begin = cursor + reg[1]
        child.prior = self.parserNodes[-1].prior
        cursor = child.begin
        self.rows.append(len(self.parserNodes))
      elif index == 1:
        # Found end of current grammar section (an 'end').
        child.grammar = self.parserNodes[self.parserNodes[-1].prior].grammar
        child.begin = cursor + reg[1]
        child.prior = self.parserNodes[self.parserNodes[-1].prior].prior
        cursor = child.begin
        if subdata[reg[1] - 1:reg[1]] == '\n':
          # This 'end' ends with a new line.
          self.rows.append(len(self.parserNodes))
      elif index < newGrammarIndexLimit:
        # A new grammar within this grammar (a 'contains').
        if subdata[reg[0]:reg[0] + 1] == '\n':
          # This 'begin' begins with a new line.
          self.rows.append(len(self.parserNodes))
        child.grammar = self.parserNodes[-1].grammar.get(
            'matchGrammars', [])[index]
        child.begin = cursor + reg[0]
        cursor += reg[1]
        child.prior = len(self.parserNodes) - 1
      elif index < keywordIndexLimit:
        # A keyword doesn't change the nodeIndex.
        keywordNode = ParserNode()
        keywordNode.grammar = app.prefs.grammars['keyword']
        keywordNode.begin = cursor + reg[0]
        keywordNode.prior = len(self.parserNodes) - 1
        self.parserNodes.append(keywordNode)
        # Resume the current grammar.
        child.grammar = self.parserNodes[self.parserNodes[-1].prior].grammar
        child.begin = cursor + reg[1]
        child.prior = self.parserNodes[self.parserNodes[-1].prior].prior
        cursor += reg[1]
      else:
        # A special doesn't change the nodeIndex.
        specialNode = ParserNode()
        specialNode.grammar = app.prefs.grammars['special']
        specialNode.begin = cursor + reg[0]
        specialNode.prior = len(self.parserNodes) - 1
        self.parserNodes.append(specialNode)
        # Resume the current grammar.
        child.grammar = self.parserNodes[self.parserNodes[-1].prior].grammar
        child.begin = cursor + reg[1]
        child.prior = self.parserNodes[self.parserNodes[-1].prior].prior
        cursor += reg[1]
      self.parserNodes.append(child)

  def debugLog(self, out, data):
    out('parser debug:')
    out('RowList ----------------', len(self.rows))
    for i,start in enumerate(self.rows):
      if i + 1 < len(self.rows):
        end = self.rows[i + 1]
      else:
        end = sys.maxint
      out('row', i, '(line', str(i + 1) + ') index', start, 'to', end)
      for node in self.parserNodes[start:end]:
        if node is None:
          out('a None')
          continue
        node.debugLog(out, '  ', data)
