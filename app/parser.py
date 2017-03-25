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
import time
import traceback


class ParserNode:
  """A parser node represents a span of grammar. i.e. from this point to that
      point is HTML. Another parser node would represent the next segment, of
      grammar (maybe JavaScript, CSS, comment, or quoted string for example."""
  def __init__(self):
    self.grammar = None
    self.begin = None

  def debugLog(self, out, indent, data):
    out('%sParserNode %16s %4d %s' % (indent, self.grammar.get('name', 'None'),
        self.begin, repr(data[self.begin:self.begin+15])[1:-1]))


class Parser:
  """A parser generates a set of grammar segments (ParserNode objects)."""
  def __init__(self):
    self.data = ""
    self.grammarPrefs = app.prefs.prefs['grammar']
    self.grammarList = []
    app.log.parser('__init__')

  def grammarFromOffset(self, offset):
    gl = self.grammarList
    low = 0
    high = len(gl)-1
    while True:
      index = (high+low)/2
      if offset >= gl[index+1].begin:
        low = index
      elif offset < gl[index].begin:
        high = index
      else:
        return gl[index], gl[index+1].begin-offset

  def parse(self, data, grammar):
    app.log.parser('grammar', grammar['name'])
    self.data = data
    node = ParserNode()
    node.grammar = grammar
    node.begin = 0
    self.grammarList = [node]
    startTime = time.time()
    self.buildGrammarList()
    totalTime = time.time() - startTime
    self.debugLog(app.log.parser, data)
    app.log.startup('parsing took', totalTime)

  def buildGrammarList(self):
    leash = 30000
    cursor = 0
    grammarStack = [self.grammarList[-1].grammar]
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
      if index == 1:
        # Found end of current grammar section (an 'end').
        grammarStack.pop()
        child.grammar = grammarStack[-1]
        child.begin = cursor + reg[1]
        cursor = child.begin
      else:
        # A new grammar within this grammar (a 'contains').
        child.grammar = grammarStack[-1].get('matchGrammars', [])[index]
        child.begin = cursor + reg[0]
        cursor += reg[1]
        grammarStack.append(child.grammar)
      if len(self.grammarList) and self.grammarList[-1].begin == child.begin:
        self.grammarList[-1] = child
      else:
        self.grammarList.append(child)
    sentinel = ParserNode()
    sentinel.grammar = {}
    sentinel.begin = sys.maxint
    self.grammarList.append(sentinel)

  def debugLog(self, out, data):
    out('parser debug:')
    for node in self.grammarList:
      node.debugLog(out, '  ', data)

