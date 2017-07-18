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
    self.begin = None  # Offset from start of file.

  def debugLog(self, out, indent, data):
    out('%sParserNode %16s %4d %s' % (indent, self.grammar.get('name', 'None'),
        self.begin, repr(data[self.begin:self.begin+15])[1:-1]))


class Parser:
  """A parser generates a set of grammar segments (ParserNode objects)."""
  def __init__(self):
    self.data = ""
    self.grammarRowList = []
    app.log.parser('__init__')

  def grammarFromRowCol(self, row, col):
    sentinel = ParserNode()
    sentinel.grammar = {}
    sentinel.begin = sys.maxint
    sentinel.col = sys.maxint
    if row >= len(self.grammarRowList):
      # This file is too large. There's other ways to handle this, but for now
      # let's leave the tail un-highlighted.
      empty = ParserNode()
      empty.grammar = {}
      return empty, 0, sys.maxint
    gl = self.grammarRowList[row] + [sentinel]
    offset = gl[0].begin + col
    # Binary search to find the node for the column.
    low = 0
    high = len(gl)-1
    while True:
      index = (high+low)/2
      if offset >= gl[index+1].begin:
        low = index
      elif offset < gl[index].begin:
        high = index
      else:
        return gl[index], offset - gl[index].begin, gl[index+1].begin-offset

  def parse(self, data, grammar):
    app.log.parser('grammar', grammar['name'])
    self.data = data
    node = ParserNode()
    node.grammar = grammar
    node.begin = 0
    self.grammarRowList = [[node]]
    startTime = time.time()
    self.buildGrammarList()
    totalTime = time.time() - startTime
    if app.log.enabledChannels.get('parser', False):
      self.debugLog(app.log.parser, data)
    app.log.startup('parsing took', totalTime)

  def buildGrammarList(self):
    # An arbitrary limit to avoid run-away looping.
    leash = 10000
    cursor = 0
    grammarStack = [self.grammarRowList[0][-1].grammar]
    while len(grammarStack):
      if not leash:
        app.log.error('grammar likely caught in a loop')
        break
      leash -= 1
      subdata = self.data[cursor:]
      found = grammarStack[-1].get('matchRe').search(subdata)
      if not found:
        grammarStack.pop()
        # todo(dschuyler): mark parent grammars as unterminated (if they expect
        # be terminated. e.g. unmatched string quote or xml tag.
        break
      index = -1
      for i,k in enumerate(found.groups()):
        if k is not None:
          index = i
          break
      assert index >= 0
      reg = found.regs[index+1]
      if index == 0:
        # Found escaped value.
        cursor += reg[1]
        continue
      child = ParserNode()
      if index == len(found.groups()) - 1:
        # Found new line.
        if 0:
          remaining = ParserNode()
          remaining.grammar = {}
          remaining.begin = cursor + reg[0] + 1
          self.grammarRowList[-1].append(remaining)

        child.grammar = grammarStack[-1]
        child.begin = cursor + reg[1]
        cursor = child.begin
        self.grammarRowList.append([])
      elif index == 1:
        # Found end of current grammar section (an 'end').
        grammarStack.pop()
        child.grammar = grammarStack[-1]
        child.begin = cursor + reg[1]
        cursor = child.begin
        if subdata[reg[0]:reg[1]] == '\n':
          if 0:
            remaining = ParserNode()
            remaining.grammar = {}
            remaining.begin = cursor + reg[0] + 1
            self.grammarRowList[-1].append(remaining)
          self.grammarRowList.append([])
      else:
        # A new grammar within this grammar (a 'contains').
        child.grammar = grammarStack[-1].get('matchGrammars', [])[index]
        child.begin = cursor + reg[0]
        cursor += reg[1]
        grammarStack.append(child.grammar)
      if len(self.grammarRowList[0]) and self.grammarRowList[0][-1].begin == child.begin:
        self.grammarRowList[-1][-1] = child
      else:
        self.grammarRowList[-1].append(child)

  def debugLog(self, out, data):
    out('parser debug:')
    out('RowList ----------------', len(self.grammarRowList))
    for i,rowList in enumerate(self.grammarRowList):
      out('row', i+1)
      for node in rowList:
        if node is None:
          out('a None')
          continue
        node.debugLog(out, '  ', data)

