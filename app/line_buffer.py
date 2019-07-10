# Copyright 2019 Google Inc.
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

import re
import time

import app.config
import app.log
import app.parser

class LineBuffer:

    def __init__(self, program):
        self.program = program
        self.debugUpperChangedRow = -1
        self.isBinary = False
        self.lines = [u""]
        self.parser = app.parser.Parser()
        self.parserTime = .0
        self.message = (u"New buffer", None)
        self.rootGrammar = self.program.prefs.getGrammar(None)
        self.upperChangedRow = 0

    def doLinesToBinaryData(self, lines):
        # TODO(dschuyler): convert lines to binary data.
        return ''

    def doLinesToData(self, lines):

        def encode(line):
            return chr(int(line.groups()[0], 16))

        return re.sub(u'\x01([0-9a-fA-F][0-9a-fA-F])', encode, "\n".join(lines))

    def doBinaryDataToLines(self, data):
        long_hex = binascii.hexlify(data)
        hex_list = []
        i = 0
        width = 32
        while i < len(long_hex):
            hex_list.append(long_hex[i:i + width] + '\n')
            i += width
        return hex_list

    def doDataToLines(self, data):
        if app.config.strict_debug:
            assert isinstance(data, unicode)
        # Performance: in a 1000 line test it appears fastest to do some simple
        # .replace() calls to minimize the number of calls to parse().
        data = data.replace(u'\r\n', u'\n')
        data = data.replace(u'\r', u'\n')
        tabSize = self.program.prefs.editor.get(u"tabSize", 8)
        data = data.expandtabs(tabSize)

        def parse(sre):
            return u"\x01%02x" % ord(sre.groups()[0])

        #data = re.sub(u'([\0-\x09\x0b-\x1f\x7f-\xff])', parse, data)
        data = re.sub(u'([\0-\x09\x0b-\x1f])', parse, data)
        return data.split(u'\n')

    def dataToLines(self):
        if self.isBinary:
            self.lines = self.doDataToLines(self.data)
            #self.lines = self.doBinaryDataToLines(self.data)
        else:
            self.lines = self.doDataToLines(self.data)

    def doParse(self, begin, end):
        start = time.time()
        self.linesToData()
        self.parser.parse(self.program.bg, self.program.prefs, self.data,
                          self.rootGrammar, begin, end)
        self.debugUpperChangedRow = self.upperChangedRow
        self.upperChangedRow = self.parser.fullyParsedToLine
        self.parserTime = time.time() - start

    def isEmpty(self):
        return len(self.lines) == 1 and len(self.lines[0]) == 0

    def linesToData(self):
        if self.isBinary:
            self.data = self.doLinesToData(self.lines)
            # TODO(dschuyler): convert binary data.
            #self.data = self.doLinesToBinaryData(self.lines)
        else:
            self.data = self.doLinesToData(self.lines)

    def parseDocument(self):
        begin = min(self.parser.fullyParsedToLine, self.upperChangedRow)
        end = self.parser.rowCount() + 1
        self.doParse(begin, end)

    def setMessage(self, *args, **kwargs):
        if not len(args):
            self.message = None
            #app.log.caller()
            return
        msg = str(args[0])
        prior = msg
        for i in args[1:]:
            if not len(prior) or prior[-1] != '\n':
                msg += ' '
            prior = str(i)
            msg += prior
        if app.config.strict_debug:
            app.log.caller("\n", msg)
        self.message = (repr(msg)[1:-1], kwargs.get('color'))
