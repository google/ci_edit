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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
try:
    unicode
except NameError:
    unicode = str
    unichr = chr

import curses.ascii
import os
import re
import sys
import time
import traceback

import third_party.pyperclip as clipboard

import app.config
import app.log
import app.selectable

kGrammar = 0
kBegin = 1
kPrior = 2
kVisual = 3


class ParserNode:
    """A parser node represents a span of grammar. i.e. from this point to that
      point is HTML. Another parser node would represent the next segment, of
      grammar (maybe JavaScript, CSS, comment, or quoted string for example."""

    def __init__(self, grammar, begin, prior, visual):
        self.grammar = grammar
        # Offset from start of file.
        self.begin = begin
        # Index of prior grammar (like a stack of grammars).
        self.prior = prior
        # Visible width on screen (double wide chars, and tabs).
        self.visual = visual

    def debugLog(self, out, indent, data):
        out('%sParserNode %26s prior %4s, b%4d, v%4d %s' %
            (indent, self.grammar.get('name', 'None'), self.prior, self.begin,
             self.visual, repr(data[self.begin:self.begin + 15])[1:-1]))


class Parser:
    """A parser generates a set of grammar segments (ParserNode objects)."""

    def __init__(self):
        self.data = u""
        self.emptyNode = ParserNode({}, None, None, 0)
        self.endNode = ({}, sys.maxsize, sys.maxsize, sys.maxsize)
        self.fullyParsedToLine = -1
        # A row on screen will consist of one or more ParserNodes. When a
        # ParserNode is returned from the parser it will be an instance of
        # ParserNode, but internally tuples are used in place of ParserNodes.
        # This makes for some ugly code, but the performance difference (~5%) is
        # worth it.
        self.parserNodes = [({}, 0, None, 0)]
        # Each entry in |self.rows| is an index into the |self.parserNodes|
        # array to the parerNode that begins that row.
        self.rows = [0]  # Row parserNodes index.
        app.log.parser('__init__')

    def grammarIndexFromRowCol(self, row, col):
        """
        Returns:
            index. |index| may then be passed to grammarAtIndex().
        """
        if row + 1 >= len(
                self.rows):  # or self.rows[row + 1] > len(self.parserNodes):
            # This file is too large. There's other ways to handle this, but for
            # now let's leave the tail un-highlighted.
            return 0
        gl = self.parserNodes[self.rows[row]:self.rows[row + 1]] + [
            self.endNode
        ]
        offset = gl[0][kVisual] + col
        # Binary search to find the node for the column.
        low = 0
        high = len(gl) - 1
        while True:
            index = (high + low) // 2
            if offset >= gl[index + 1][kVisual]:
                low = index
            elif offset < gl[index][kVisual]:
                high = index
            else:
                return index

    def grammarAt(self, row, col):
        """Get the grammar at row, col.
        It's more efficient to use grammarIndexFromRowCol() and grammarAtIndex()
        individually if grammars are requested contiguously. This function is
        just for one-off needs.
        """
        grammarIndex = self.grammarIndexFromRowCol(row, col)
        node, _, _ = self.grammarAtIndex(row, col, grammarIndex)
        return node.grammar

    def grammarAtIndex(self, row, col, index):
        """Call grammarIndexFromRowCol() to get the index parameter.

        Returns:
            (node, preceding, remaining). |proceeding| and |remaining| are
            relative to the |col| parameter.
        """
        finalResult = (self.emptyNode, col, sys.maxsize)
        if row >= len(self.rows):
            return finalResult
        rowIndex = self.rows[row]
        if rowIndex + index >= len(self.parserNodes):
            return finalResult
        offset = self.parserNodes[rowIndex][kVisual] + col
        nextOffset = sys.maxsize
        if rowIndex + index + 1 < len(self.parserNodes):
            nextOffset = self.parserNodes[rowIndex + index + 1][kVisual]
        remaining = nextOffset - offset
        if remaining < 0:
            return finalResult
        node = self.parserNodes[rowIndex + index]
        return ParserNode(*node), offset - node[kVisual], remaining

    def parse(self, bgThread, appPrefs, data, grammar, beginRow, endRow):
        """
        Args:
          data (string): The file contents. The document.
          grammar (object): The initial grammar (often determined by the file
              extension). If |beginRow| is not zero then grammar is ignored.
          beginRow (int): is the first row (which is line number - 1) in data
              that is has changed since the previous parse of this data. Pass
              zero to parse the entire document. If beginRow >= len(data) then
              no parse is done.
          endRow (int): The last row to parse. This stops the parser from going
              over the entire file if, for example, only 100 rows out of a
              million rows are needed (which can save a lot of cpu time).
        """
        app.log.parser('grammar', grammar['name'])
        # Trim partially parsed data.
        if self.fullyParsedToLine < beginRow:
            beginRow = self.fullyParsedToLine

        self.emptyNode = ParserNode(grammar, None, None, 0)
        self.data = data
        self.endRow = endRow
        if beginRow > 0:  # and len(self.rows):
            if beginRow < len(self.rows):
                self.parserNodes = self.parserNodes[:self.rows[beginRow]]
                self.rows = self.rows[:beginRow]
        else:
            # First time parse. Do a fast parse of the whole file.
            self.parserNodes = [(grammar, 0, None, 0)]
            self.rows = [0]
        if self.endRow > len(self.rows):
            self.__buildGrammarList(bgThread, appPrefs)
        self.fullyParsedToLine = len(self.rows)
        self.__fastLineParse(grammar)
        #startTime = time.time()
        if app.log.enabledChannels.get('parser', False):
            self.debugLog(app.log.parser, data)
        #app.log.startup('parsing took', time.time() - startTime)

    def __fastLineParse(self, grammar):
        data = self.data
        index = self.parserNodes[self.rows[-1]][kBegin]
        visual = self.parserNodes[self.rows[-1]][kVisual]
        limit = len(data)
        while True:
            while index < limit and data[index] != '\n':
                if data[index] >= app.curses_util.MIN_DOUBLE_WIDE_CHARACTER:
                    visual += 2
                else:
                    visual += 1
                index += 1
            if index >= limit:
                # New line not found.
                break
            index += 1
            self.rows.append(len(self.parserNodes))
            self.parserNodes.append((grammar, index, None, visual))
        if self.parserNodes[-1][kBegin] != sys.maxsize:
            # End node, points just past the end of the document.
            self.parserNodes.append((grammar, sys.maxsize, None, visual))

    def rowCount(self):
        return len(self.rows)

    def rowText(self, row):
        if app.config.strict_debug:
            assert isinstance(row, int)
            assert isinstance(self.data, unicode)
        begin = self.parserNodes[self.rows[row]][kBegin]
        if row + 1 < len(self.rows):
            end = self.parserNodes[self.rows[row + 1]][kBegin]
            if len(self.data) and self.data[end - 1] == '\n':
                end -= 1
        else:
            end = sys.maxsize
        return self.data[begin:end]

    def rowTextAndWidth(self, row):
        begin = self.parserNodes[self.rows[row]][kBegin]
        visual = self.parserNodes[self.rows[row]][kVisual]
        if row + 1 < len(self.rows):
            end = self.parserNodes[self.rows[row + 1]][kBegin]
            visualEnd = self.parserNodes[self.rows[row + 1]][kVisual]
            if len(self.data) and self.data[end - 1] == '\n':
                end -= 1
                visualEnd -= 1
        else:
            # There is a sentinel node at the end that records the end of
            # document.
            lastNode = self.parserNodes[-1]
            end = lastNode[kBegin]
            visualEnd = lastNode[kVisual]
        return self.data[begin:end], visualEnd - visual

    def __buildGrammarList(self, bgThread, appPrefs):
        # An arbitrary limit to avoid run-away looping.
        leash = 50000
        topNode = self.parserNodes[-1]
        cursor = topNode[kBegin]
        visual = topNode[kVisual]
        # If we are at the start of a grammar, skip the 'begin' part of the
        # grammar.
        if (len(self.parserNodes) == 1 or
                topNode[kGrammar] is not self.parserNodes[-2][kGrammar]):
            beginRegex = topNode[kGrammar].get('begin')
            if beginRegex is not None:
                sre = re.match(beginRegex, self.data[cursor:])
                if sre is not None:
                    cursor += sre.regs[0][1]
                    visual += sre.regs[0][1]  # Assumes single-wide characters.
        while self.endRow > len(self.rows):
            if not leash:
                #app.log.error('grammar likely caught in a loop')
                break
            leash -= 1
            if bgThread and bgThread.hasUserEvent():
                break
            subdata = self.data[cursor:]
            found = self.parserNodes[-1][kGrammar].get('matchRe').search(
                subdata)
            if not found:
                #app.log.info('parser exit, match not found')
                # todo(dschuyler): mark parent grammars as unterminated (if they
                # expect be terminated). e.g. unmatched string quote or xml tag.
                break
            index = -1
            foundGroups = found.groups()
            for k in foundGroups:
                index += 1
                if k is not None:
                    break
            reg = found.regs[index + 1]
            if index == 0:
                # Found escaped value.
                cursor += reg[1]
                visual += reg[1]
                continue
            if index == len(foundGroups) - 1:
                # Found new line.
                child = (self.parserNodes[-1][kGrammar], cursor + reg[1],
                         self.parserNodes[-1][kPrior], visual + reg[1])
                cursor += reg[1]
                visual += reg[1]
                self.rows.append(len(self.parserNodes))
            elif index == len(foundGroups) - 2:
                # Found double wide character.
                self.parserNodes.append(
                    (appPrefs.grammars['text'], cursor + reg[0],
                     len(self.parserNodes) - 1, visual + reg[0]))
                # Resume the current grammar.
                child = (
                    self.parserNodes[self.parserNodes[-1][kPrior]][kGrammar],
                    cursor + reg[1],
                    self.parserNodes[self.parserNodes[-1][kPrior]][kPrior],
                    visual + reg[1] * 2)
                cursor += reg[1]
                visual += reg[1] * 2
            elif index == 1:
                # Found end of current grammar section (an 'end').
                child = (
                    self.parserNodes[self.parserNodes[-1][kPrior]][kGrammar],
                    cursor + reg[1],
                    self.parserNodes[self.parserNodes[-1][kPrior]][kPrior],
                    visual + reg[1])
                cursor = child[kBegin]
                visual += reg[1]
                if subdata[reg[1] - 1] == '\n':
                    # This 'end' ends with a new line.
                    self.rows.append(len(self.parserNodes))
            else:
                [
                    newGrammarIndexLimit, errorIndexLimit, keywordIndexLimit,
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
                        hereKey = re.search(priorGrammar['end_key'],
                                            subdata[reg[0]:]).groups()[0]
                        markers = priorGrammar['markers']
                        markers[1] = priorGrammar['end'].replace(
                            r'\0', re.escape(hereKey))
                        priorGrammar['matchRe'] = re.compile(
                            app.regex.joinReList(markers))
                    child = (priorGrammar, cursor + reg[0],
                             len(self.parserNodes) - 1, visual + reg[0])
                    cursor += reg[1]
                    visual += reg[1]
                elif index < errorIndexLimit:
                    # A special doesn't change the nodeIndex.
                    self.parserNodes.append(
                        (appPrefs.grammars['error'], cursor + reg[0],
                         len(self.parserNodes) - 1, visual + reg[0]))
                    # Resume the current grammar.
                    child = (
                        self.parserNodes[self.parserNodes[-1]
                                         [kPrior]][kGrammar], cursor + reg[1],
                        self.parserNodes[self.parserNodes[-1][kPrior]][kPrior],
                        visual + reg[1])
                    cursor += reg[1]
                    visual += reg[1]
                elif index < keywordIndexLimit:
                    # A keyword doesn't change the nodeIndex.
                    self.parserNodes.append(
                        (appPrefs.grammars['keyword'], cursor + reg[0],
                         len(self.parserNodes) - 1, visual + reg[0]))
                    # Resume the current grammar.
                    child = (
                        self.parserNodes[self.parserNodes[-1]
                                         [kPrior]][kGrammar], cursor + reg[1],
                        self.parserNodes[self.parserNodes[-1][kPrior]][kPrior],
                        visual + reg[1])
                    cursor += reg[1]
                    visual += reg[1]
                elif index < typeIndexLimit:
                    # A type doesn't change the nodeIndex.
                    self.parserNodes.append(
                        (appPrefs.grammars['type'], cursor + reg[0],
                         len(self.parserNodes) - 1, visual + reg[0]))
                    # Resume the current grammar.
                    child = (
                        self.parserNodes[self.parserNodes[-1]
                                         [kPrior]][kGrammar], cursor + reg[1],
                        self.parserNodes[self.parserNodes[-1][kPrior]][kPrior],
                        visual + reg[1])
                    cursor += reg[1]
                    visual += reg[1]
                elif index < specialIndexLimit:
                    # A special doesn't change the nodeIndex.
                    self.parserNodes.append(
                        (appPrefs.grammars['special'], cursor + reg[0],
                         len(self.parserNodes) - 1, visual + reg[0]))
                    # Resume the current grammar.
                    child = (
                        self.parserNodes[self.parserNodes[-1]
                                         [kPrior]][kGrammar], cursor + reg[1],
                        self.parserNodes[self.parserNodes[-1][kPrior]][kPrior],
                        visual + reg[1])
                    cursor += reg[1]
                    visual += reg[1]
                else:
                    app.log.error('invalid grammar index')
            self.parserNodes.append(child)

    def debugLog(self, out, data):
        out('parser debug:')
        out('RowList ----------------', len(self.rows))
        for i, start in enumerate(self.rows):
            if i + 1 < len(self.rows):
                end = self.rows[i + 1]
            else:
                end = sys.maxsize
            out('row', i, '(line', str(i + 1) + ') index', start, 'to', end)
            for node in self.parserNodes[start:end]:
                if node is None:
                    out('a None')
                    continue
                nodeBegin = node[kBegin]
                out('  ParserNode %26s prior %4s, b%4d, v%4d, %s' % (
                    node[kGrammar].get('name', 'None'), node[kPrior], nodeBegin,
                    node[kVisual], repr(data[nodeBegin:nodeBegin + 15])[1:-1]))
