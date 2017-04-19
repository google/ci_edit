# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

"""Key bindings for the ciEditor."""

from app.curses_util import *
import app.buffer_manager
import app.controller
import curses
import curses.ascii
import os
import re
import subprocess
import text_buffer


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


def parseInt(str):
  i = 0
  k = 0
  if len(str) > i and str[i] in ('+', '-'):
    i += 1
  k = i
  while len(str) > k and str[k].isdigit():
    k += 1
  if k > i:
    return int(str[:k])
  return 0

def test_parseInt():
  assert parseInt('0') == 0
  assert parseInt('0e') == 0
  assert parseInt('qwee') == 0
  assert parseInt('10') == 10
  assert parseInt('+10') == 10
  assert parseInt('-10') == -10
  assert parseInt('--10') == 0
  assert parseInt('--10') == 0


class InteractiveOpener(app.controller.Controller):
  """Open a file to edit."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'opener')
    self.textBuffer = textBuffer
    self.textBuffer.lines = [""]

  def focus(self):
    app.log.info('InteractiveOpener.focus')
    self.priorPath = self.host.textBuffer.fullPath
    self.commandDefault = self.textBuffer.insertPrintable
    self.textBuffer.selectionAll()
    self.textBuffer.editPasteLines(
        (self.suggestFile(self.host.textBuffer.fullPath),))
    # Create a new text buffer to display dir listing.
    self.host.setTextBuffer(text_buffer.TextBuffer())

  def info(self):
    app.log.info('InteractiveOpener command set')

  def createOrOpen(self):
    if 0:
      expandedPath = os.path.abspath(os.path.expanduser(self.textBuffer.lines[0]))
      app.log.info('createOrOpen\n\n', expandedPath)
      if not os.path.isdir(expandedPath):
        self.host.setTextBuffer(
            app.buffer_manager.buffers.loadTextBuffer(expandedPath))
    self.changeToHostWindow()

  def maybeSlash(self, expandedPath):
    if (self.textBuffer.lines[0] and self.textBuffer.lines[0][-1] != '/' and
        os.path.isdir(expandedPath)):
      self.textBuffer.insert('/')

  def suggestFile(self, currentFile):
    dirPath, fileName = os.path.split(currentFile)
    suggestion = ''
    file, ext = os.path.splitext(fileName)
    for i in os.listdir(os.path.expandvars(os.path.expanduser(dirPath)) or '.'):
      f, e = os.path.splitext(i)
      if file == f and ext != e and e not in ('.pyc', '.pyo', '.o', '.obj',):
        return os.path.join(dirPath, i)
    tb = app.buffer_manager.buffers.recentBuffer()
    if tb:
      return tb.fullPath
    return ''

  def tabCompleteFirst(self):
    """Find the first file that starts with the pattern."""
    dirPath, fileName = os.path.split(self.lines[0])
    foundOnce = ''
    app.log.debug('tabComplete\n', dirPath, '\n', fileName)
    for i in os.listdir(os.path.expandvars(os.path.expanduser(dirPath)) or '.'):
      if i.startswith(fileName):
        if foundOnce:
          # Found more than one match.
          return
        fileName = os.path.join(dirPath, i)
        if os.path.isdir(fileName):
          fileName += '/'
        self.lines[0] = fileName
        self.onChange()
        return

  def tabCompleteExtend(self):
    """Extend the selection to match characters in common."""
    dirPath, fileName = os.path.split(self.textBuffer.lines[0])
    expandedDir = os.path.expandvars(os.path.expanduser(dirPath)) or '.'
    matches = []
    if not os.path.isdir(expandedDir):
      return
    for i in os.listdir(expandedDir):
      if i.startswith(fileName):
        matches.append(i)
      else:
        pass
        #app.log.info('not', i)
    if len(matches) <= 0:
      self.maybeSlash(expandedDir)
      self.onChange()
      return
    if len(matches) == 1:
      self.textBuffer.insert(matches[0][len(fileName):])
      self.maybeSlash(os.path.join(expandedDir, matches[0]))
      self.onChange()
      return
    def findCommonPrefixLength(prefixLen):
      count = 0
      ch = None
      for match in matches:
        if len(match) <= prefixLen:
          return prefixLen
        if not ch:
          ch = match[prefixLen]
        if match[prefixLen] == ch:
          count += 1
      if count and count == len(matches):
        return findCommonPrefixLength(prefixLen + 1)
      return prefixLen
    prefixLen = findCommonPrefixLength(len(fileName))
    self.textBuffer.insert(matches[0][len(fileName):prefixLen])
    self.onChange()

  def setFileName(self, path):
    self.textBuffer.lines = [path]
    self.textBuffer.cursorCol = len(path)
    self.textBuffer.goalCol = self.textBuffer.cursorCol

  def oldAutoOpenOnChange(self):
    path = os.path.expanduser(os.path.expandvars(self.textBuffer.lines[0]))
    dirPath, fileName = os.path.split(path)
    dirPath = dirPath or '.'
    app.log.info('O.onChange', dirPath, fileName)
    if os.path.isdir(dirPath):
      lines = []
      for i in os.listdir(dirPath):
        if i.startswith(fileName):
          lines.append(i)
      if len(lines) == 1 and os.path.isfile(os.path.join(dirPath, fileName)):
        self.host.setTextBuffer(app.buffer_manager.buffers.loadTextBuffer(
            os.path.join(dirPath, fileName)))
      else:
        self.host.textBuffer.lines = [
            os.path.abspath(os.path.expanduser(dirPath))+":"] + lines
    else:
      self.host.textBuffer.lines = [
          os.path.abspath(os.path.expanduser(dirPath))+": not found"]

  def onChange(self):
    input = self.textBuffer.lines[0]
    path = os.path.abspath(os.path.expanduser(os.path.expandvars(input)))
    dirPath = path or '.'
    fileName = ''
    if len(input) == 0 or input[-1] != os.sep:
      dirPath, fileName = os.path.split(path)
    app.log.info('\n\nO.onChange\n', path, '\n', dirPath, fileName)
    if os.path.isdir(dirPath):
      lines = []
      for i in os.listdir(dirPath):
        if os.path.isdir(i):
          i += '/'
        lines.append(i)
      clip = [dirPath+":"] + lines
    else:
      clip = [dirPath+": not found"]
    app.log.info(clip)
    self.host.textBuffer.selectionAll()
    self.host.textBuffer.editPasteLines(tuple(clip))

  def unfocus(self):
    expandedPath = os.path.abspath(os.path.expanduser(self.textBuffer.lines[0]))
    if os.path.isdir(expandedPath):
      app.log.info('dir\n\n', expandedPath)
      self.host.setTextBuffer(
          app.buffer_manager.buffers.loadTextBuffer(self.priorPath))
    else:
      app.log.info('non-dir\n\n', expandedPath)
      app.log.info('non-dir\n\n',
          app.buffer_manager.buffers.loadTextBuffer(expandedPath).lines[0])
      self.host.setTextBuffer(
          app.buffer_manager.buffers.loadTextBuffer(expandedPath))


class InteractiveFind(app.controller.Controller):
  """Find text within the current document."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'find')
    self.textBuffer = textBuffer
    self.textBuffer.lines = [""]

  def findNext(self):
    self.findCmd = self.document.textBuffer.findNext

  def findPrior(self):
    self.findCmd = self.document.textBuffer.findPrior

  def findReplace(self):
    self.findCmd = self.document.textBuffer.findReplace

  def focus(self):
    app.log.info('InteractiveFind')
    self.findCmd = self.document.textBuffer.find
    selection = self.document.textBuffer.getSelectedText()
    if selection:
      self.textBuffer.selectionAll()
      # Make a single regex line.
      selection = "\\n".join(selection)
      app.log.info(selection)
      self.textBuffer.insert(selection)
    self.textBuffer.selectionAll()

  def info(self):
    app.log.info('InteractiveFind command set')

  def onChange(self):
    app.log.info('InteractiveFind')
    searchFor = self.textBuffer.lines[0]
    try:
      self.findCmd(searchFor)
    except re.error, e:
      self.error = e.message
    self.findCmd = self.document.textBuffer.find


