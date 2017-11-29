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

import app.controller
import os
import re
import subprocess


def functionTestEq(a, b):
  assert a == b, "%r != %r"%(a, b)

if 1:
  # Break up a command line, separate by |.
  kRePipeChain = re.compile(
      #r'''\|\|?|&&|((?:"(?:\\"|[^"])*"|'(?:\\'|[^'])*'|[^\s|&]+)+)''')
      r'''((?:"(?:\\"|[^"])*"|'(?:\\'|[^'])*'|\|\||[^|]+)+)''')
  functionTestEq(kRePipeChain.findall(''' date "a b" 'c d ' | sort '''),
      [""" date "a b" 'c d ' """, ' sort '])
  functionTestEq(kRePipeChain.findall('date'),
      ['date'])
  functionTestEq(kRePipeChain.findall('d-a.te'),
      ['d-a.te'])
  functionTestEq(kRePipeChain.findall('date | wc'),
      ['date ', ' wc'])
  functionTestEq(kRePipeChain.findall('date|wc'),
      ['date', 'wc'])
  functionTestEq(kRePipeChain.findall('date && sort'),
      ['date && sort'])
  functionTestEq(kRePipeChain.findall('date || sort'),
      ['date || sort'])
  functionTestEq(kRePipeChain.findall('''date "a b" 'c d ' || sort'''),
      ["""date "a b" 'c d ' || sort"""])


# Break up a command line, separate by &&.
kReLogicChain = re.compile(
    r'''\s*(\|\|?|&&|"(?:\\"|[^"])*"|'(?:\\'|[^'])*'|[^\s|&]+)''')
functionTestEq(kReLogicChain.findall('date'),
    ['date'])
functionTestEq(kReLogicChain.findall('d-a.te'),
    ['d-a.te'])
functionTestEq(kReLogicChain.findall('date | wc'),
    ['date', '|', 'wc'])
functionTestEq(kReLogicChain.findall('date|wc'),
    ['date', '|', 'wc'])
functionTestEq(kReLogicChain.findall('date && sort'),
    ['date', '&&', 'sort'])
functionTestEq(kReLogicChain.findall('date || sort'),
    ['date', '||', 'sort'])
functionTestEq(kReLogicChain.findall(''' date "a\\" b" 'c d ' || sort '''),
    ['date', '"a\\" b"', "'c d '", '||', 'sort'])


# Break up a command line, separate by \\s.
kReArgChain = re.compile(
    r'''\s*("(?:\\"|[^"])*"|'(?:\\'|[^'])*'|[^\s]+)''')
functionTestEq(kReArgChain.findall('date'),
    ['date'])
functionTestEq(kReArgChain.findall('d-a.te'),
    ['d-a.te'])
functionTestEq(kReArgChain.findall(
    ''' date "a b" 'c d ' "a\\" b" 'c\\' d ' '''),
    ['date', '"a b"', "'c d '", '"a\\" b"', "'c\\' d '"])
functionTestEq(kReArgChain.findall(
    '''bm +'''),
    ['bm', '+'])


# Break up a command line, separate by \w (non-word chars will be separated).
kReSplitCmdLine = re.compile(
    r"""\s*("(?:\\"|[^"])*"|'(?:\\'|[^'])*'|\w+|[^\s]+)\s*""")
functionTestEq(kReSplitCmdLine.findall(
    '''bm ab'''),
    ['bm', 'ab'])
functionTestEq(kReSplitCmdLine.findall(
    '''bm+'''),
    ['bm', '+'])
functionTestEq(kReSplitCmdLine.findall(
    '''bm "one two"'''),
    ['bm', '"one two"'])
functionTestEq(kReSplitCmdLine.findall(
    '''bm "o\\"ne two"'''),
    ['bm', '"o\\"ne two"'])


# Unquote text.
kReUnquote = re.compile(r'''(["'])([^\1]*)\1''')
functionTestEq(kReUnquote.sub('\\2', 'date'),
    'date')
functionTestEq(kReUnquote.sub('\\2', '"date"'),
    'date')
functionTestEq(kReUnquote.sub('\\2', "'date'"),
    'date')
functionTestEq(kReUnquote.sub('\\2', "'da\\'te'"),
    "da\\'te")
functionTestEq(kReUnquote.sub('\\2', '"da\\"te"'),
    'da\\"te')


