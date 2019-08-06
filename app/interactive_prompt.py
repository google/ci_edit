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
"""Interactive prompt to run advanced commands and sub-processes."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
try:
    unicode
except NameError:
    unicode = str
    unichr = chr

import os
import re
import subprocess

import app.controller


def functionTestEq(a, b):
    assert a == b, u"%r != %r" % (a, b)


if 1:
    # Break up a command line, separate by |.
    kRePipeChain = re.compile(
        #r'''\|\|?|&&|((?:"(?:\\"|[^"])*"|'(?:\\'|[^'])*'|[^\s|&]+)+)''')
        r'''((?:"(?:\\"|[^"])*"|'(?:\\'|[^'])*'|\|\||[^|]+)+)''')
    functionTestEq(
        kRePipeChain.findall(''' date "a b" 'c d ' | sort '''),
        [""" date "a b" 'c d ' """, ' sort '])
    functionTestEq(kRePipeChain.findall('date'), ['date'])
    functionTestEq(kRePipeChain.findall('d-a.te'), ['d-a.te'])
    functionTestEq(kRePipeChain.findall('date | wc'), ['date ', ' wc'])
    functionTestEq(kRePipeChain.findall('date|wc'), ['date', 'wc'])
    functionTestEq(kRePipeChain.findall('date && sort'), ['date && sort'])
    functionTestEq(kRePipeChain.findall('date || sort'), ['date || sort'])
    functionTestEq(
        kRePipeChain.findall('''date "a b" 'c d ' || sort'''),
        ["""date "a b" 'c d ' || sort"""])

# Break up a command line, separate by &&.
kReLogicChain = re.compile(
    r'''\s*(\|\|?|&&|"(?:\\"|[^"])*"|'(?:\\'|[^'])*'|[^\s|&]+)''')
functionTestEq(kReLogicChain.findall('date'), ['date'])
functionTestEq(kReLogicChain.findall('d-a.te'), ['d-a.te'])
functionTestEq(kReLogicChain.findall('date | wc'), ['date', '|', 'wc'])
functionTestEq(kReLogicChain.findall('date|wc'), ['date', '|', 'wc'])
functionTestEq(kReLogicChain.findall('date && sort'), ['date', '&&', 'sort'])
functionTestEq(kReLogicChain.findall('date || sort'), ['date', '||', 'sort'])
functionTestEq(
    kReLogicChain.findall(''' date "a\\" b" 'c d ' || sort '''),
    ['date', '"a\\" b"', "'c d '", '||', 'sort'])

# Break up a command line, separate by \\s.
kReArgChain = re.compile(r'''\s*("(?:\\"|[^"])*"|'(?:\\'|[^'])*'|[^\s]+)''')
functionTestEq(kReArgChain.findall('date'), ['date'])
functionTestEq(kReArgChain.findall('d-a.te'), ['d-a.te'])
functionTestEq(
    kReArgChain.findall(''' date "a b" 'c d ' "a\\" b" 'c\\' d ' '''),
    ['date', '"a b"', "'c d '", '"a\\" b"', "'c\\' d '"])
functionTestEq(kReArgChain.findall('''bm +'''), ['bm', '+'])

# Break up a command line, separate by \w (non-word chars will be separated).
kReSplitCmdLine = re.compile(
    r"""\s*("(?:\\"|[^"])*"|'(?:\\'|[^'])*'|\w+|[^\s]+)\s*""")
functionTestEq(kReSplitCmdLine.findall('''bm ab'''), ['bm', 'ab'])
functionTestEq(kReSplitCmdLine.findall('''bm+'''), ['bm', '+'])
functionTestEq(kReSplitCmdLine.findall('''bm "one two"'''), ['bm', '"one two"'])
functionTestEq(
    kReSplitCmdLine.findall('''bm "o\\"ne two"'''), ['bm', '"o\\"ne two"'])

# Unquote text.
kReUnquote = re.compile(r'''(["'])([^\1]*)\1''')
functionTestEq(kReUnquote.sub('\\2', 'date'), 'date')
functionTestEq(kReUnquote.sub('\\2', '"date"'), 'date')
functionTestEq(kReUnquote.sub('\\2', "'date'"), 'date')
functionTestEq(kReUnquote.sub('\\2', "'da\\'te'"), "da\\'te")
functionTestEq(kReUnquote.sub('\\2', '"da\\"te"'), 'da\\"te')


class InteractivePrompt(app.controller.Controller):
    """Extended commands prompt."""

    def __init__(self, view):
        app.controller.Controller.__init__(self, view, u"prompt")

    def setTextBuffer(self, textBuffer):
        app.controller.Controller.setTextBuffer(self, textBuffer)
        self.textBuffer = textBuffer
        self.textBuffer.lines = [u""]
        self.commands = {
            u'bm': self.bookmarkCommand,
            u'build': self.buildCommand,
            u'cua': self.changeToCuaMode,
            u'emacs': self.changeToEmacsMode,
            u'make': self.makeCommand,
            u'open': self.openCommand,
            #u'split': self.splitCommand,  # Experimental wip.
            u'vim': self.changeToVimNormalMode,
        }
        self.filters = {
            u'format': self.formatCommand,
            u'lower': self.lowerSelectedLines,
            u'numEnum': self.assignIndexToSelectedLines,
            u's': self.substituteText,
            u'sort': self.sortSelectedLines,
            u'sub': self.substituteText,
            u'upper': self.upperSelectedLines,
            u'wrap': self.wrapSelectedLines,
        }
        self.subExecute = {
            u'!': self.shellExecute,
            u'|': self.pipeExecute,
        }

    def bookmarkCommand(self, cmdLine, view):
        args = kReSplitCmdLine.findall(cmdLine)
        if len(args) > 1 and args[1][0] == u'-':
            if self.view.host.textBuffer.bookmarkRemove():
                return {}, u'Removed bookmark'
            else:
                return {}, u'No bookmarks to remove'
        else:
            self.view.host.textBuffer.bookmarkAdd()
            return {}, u'Added bookmark'

    def buildCommand(self, cmdLine, view):
        return {}, u'building things'

    def changeToCuaMode(self, cmdLine, view):
        return {}, u'CUA mode'

    def changeToEmacsMode(self, cmdLine, view):
        return {}, u'Emacs mode'

    def changeToVimNormalMode(self, cmdLine, view):
        return {}, u'Vim normal mode'

    def focus(self):
        app.log.info(u'InteractivePrompt.focus')
        self.textBuffer.selectionAll()

    def formatCommand(self, cmdLine, lines):
        formatter = {
            #".js": app.format_javascript.format
            #".py": app.format_python.format
            #".html": app.format_html.format,
        }

        def noOp(data):
            return data

        fileName, ext = os.path.splitext(self.view.host.textBuffer.fullPath)
        app.log.info(fileName, ext)
        lines = self.view.host.textBuffer.doDataToLines(
            formatter.get(ext,
                          noOp)(self.view.host.textBuffer.doLinesToData(lines)))
        return lines, u'Changed %d lines' % (len(lines),)

    def makeCommand(self, cmdLine, view):
        return {}, u'making stuff'

    def openCommand(self, cmdLine, view):
        """
        Opens the file under cursor.
        """
        args = kReArgChain.findall(cmdLine)
        app.log.info(args)
        if len(args) == 1:
            # If no args are provided, look for a path at the cursor position.
            view.textBuffer.openFileAtCursor()
            return {}, view.textBuffer.message[0]
        # Try the raw path.
        path = args[1]
        if os.access(path, os.R_OK):
            return self.openFile(path, view)
        # Look in the same directory as the current file.
        path = os.path.join(os.path.dirname(view.textBuffer.fullPath), args[1])
        if os.access(path, os.R_OK):
            return self.openFile(path, view)
        return {}, u"Unable to open " + args[1]

    def openFile(self, path, view):
        textBuffer = view.program.bufferManager.loadTextBuffer(path)
        inputWindow = self.currentInputWindow()
        inputWindow.setTextBuffer(textBuffer)
        self.changeTo(inputWindow)
        inputWindow.setMessage('Opened file {}'.format(path))

    def splitCommand(self, cmdLine, view):
        view.splitWindow()
        return {}, u'Split window'

    def execute(self):
        try:
            inputLines = self.textBuffer.lines
            if not len(inputLines) or not len(inputLines[0]):
                self.changeToHostWindow()
                return
            cmdLine = inputLines[0]
            tb = self.view.host.textBuffer
            lines = list(tb.getSelectedText())
            if cmdLine[0] in self.subExecute:
                data = self.view.host.textBuffer.doLinesToData(lines).encode(
                    'utf-8')
                output, message = self.subExecute.get(cmdLine[0])(cmdLine[1:],
                                                                  data)
                if app.config.strict_debug:
                    assert isinstance(output, bytes)
                    assert isinstance(message, unicode)
                output = tb.doDataToLines(output.decode('utf-8'))
                tb.editPasteLines(tuple(output))
                tb.setMessage(message)
            else:
                cmd = re.split(u'\\W', cmdLine)[0]
                dataFilter = self.filters.get(cmd)
                if dataFilter:
                    if not len(lines):
                        tb.setMessage(
                            u'The %s filter needs a selection.' % (cmd,))
                    else:
                        lines, message = dataFilter(cmdLine, lines)
                        tb.setMessage(message)
                        if not len(lines):
                            lines.append(u'')
                        tb.editPasteLines(tuple(lines))
                else:
                    command = self.commands.get(cmd, self.unknownCommand)
                    message = command(cmdLine, self.view.host)[1]
                    tb.setMessage(message)
        except Exception as e:
            app.log.exception(e)
            tb.setMessage(u'Execution threw an error.')
        self.changeToHostWindow()

    def shellExecute(self, commands, cmdInput):
        """
        cmdInput is in bytes (not unicode).
        return tuple: output as bytes (not unicode), message as unicode.
        """
        if app.config.strict_debug:
            assert isinstance(commands, unicode), type(commands)
            assert isinstance(cmdInput, bytes), type(cmdInput)
        try:
            process = subprocess.Popen(
                commands,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True)
            return process.communicate(cmdInput)[0], u''
        except Exception as e:
            return u'', u'Error running shell command\n' + e

    def pipeExecute(self, commands, cmdInput):
        """
        cmdInput is in bytes (not unicode).
        return tuple: output as bytes (not unicode), message as unicode.
        """
        if app.config.strict_debug:
            assert isinstance(commands, unicode), type(commands)
            assert isinstance(cmdInput, bytes), type(cmdInput)
        chain = kRePipeChain.findall(commands)
        try:
            process = subprocess.Popen(
                kReArgChain.findall(chain[-1]),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            if len(chain) == 1:
                return process.communicate(cmdInput)[0], u''
            else:
                chain.reverse()
                prior = process
                for i in chain[1:]:
                    prior = subprocess.Popen(
                        kReArgChain.findall(i),
                        stdin=subprocess.PIPE,
                        stdout=prior.stdin,
                        stderr=subprocess.STDOUT)
                prior.communicate(cmdInput)
                return process.communicate()[0], u''
        except Exception as e:
            app.log.exception(e)
            return b'', u'Error running shell command\n' + unicode(e)

    def info(self):
        app.log.info(u'InteractivePrompt command set')

    def lowerSelectedLines(self, cmdLine, lines):
        lines = [line.lower() for line in lines]
        return lines, u'Changed %d lines' % (len(lines),)

    def assignIndexToSelectedLines(self, cmdLine, lines):
        output = []
        for i, line in enumerate(lines):
            output.append(u"%s = %d" % (line, i))
        return output, u'Changed %d lines' % (len(output),)

    def sortSelectedLines(self, cmdLine, lines):
        lines.sort()
        return lines, u'Changed %d lines' % (len(lines),)

    def substituteText(self, cmdLine, lines):
        if len(cmdLine) < 2:
            return (lines, u'''tip: %s/foo/bar/ to replace 'foo' with 'bar'.'''
                    % (cmdLine,))
        if not lines:
            return lines, u'No text was selected.'
        sre = re.match('\w+(\W)', cmdLine)
        if not sre:
            return (lines, u'''Separator punctuation missing, example:'''
                    u''' %s/foo/bar/''' % (cmdLine,))
        separator = sre.groups()[0]
        try:
            _, find, replace, flags = cmdLine.split(separator, 3)
        except ValueError:
            return (lines, u'''Separator punctuation missing, there should be'''
                    u''' three '%s'.''' % (separator,))
        data = self.view.host.textBuffer.doLinesToData(lines)
        output = self.view.host.textBuffer.findReplaceText(
            find, replace, flags, data)
        lines = self.view.host.textBuffer.doDataToLines(output)
        return lines, u'Changed %d lines' % (len(lines),)

    def upperSelectedLines(self, cmdLine, lines):
        lines = [line.upper() for line in lines]
        return lines, u'Changed %d lines' % (len(lines),)

    def unknownCommand(self, cmdLine, view):
        self.view.host.textBuffer.setMessage(u'Unknown command')
        return {}, u'Unknown command %s' % (cmdLine,)

    def wrapSelectedLines(self, cmdLine, lines):
        tokens = cmdLine.split()
        app.log.info("tokens", tokens)
        width = 80 if len(tokens) == 1 else int(tokens[1])
        indent = len(lines[0]) - len(lines[0].lstrip())
        width -= indent
        lines = app.curses_util.wrapLines(lines, u" " * indent, width)
        return lines, u'Changed %d lines' % (len(lines),)
