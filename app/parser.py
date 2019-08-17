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

# Keys to tuples within |parserNodes|.
# Reference to a prefs grammar dictionary.
kGrammar = 0
# The current grammar begins at byte offset |kBegin| in the source data.
kBegin = 1
# An index into the parserNodes list to the prior (or parent) grammar.
kPrior = 2
# Some characters display wider (or narrower) than others. Visual is a running
# display offset. E.g. if the first character in some utf-8 data is a double
# width and 3 bytes long the kBegin = 0, and kVisual = 0; the second character
# will start at kBegin = 3, kVisual = 2.
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
                #assert index < len(gl)  # Never return index to self.endNode.
                return index

    def grammarAt(self, row, col):
        """Get the grammar at row, col.
        It's more efficient to use grammarIndexFromRowCol() and grammarAtIndex()
        individually if grammars are requested contiguously. This function is
        just for one-off needs.
        """
        grammarIndex = self.grammarIndexFromRowCol(row, col)
        node, _, _, _ = self.grammarAtIndex(row, col, grammarIndex)
        return node.grammar

    def grammarAtIndex(self, row, col, index):
        """Call grammarIndexFromRowCol() to get the index parameter.

        Returns:
            (node, preceding, remaining, eol). |proceeding| and |remaining| are
            relative to the |col| parameter.
        """
        if app.config.strict_debug:
            assert isinstance(row, int)
            assert isinstance(col, int)
            assert isinstance(index, int)
            assert row < len(self.rows), row
        eol = True
        finalResult = (self.emptyNode, 0, 0, eol)
        rowIndex = self.rows[row]
        if rowIndex + index + 1 >= len(self.parserNodes):
            return finalResult
        nextOffset = self.parserNodes[rowIndex + index + 1][kVisual]
        offset = self.parserNodes[rowIndex][kVisual] + col
        remaining = nextOffset - offset
        if remaining < 0:
            return finalResult
        node = self.parserNodes[rowIndex + index]
        eol = False
        return ParserNode(*node), offset - node[kVisual], remaining, eol

    def grammarTextAt(self, row, col):
        """Get the run of text for the given position."""
        if app.config.strict_debug:
            assert isinstance(row, int)
            assert isinstance(col, int)
            assert row < len(self.rows), row
        rowIndex = self.rows[row]
        grammarIndex = self.grammarIndexFromRowCol(row, col)
        node = self.parserNodes[rowIndex + grammarIndex]
        nextNode = self.parserNodes[rowIndex + grammarIndex + 1]
        return (self.data[node[kBegin]:nextNode[kBegin]],
                node[kGrammar].get(u"link_type"))

    def inDocument(self, row, col):
        if app.config.strict_debug:
            assert isinstance(row, int)
            assert isinstance(col, int)
            assert row >= 0
            assert col >= 0
        return (row < len(self.rows) and
            col < self.parserNodes[self.rows[row]][kVisual])

    def nextCharRowCol(self, row, col):
        """Get the next column value for the character to the right.
        Returns: None if there is no remaining characters.
                 or (row, col) deltas of the next character in the document.
        """
        if app.config.strict_debug:
            assert isinstance(row, int)
            assert isinstance(col, int)
            assert row >= 0
            assert col >= 0
            assert len(self.rows) > 0
        ch = self.charAt(row, col)
        if ch is None:
            return (1, -col) if self.inDocument(row + 1, 0) else None
        return 0, app.curses_util.charWidth(ch, col)

    def priorCharRowCol(self, row, col):
        """Get the prior column value for the character to the left.
        Returns: None if there is no remaining characters.
                 or (row, col) deltas of the next character in the document.
        """
        if app.config.strict_debug:
            assert isinstance(row, int)
            assert isinstance(col, int)
            assert row >= 0
            assert col >= 0
            assert len(self.rows) > 0
        if col == 0:
            if row == 0:
                return None
            return (-1, self.rowWidth(row - 1))
        return 0, app.curses_util.priorCol(col, self.rowText(row)) - col

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
          endRow (int): The row to stop parsing. This stops the parser from
              going over the entire file if, for example, only 100 rows out of
              a million rows are needed (which can save a lot of cpu time).
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
            # First time parse. Do a parse of the whole file.
            self.parserNodes = [(grammar, 0, None, 0)]
            self.rows = [0]
        if self.endRow > len(self.rows):
            self.__buildGrammarList(bgThread, appPrefs)
        self.fullyParsedToLine = len(self.rows)
        self.__fastLineParse(grammar)
        #self.debug_checkLines(app.log.parser, data)
        #startTime = time.time()
        if app.log.enabledChannels.get('parser', False):
            self.debugLog(app.log.parser, data)
        #app.log.startup('parsing took', time.time() - startTime)

    def __fastLineParse(self, grammar):
        """If there's not enough time to thoroughly parse the file, identify the
        lines so that the document can still be edited.
        """
        data = self.data
        offset = self.parserNodes[self.rows[-1]][kBegin]
        visual = self.parserNodes[self.rows[-1]][kVisual]
        limit = len(data)
        while True:
            while offset < limit and data[offset] != '\n':
                if data[offset] >= app.curses_util.MIN_DOUBLE_WIDE_CHARACTER:
                    visual += 2
                else:
                    visual += 1
                offset += 1
            if offset >= limit:
                # Add a terminating (end) node.
                self.parserNodes.append((grammar, len(data), None, visual))
                break
            offset += 1
            visual += 1
            self.rows.append(len(self.parserNodes))
            self.parserNodes.append((grammar, offset, None, visual))

    def rowCount(self):
        return len(self.rows)

    def rowText(self, row):
        """Get the text for |row|.

        Args:
            row (int): row is zero based.

        Returns:
            document text (unicode)
        """
        if app.config.strict_debug:
            assert isinstance(row, int)
            assert isinstance(self.data, unicode)
        begin = self.parserNodes[self.rows[row]][kBegin]
        if row + 1 >= len(self.rows):
            return self.data[begin:]
        end = self.parserNodes[self.rows[row + 1]][kBegin]
        if len(self.data) and self.data[end - 1] == '\n':
            end -= 1
        return self.data[begin:end]

    def charAt(self, row, col):
        """Get the character at |row|, |col|.

        Args:
            row (int): zero based index into list of rows.
            col (int): zero based visual offset from start of line.

        Returns:
            character (unicode) or None if row, col is outside of the document.
        """
        if app.config.strict_debug:
            assert isinstance(row, int)
            assert isinstance(col, int)
            assert isinstance(self.data, unicode)
            assert row >= 0
            assert col >= 0
        if row > len(self.rows):
            return None
        string, width = self.rowTextAndWidth(row)
        if col > width:
            return None
        return app.curses_util.charAtColumn(col, string)

    def rowTextAndWidth(self, row):
        """Get the character data and the visual/display column width of those
        characters.

        If the text is all ASCII then len(text) will equal the column width. If
        there are double wide characters (e.g. Chinese or some emoji) the column
        width may be larger than len(text).

        Args:
            row (int): the row index is zero based (so it's line number - 1).

        Returns:
            (text, columnWidth) (tuple)
        """
        if app.config.strict_debug:
            assert isinstance(row, int)
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

    def rowWidth(self, row):
        """Get the visual/display column width of a row.

        If the text is all ASCII then len(text) will equal the column width. If
        there are double wide characters (e.g. Chinese or some emoji) the column
        width may be larger than len(text).

        Args:
            row (int): the row index is zero based (so it's `line_number - 1`).

        Returns:
            columnWidth (int)
        """
        if app.config.strict_debug:
            assert isinstance(row, int)
        if row < 0:
            row = len(self.rows) + row
        visual = self.parserNodes[self.rows[row]][kVisual]
        if row + 1 < len(self.rows):
            end = self.parserNodes[self.rows[row + 1]][kBegin]
            visualEnd = self.parserNodes[self.rows[row + 1]][kVisual]
            if len(self.data) and self.data[end - 1] == '\n':
                visualEnd -= 1
        else:
            # There is a sentinel node at the end that records the end of
            # document.
            lastNode = self.parserNodes[-1]
            visualEnd = lastNode[kVisual]
        return visualEnd - visual

    def __buildGrammarList(self, bgThread, appPrefs):
        """The guts of the parser. This is where the heavy lifting is done.

        This code can be interrupted (by |bgThread|) and resumed (by calling it
        again).
        """
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
                topNode = self.parserNodes[-1]
                regBegin, regEnd = reg
                # First, add any preceding single wide characters.
                if regBegin > 0:
                    self.parserNodes.append((topNode[kGrammar], cursor,
                                             topNode[kPrior], visual))
                    cursor += regBegin
                    visual += regBegin
                    # Remove the regular text from reg values.
                    regEnd -= regBegin
                    regBegin = 0
                # Resume current grammar; store the double wide characters.
                child = (topNode[kGrammar], cursor, topNode[kPrior], visual)
                cursor += regEnd
                visual += regEnd * 2
            elif index == len(foundGroups) - 3:
                # Found variable width character.
                topNode = self.parserNodes[-1]
                regBegin, regEnd = reg
                # First, add any preceding single wide characters.
                if regBegin > 0:
                    self.parserNodes.append((topNode[kGrammar], cursor,
                                             topNode[kPrior], visual))
                    cursor += regBegin
                    visual += regBegin
                    # Remove the regular text from reg values.
                    regEnd -= regBegin
                    regBegin = 0
                # Add tabs grammar; store the variable width characters.
                rowStart = self.parserNodes[self.rows[-1]][kVisual]
                col = visual - rowStart
                # Advance to the next tab stop.
                self.parserNodes.append((appPrefs.grammars['tabs'], cursor,
                        topNode[kPrior], visual))
                cursor += regEnd
                visual = rowStart + ((col + 8) // 8 * 8)
                visual += (regEnd - 1) * 8
                # Resume current grammar; store the variable width characters.
                child = (topNode[kGrammar], cursor, topNode[kPrior], visual)
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
                    containsGrammarIndexLimit, nextGrammarIndexLimit,
                    errorIndexLimit, keywordIndexLimit, typeIndexLimit,
                    specialIndexLimit
                ] = self.parserNodes[-1][kGrammar]['indexLimits']
                if index < containsGrammarIndexLimit:
                    # A new grammar within this grammar (a 'contains').
                    if subdata[reg[0]] == '\n':
                        # This 'begin' begins with a new line.
                        self.rows.append(len(self.parserNodes))
                    priorGrammar = self.parserNodes[-1][kGrammar].get(
                        'matchGrammars', [])[index]
                    if priorGrammar['end'] is None:
                        # Found single regex match (a leaf grammar).
                        self.parserNodes.append((priorGrammar, cursor + reg[0],
                                                 len(self.parserNodes) - 1,
                                                 visual + reg[0]))
                        # Resume the current grammar.
                        child = (self.parserNodes[self.parserNodes[-1][kPrior]]
                                 [kGrammar], cursor + reg[1], self.parserNodes[
                                     self.parserNodes[-1][kPrior]][kPrior],
                                 visual + reg[1])
                    else:
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
                elif index < nextGrammarIndexLimit:
                    # A new grammar follows this grammar (a 'next').
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
                             len(self.parserNodes) - 2, visual + reg[0])
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
                end = len(self.parserNodes)
            out('row', i, '(line', str(i + 1) + ') index', start, 'to', end)
            for node in self.parserNodes[start:end]:
                if node is None:
                    out('a None')
                    continue
                nodeBegin = node[kBegin]
                out('  ParserNode %26s prior %4s, b%4d, v%4d, %s' % (
                    node[kGrammar].get('name', 'None'), node[kPrior], nodeBegin,
                    node[kVisual], repr(data[nodeBegin:nodeBegin + 15])[1:-1]))

    def debug_checkLines(self, out, data):
        """Debug test that all the lines were recognized by the parser. This is
        very slow, so it's normally disabled.
        """
        # Check that all the lines got identified.
        lines = data.split(u"\n")
        if out is not None:
            out(lines)
        assert len(lines) == self.rowCount()
        for i, line in enumerate(lines):
            parsedLine, columnWidth = self.rowTextAndWidth(i)
            assert line == parsedLine, "\nexpected:{}\n  actual:{}".format(
                repr(line), repr(parsedLine))
            parsedLine = self.rowText(i)
            assert line == parsedLine, "\nexpected:{}\n  actual:{}".format(
                line, parsedLine)

            if out is not None:
                out("----------- ", line)
            piecedLine = u""
            k = 0
            grammarIndex = 0
            while True:
                node, preceding, remaining, eol = self.grammarAtIndex(
                    i, k, grammarIndex)
                grammarIndex += 1
                piecedLine += line[k - preceding:k + remaining]
                if out is not None:
                    out(i, preceding, remaining, i, k, piecedLine)
                if eol:
                    assert piecedLine == line, (
                        "\nexpected:{}\n  actual:{}".format(
                            repr(line), repr(piecedLine)))
                    break
                k += remaining