class InteractivePrompt(app.controller.Controller):
  """Extended commands prompt."""
  def __init__(self, host):
    app.controller.Controller.__init__(self, host, 'prompt')

  def setTextBuffer(self, textBuffer):
    app.controller.Controller.setTextBuffer(self, textBuffer)
    self.textBuffer = textBuffer
    self.textBuffer.lines = [unicode("")]
    self.commands = {
      'bm': self.bookmarkCommand,
      'build': self.buildCommand,
      'cua': self.changeToCuaMode,
      'emacs': self.changeToEmacsMode,
      'make': self.makeCommand,
      #'split': self.splitCommand,  # Experimental wip.
      'vim': self.changeToVimNormalMode,
    }
    self.filters = {
      'format': self.formatCommand,
      'lower': self.lowerSelectedLines,
      'numEnum': self.assignIndexToSelectedLines,
      's' : self.substituteText,
      'sort': self.sortSelectedLines,
      'sub' : self.substituteText,
      'upper': self.upperSelectedLines,
    }
    self.subExecute = {
      '!': self.shellExecute,
      '|': self.pipeExecute,
    }

  def bookmarkCommand(self, cmdLine, view):
    args = kReSplitCmdLine.findall(cmdLine)
    if len(args) > 1 and args[1][0] == '-':
      if self.host.textBuffer.bookmarkRemove():
        return {}, 'Removed bookmark'
      else:
        return {}, 'No bookmarks to remove'
    else:
      self.host.textBuffer.bookmarkAdd()
      return {}, 'Added bookmark'

  def buildCommand(self, cmdLine, view):
    return {}, 'building things'

  def changeToCuaMode(self, cmdLine, view):
    return {}, 'CUA mode'

  def changeToEmacsMode(self, cmdLine, view):
    return {}, 'Emacs mode'

  def changeToVimNormalMode(self, cmdLine, view):
    return {}, 'Vim normal mode'

  def focus(self):
    app.log.info('InteractivePrompt.focus')
    self.textBuffer.selectionAll()

  def formatCommand(self, cmdLine, lines):
    formatter = {
      #".js": app.format_javascript.format
      #".py": app.format_python.format
      #".html": app.format_html.format,
    }
    def noOp(data):
      return data
    file, ext = os.path.splitext(self.host.textBuffer.fullPath)
    app.log.info(file, ext)
    lines = self.host.textBuffer.doDataToLines(
        formatter.get(ext, noOp)(self.host.textBuffer.doLinesToData(lines)))
    return lines, 'Changed %d lines'%(len(lines),)

  def makeCommand(self, cmdLine, view):
    return {}, 'making stuff'

  def splitCommand(self, cmdLine, view):
    view.splitWindow()
    return {}, 'Split window'

  def execute(self):
    try:
      cmdLine = ''
      try: cmdLine = self.textBuffer.lines[0]
      except: pass
      if not len(cmdLine):
        self.changeToHostWindow()
        return
      tb = self.host.textBuffer
      lines = list(tb.getSelectedText())
      if cmdLine[0] in self.subExecute:
        data = self.host.textBuffer.doLinesToData(lines)
        output, message = self.subExecute.get(cmdLine[0])(
            cmdLine[1:], data)
        output = tb.doDataToLines(output)
        tb.editPasteLines(tuple(output))
        tb.setMessage(message)
      else:
        cmd = re.split('\\W', cmdLine)[0]
        filter = self.filters.get(cmd)
        if filter:
          if not len(lines):
            tb.setMessage('The %s filter needs a selection.'%(cmd,))
          else:
            lines, message = filter(cmdLine, lines)
            tb.setMessage(message)
            if not len(lines):
              lines.append('')
            tb.editPasteLines(tuple(lines))
        else:
          command = self.commands.get(cmd, self.unknownCommand)
          message = command(cmdLine, self.host)[1]
          tb.setMessage(message)
    except Exception as e:
      app.log.exception(e)
      tb.setMessage('Execution threw an error.')
    self.changeToHostWindow()

  def shellExecute(self, commands, input):
    try:
      process = subprocess.Popen(commands,
          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT, shell=True);
      return process.communicate(input)[0], ''
    except Exception as e:
      return '', 'Error running shell command\n' + e

  def pipeExecute(self, commands, input):
    chain = kRePipeChain.findall(commands)
    app.log.info('chain', chain)
    try:
      app.log.info(kReArgChain.findall(chain[-1]))
      process = subprocess.Popen(kReArgChain.findall(chain[-1]),
          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT);
      if len(chain) == 1:
        return process.communicate(input)[0], ''
      else:
        chain.reverse()
        prior = process
        for i in chain[1:]:
          app.log.info(kReArgChain.findall(i))
          prior = subprocess.Popen(kReArgChain.findall(i),
              stdin=subprocess.PIPE, stdout=prior.stdin,
              stderr=subprocess.STDOUT);
        prior.communicate(input)
        return process.communicate()[0], ''
    except Exception as e:
      return '', 'Error running shell command\n' + e

  def info(self):
    app.log.info('InteractivePrompt command set')

  def lowerSelectedLines(self, cmdLine, lines):
    lines = [line.lower() for line in lines]
    return lines, 'Changed %d lines'%(len(lines),)

  def assignIndexToSelectedLines(self, cmdLine, lines):
    output = []
    for i, line in enumerate(lines):
      output.append("%s = %d" % (line, i))
    return output, 'Changed %d lines'%(len(output),)

  def sortSelectedLines(self, cmdLine, lines):
    lines.sort()
    return lines, 'Changed %d lines'%(len(lines),)

  def substituteText(self, cmdLine, lines):
    if len(cmdLine) < 2:
      return lines, '''tip: %s/foo/bar/ to replace 'foo' with 'bar'.''' % (
          cmdLine,)
    if not lines:
      return lines, 'No text was selected.'
    sre = re.match('\w+(\W)', cmdLine)
    if not sre:
      return lines, '''Separator punctuation missing, example:''' \
          ''' %s/foo/bar/''' % (cmdLine,)
    separator = sre.groups()[0]
    try:
      _, find, replace, flags = cmdLine.split(separator, 3)
    except:
      return lines, '''Separator punctuation missing, there should be''' \
          ''' three '%s'.''' % (separator,)
    data = self.host.textBuffer.doLinesToData(lines)
    output = self.host.textBuffer.findReplaceText(find, replace, flags, data)
    lines = self.host.textBuffer.doDataToLines(output)
    return lines, 'Changed %d lines'%(len(lines),)

  def upperSelectedLines(self, cmdLine, lines):
    lines = [line.upper() for line in lines]
    return lines, 'Changed %d lines'%(len(lines),)

  def unknownCommand(self, cmdLine, view):
    self.host.textBuffer.setMessage('Unknown command')
    return {}, 'Unknown command %s' % (cmdLine,)