class InteractiveGoto(app.controller.Controller):
  """Jump to a particular line number."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'goto')
    self.textBuffer = textBuffer
    self.textBuffer.lines = [""]

  def focus(self):
    app.log.info('InteractiveGoto.focus')
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(self.document.textBuffer.cursorRow+1))
    self.textBuffer.selectionAll()

  def info(self):
    app.log.info('InteractiveGoto command set')

  def gotoBottom(self):
    app.log.info()
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(len(self.document.textBuffer.lines)))
    self.changeToHostWindow()

  def gotoHalfway(self):
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(len(self.document.textBuffer.lines)/2+1))
    self.changeToHostWindow()

  def gotoTop(self):
    app.log.info(self.document)
    self.textBuffer.selectionAll()
    self.textBuffer.insert("0")
    self.changeToHostWindow()

  def cursorMoveTo(self, row, col):
    textBuffer = self.document.textBuffer
    cursorRow = min(max(row - 1, 0), len(textBuffer.lines)-1)
    #app.log.info('cursorMoveTo row', row, cursorRow)
    textBuffer.cursorMove(cursorRow-textBuffer.cursorRow,
        col-textBuffer.cursorCol,
        col-textBuffer.goalCol)
    textBuffer.redo()
    textBuffer.cursorScrollToMiddle()
    textBuffer.redo()

  def onChange(self):
    app.log.info()
    line = ''
    try: line = self.textBuffer.lines[0]
    except: pass
    gotoLine, gotoCol = (line.split(',') + ['0', '0'])[:2]
    self.cursorMoveTo(parseInt(gotoLine), parseInt(gotoCol))


class InteractivePrompt(app.controller.Controller):
  """Extended commands prompt."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'prompt')
    self.textBuffer = textBuffer
    self.textBuffer.lines = [""]
    self.commands = {
      'build': self.buildCommand,
      'format': self.formatCommand,
      'make': self.makeCommand,
    }
    self.filters = {
      'lower': self.lowerSelectedLines,
      's' : self.substituteText,
      'sort': self.sortSelectedLines,
      'sub' : self.substituteText,
      'upper': self.upperSelectedLines,
    }
    self.subExecute = {
      '!': self.shellExecute,
      '|': self.pipeExecute,
    }

  def buildCommand(self):
    return 'building things'

  def formatCommand(self):
    return 'formatting text'

  def makeCommand(self):
    return 'making stuff'

  def execute(self):
    cmdLine = ''
    try: cmdLine = self.textBuffer.lines[0]
    except: pass
    if not len(cmdLine):
      return
    tb = self.host.textBuffer
    lines = list(tb.getSelectedText())
    command = self.commands.get(cmdLine)
    if command:
      command()
    elif cmdLine[0] in ('!', '|'):
      data = self.host.textBuffer.doLinesToData(lines)
      output = self.subExecute.get(cmdLine[0], self.unknownCommand)(
          cmdLine[1:], data)
      output = tb.doDataToLines(output)
      if tb.selectionMode == app.selectable.kSelectionLine:
        output.append('')
      tb.editPasteLines(tuple(output))
    else:
      cmd = re.split('\\W', cmdLine)[0]
      cmdLine = cmdLine[len(cmd):]
      if not len(lines):
        tb.setMessage('The %s command needs a selection.'%(cmd,))
      lines = self.filters.get(cmd, self.unknownCommand)(cmdLine, lines)
      tb.setMessage('Changed %d lines'%(len(lines),))
      if not len(lines):
        lines.append('')
      if tb.selectionMode == app.selectable.kSelectionLine:
        lines.append('')
      tb.editPasteLines(tuple(lines))
    self.changeToHostWindow()

  def shellExecute(self, commands, input):
    try:
      process = subprocess.Popen(commands,
          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT, shell=True);
      return process.communicate(input)[0]
    except Exception, e:
      self.host.textBuffer.setMessage('Error running shell command\n', e)
      return ''

  def pipeExecute(self, commands, input):
    chain = kRePipeChain.findall(commands)
    app.log.info('chain', chain)
    try:
      app.log.info(kReArgChain.findall(chain[-1]))
      process = subprocess.Popen(kReArgChain.findall(chain[-1]),
          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT);
      if len(chain) == 1:
        return process.communicate(input)[0]
      else:
        chain.reverse()
        prior = process
        for i in chain[1:]:
          app.log.info(kReArgChain.findall(i))
          prior = subprocess.Popen(kReArgChain.findall(i),
              stdin=subprocess.PIPE, stdout=prior.stdin,
              stderr=subprocess.STDOUT);
        prior.communicate(input)
        return process.communicate()[0]
    except Exception, e:
      self.host.textBuffer.setMessage('Error running shell command\n', e)
      return ''

  def info(self):
    app.log.info('InteractivePrompt command set')

  def lowerSelectedLines(self, cmdLine, lines):
    return [line.lower() for line in lines]

  def sortSelectedLines(self, cmdLine, lines):
    lines.sort()
    return lines

  def substituteText(self, cmdLine, lines):
    if len(cmdLine) < 2:
      return
    separator = cmdLine[0]
    a, find, replace, flags = cmdLine.split(separator, 3)
    data = self.host.textBuffer.doLinesToData(lines)
    output = self.host.textBuffer.findReplaceText(find, replace, flags, data)
    return self.host.textBuffer.doDataToLines(output)

  def upperSelectedLines(self, cmdLine, lines):
    return [line.upper() for line in lines]

  def unknownCommand(self, cmdLine, lines):
    self.host.textBuffer.setMessage('Unknown command')
    return lines
