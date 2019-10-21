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
import sys
import time

import app.config
import app.log
import app.parser

class LineBuffer:

    def __init__(self, program):
        self.program = program
        self.isBinary = False
        self.parser = app.parser.Parser(program.prefs)
        self.parserTime = 0.0
        self.message = (u"New buffer", None)
        self.setFileType("words")

    def setFileType(self, fileType):
        self.fileType = fileType
        self.rootGrammar = self.program.prefs.getGrammar(self.fileType)
        # Parse from the beginning.
        self.parser.resumeAtRow = 0

    def escapeBinaryChars(self, data):
        if app.config.strict_debug:
            assert isinstance(data, unicode)
        # Performance: in a 1000 line test it appears fastest to do some simple
        # .replace() calls to minimize the number of calls to parse().
        data = data.replace(u'\r\n', u'\n')
        data = data.replace(u'\r', u'\n')
        if self.program.prefs.tabsToSpaces(self.fileType):
            tabSize = self.program.prefs.editor.get(u"tabSize", 8)
            data = data.expandtabs(tabSize)

        def parse(sre):
            return u"\x01%02x" % ord(sre.groups()[0])

        #data = re.sub(u'([\0-\x09\x0b-\x1f\x7f-\xff])', parse, data)
        data = re.sub(u'([\0-\x09\x0b-\x1f])', parse, data)
        return data

    def unescapeBinaryChars(self, data):

        def encode(line):
            return chr(int(line.groups()[0], 16))

        out = re.sub(u'\x01([0-9a-fA-F][0-9a-fA-F])', encode, data)
        if app.config.strict_debug:
            assert isinstance(out, unicode)
        return out

    def doParse(self, begin, end):
        start = time.time()
        self.parser.parse(self.program.bg, self.parser.data,
                          self.rootGrammar, begin, end)
        self.debugUpperChangedRow = self.parser.resumeAtRow
        self.parserTime = time.time() - start

    def isEmpty(self):
        return len(self.parser.data) == 0

    def parseDocument(self):
        self.doParse(self.parser.resumeAtRow, sys.maxsize)

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
