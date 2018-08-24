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

import curses.ascii
import os
import re
import sys
import time
import traceback

import third_party.pyperclip as clipboard

import app.background
import app.log
import app.selectable
import app.prefs


kGrammar = 0
kBegin = 1
kPrior = 2

class ParserNode:
  """A parser node represents a span of grammar. i.e. from this point to that
      point is HTML. Another parser node would represent the next segment, of
      grammar (maybe JavaScript, CSS, comment, or quoted string for example."""
  def __init__(self, grammar, begin, prior):
    self.grammar = grammar
    self.begin = begin  # Offset from start of file.
    self.prior = prior  # Index of prior grammar (like a stack of grammars).

  def debugLog(self, out, indent, data):
    out('%sParserNode %26s prior %4s %4d %s' % (indent,
        self.grammar.get('name', 'None'),
        self.prior, self.begin, repr(data[self.begin:self.begin+15])[1:-1]))


class Parser:
  """A parser generates a set of grammar segments (ParserNode objects)."""
  def __init__(self):
    self.data = ""
    self.emptyNode = ParserNode({}, None, None)
    self.endNode = ({}, sys.maxint, sys.maxint)
    # A row on screen will consist of one or more ParserNodes. When a ParserNode
    # is returned from the parser it will be an instance of ParserNode, but
    # internally tuples are used in place of ParserNodes. This makes for some
    # ugly code, but the performance difference (~5%) is worth it.
    self.parserNodes = []
    # Each entry in |self.rows| is an index into the |self.parserNodes| array to
    # the parerNode that begins that row.
    self.rows = []  # Row parserNodes index.
    app.log.parser('__init__')

  def grammarIndexFromRowCol(self, row, col):
    """
    Returns:
        index. |index| may then be passed to grammarAtIndex().
    """
    if row + 1 >= len(self.rows): # or self.rows[row + 1] > len(self.parserNodes):
      # This file is too large. There's other ways to handle this, but for now
      # let's leave the tail un-highlighted.
      return 0
    gl = self.parserNodes[self.rows[row]:self.rows[row + 1]] + [self.endNode]
    offset = gl[0][kBegin] + col
    # Binary search to find the node for the column.
    low = 0
    high = len(gl) - 1
    while True:
      index = (high + low) / 2
      if offset >= gl[index + 1][kBegin]:
        low = index
      elif offset < gl[index][kBegin]:
        high = index
      else:
        return index

  def grammarAt(self, row, col):
    """
    Get the grammar at row, col.
    It's more efficient to use grammarIndexFromRowCol() and grammarAtIndex()
    individually if grammars are requested contiguously. This function is just
    for one-off needs.
    """
    grammarIndex = self.grammarIndexFromRowCol(row, col)
    node, _, _ = self.grammarAtIndex(row, col, grammarIndex)
    return node.grammar

  def grammarAtIndex(self, row, col, index):
    """
    Call grammarIndexFromRowCol() to get the index parameter.

    Returns:
        (node, preceding, remaining). |proceeding| and |remaining| are relative
        to the |col| parameter.
    """
    finalResult = (self.emptyNode, col, sys.maxint)
    if row >= len(self.rows):
      return finalResult
    rowIndex = self.rows[row]
    if rowIndex + index >= len(self.parserNodes):
      return finalResult
    offset = self.parserNodes[rowIndex][kBegin] + col
    nextOffset = sys.maxint
    if rowIndex + index + 1 < len(self.parserNodes):
      nextOffset = self.parserNodes[rowIndex + index + 1][kBegin]
    remaining = nextOffset - offset
    if remaining < 0:
      return finalResult
    node = self.parserNodes[rowIndex + index]
    return apply(ParserNode, node), offset - node[kBegin], remaining

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
            over the entire file if, for example, only 100 rows out of a million
            rows are needed (which can save a lot of cpu time).
    """
    app.log.parser('grammar', grammar['name'])
    self.emptyNode = ParserNode(grammar, None, None)
    self.data = data
    self.endRow = endRow
    if beginRow > 0 and len(self.rows):
      if beginRow < len(self.rows):
        self.parserNodes = self.parserNodes[:self.rows[beginRow]]
        self.rows = self.rows[:beginRow]
    else:
      self.parserNodes = [(grammar, 0, None)]
      self.rows = [0]
    #startTime = time.time()
    if self.endRow > len(self.rows):
      self.__buildGrammarList()
    if app.log.enabledChannels.get('parser', False):
      self.debugLog(app.log.parser, data)
    #app.log.startup('parsing took', time.time() - startTime)

  def __buildGrammarList(self):
    # An arbitrary limit to avoid run-away looping.
    leash = 50000
    topNode = self.parserNodes[-1]
    cursor = topNode[kBegin]
    # If we are at the start of a grammar, skip the 'begin' part of the grammar.
    if (len(self.parserNodes) == 1 or
        topNode[kGrammar] is not self.parserNodes[-2][kGrammar]):
      beginRegex = topNode[kGrammar].get('begin')
      if beginRegex is not None:
        sre = re.match(beginRegex, self.data[cursor:])
        if sre is not None:
          cursor += sre.regs[0][1]
    while self.endRow > len(self.rows):
      if not leash:
        #app.log.error('grammar likely caught in a loop')
        break
      leash -= 1
      if app.background.bg and app.background.bg.hasUserEvent():
        break
      subdata = self.data[cursor:]
      found = self.parserNodes[-1][kGrammar].get('matchRe').search(subdata)
      if not found:
        #app.log.info('parser exit, match not found')
        # todo(dschuyler): mark parent grammars as unterminated (if they expect
        # be terminated). e.g. unmatched string quote or xml tag.
        break
      index = -1
      foundGroups = found.groups()
      for k in foundGroups:
        index += 1
        if k is not None:
          break
      #assert index >= 0
      reg = found.regs[index + 1]
      if index == 0:
        # Found escaped value.
        cursor += reg[1]
        continue
      if index == len(foundGroups) - 1:
        # Found new line.
        child = (self.parserNodes[-1][kGrammar], cursor + reg[1],
            self.parserNodes[-1][kPrior])
        cursor = child[kBegin]
        self.rows.append(len(self.parserNodes))
      elif index == 1:
        # Found end of current grammar section (an 'end').
        child = (self.parserNodes[self.parserNodes[-1][kPrior]][kGrammar],
            cursor + reg[1],
            self.parserNodes[self.parserNodes[-1][kPrior]][kPrior])
        cursor = child[kBegin]
        if subdata[reg[1] - 1] == '\n':
          # This 'end' ends with a new line.
          self.rows.append(len(self.parserNodes))
      else:
        [newGrammarIndexLimit, errorIndexLimit, keywordIndexLimit,
            typeIndexLimit, specialIndexLimit
            ] = self.parserNodes[-1][kGrammar]['indexLimits']
        if index < newGrammarIndexLimit:
          # A new grammar within this grammar (a 'contains').
          if subdata[reg[0]] == '\n':
            # This 'begin' begins with a new line.
            self.rows.append(len(self.parserNodes))
          priorGrammar = self.parserNodes[-1][kGrammar].get(
              'matchGrammars', [])[index]
          if priorGrammar.get('end_key'):
            # A dynamic end tag.
            hereKey = re.search(
                priorGrammar['end_key'], subdata[reg[1]:]).groups()[0]
            markers = priorGrammar['markers']
            markers[1] = priorGrammar['end'].replace(r'\0', re.escape(hereKey))
            priorGrammar['matchRe'] = re.compile(app.prefs.joinReList(markers))
          child = (priorGrammar, cursor + reg[0], len(self.parserNodes) - 1)
          cursor += reg[1]
        elif index < errorIndexLimit:
          # A special doesn't change the nodeIndex.
          self.parserNodes.append((app.prefs.grammars['error'], cursor + reg[0],
              len(self.parserNodes) - 1))
          # Resume the current grammar.
          child = (self.parserNodes[self.parserNodes[-1][kPrior]][kGrammar],
              cursor + reg[1],
              self.parserNodes[self.parserNodes[-1][kPrior]][kPrior])
          cursor += reg[1]
        elif index < keywordIndexLimit:
          # A keyword doesn't change the nodeIndex.
          self.parserNodes.append((app.prefs.grammars['keyword'],
              cursor + reg[0], len(self.parserNodes) - 1))
          # Resume the current grammar.
          child = (self.parserNodes[self.parserNodes[-1][kPrior]][kGrammar],
              cursor + reg[1],
              self.parserNodes[self.parserNodes[-1][kPrior]][kPrior])
          cursor += reg[1]
        elif index < typeIndexLimit:
          # A type doesn't change the nodeIndex.
          self.parserNodes.append((app.prefs.grammars['type'], cursor + reg[0],
              len(self.parserNodes) - 1))
          # Resume the current grammar.
          child = (self.parserNodes[self.parserNodes[-1][kPrior]][kGrammar],
              cursor + reg[1],
              self.parserNodes[self.parserNodes[-1][kPrior]][kPrior])
          cursor += reg[1]
        elif index < specialIndexLimit:
          # A special doesn't change the nodeIndex.
          self.parserNodes.append((app.prefs.grammars['special'],
              cursor + reg[0], len(self.parserNodes) - 1))
          # Resume the current grammar.
          child = (self.parserNodes[self.parserNodes[-1][kPrior]][kGrammar],
              cursor + reg[1],
              self.parserNodes[self.parserNodes[-1][kPrior]][kPrior])
          cursor += reg[1]
        else:
          app.log.error('invalid grammar index')
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
