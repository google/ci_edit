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

"""Interactive UIs for the ciEditor."""

import app.buffer_manager
import app.controller
import os
import re
import text_buffer


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
  assert parseInt('text') == 0
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

  def createOrOpen(self):
    self.changeToHostWindow()

  def focus(self):
    app.log.info('InteractiveOpener.focus\n',
        self.host.textBuffer.fullPath)
    self.priorTextBuffer = self.host.textBuffer
    self.commandDefault = self.textBuffer.insertPrintable
    self.textBuffer.selectionAll()
    self.textBuffer.editPasteLines((self.host.textBuffer.fullPath,))
    # Create a new text buffer to display dir listing.
    self.host.setTextBuffer(text_buffer.TextBuffer())

  def info(self):
    app.log.info('InteractiveOpener command set')

  def maybeSlash(self, expandedPath):
    if (self.textBuffer.lines[0] and self.textBuffer.lines[0][-1] != '/' and
        os.path.isdir(expandedPath)):
      self.textBuffer.insert('/')

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
    if len(input) > 0 and input[-1] != os.sep:
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
    self.host.textBuffer.findPlainText(fileName)

  def unfocus(self):
    expandedPath = os.path.abspath(os.path.expanduser(self.textBuffer.lines[0]))
    if os.path.isdir(expandedPath):
      app.log.info('dir\n\n', expandedPath)
      self.host.setTextBuffer(
          app.buffer_manager.buffers.getValidTextBuffer(self.priorTextBuffer))
    else:
      app.log.info('non-dir\n\n', expandedPath)
      app.log.info('non-dir\n\n',
          app.buffer_manager.buffers.loadTextBuffer(expandedPath).lines[0])
      self.host.setTextBuffer(
          app.buffer_manager.buffers.loadTextBuffer(expandedPath))


class InteractivePrediction(app.controller.Controller):
  """Make a guess about what the user desires."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, 'opener')
    self.textBuffer = textBuffer

  def cancel(self):
    self.items = [(self.priorTextBuffer, '')]
    self.index = 0
    self.changeToHostWindow()

  def cursorMoveTo(self, row, col):
    textBuffer = self.document.textBuffer
    textBuffer.cursorMoveTo(row, col)
    textBuffer.cursorScrollToMiddle()
    textBuffer.redo()

  def focus(self):
    app.log.info('InteractivePrediction.focus')
    self.priorTextBuffer = self.host.textBuffer
    self.index = self.buildFileList(self.host.textBuffer.fullPath)
    self.host.setTextBuffer(text_buffer.TextBuffer())
    self.commandDefault = self.host.textBuffer.insertPrintable
    self.host.textBuffer.lineLimitIndicator = 0
    self.host.textBuffer.rootGrammar = app.prefs.getGrammar('_pre')

  def info(self):
    app.log.info('InteractivePrediction command set')

  def buildFileList(self, currentFile):
    self.items = []
    for i in app.buffer_manager.buffers.buffers:
      dirty = '*' if i.isDirty() else '.'
      if i.fullPath:
        self.items.append((i, i.fullPath, dirty))
      else:
        self.items.append((i, '<new file> %s'%(i.lines[0][:20]), dirty))
    dirPath, fileName = os.path.split(currentFile)
    file, ext = os.path.splitext(fileName)
    # TODO(dschuyler): rework this ignore list.
    ignoreExt = set(('.pyc', '.pyo', '.o', '.obj', '.tgz', '.zip', '.tar',))
    for i in os.listdir(os.path.expandvars(os.path.expanduser(dirPath)) or '.'):
      f, e = os.path.splitext(i)
      if file == f and ext != e and e not in ignoreExt:
        self.items.append((None, os.path.join(dirPath, i), '='))
    # Suggest item.
    return (len(app.buffer_manager.buffers.buffers) - 2) % len(self.items)

  def onChange(self):
    input = self.textBuffer.lines[0]
    clip = []
    limit = max(5, self.host.cols-10)
    for i,item in enumerate(self.items):
      prefix = '-->' if i == self.index else '   '
      suffix = ' <--' if i == self.index else ''
      clip.append("%s %s %s%s"%(prefix, item[1][-limit:], item[2], suffix))
    app.log.info(clip)
    self.host.textBuffer.selectionAll()
    self.host.textBuffer.editPasteLines(tuple(clip))
    self.cursorMoveTo(self.index, 0)

  def nextItem(self):
    self.index = (self.index + 1) % len(self.items)

  def priorItem(self):
    self.index = (self.index - 1) % len(self.items)

  def selectItem(self):
    self.changeToHostWindow()

  def unfocus(self):
    textBuffer, fullPath = self.items[self.index][:2]
    if textBuffer is not None:
      self.host.setTextBuffer(
          app.buffer_manager.buffers.getValidTextBuffer(textBuffer))
    else:
      expandedPath = os.path.abspath(os.path.expanduser(fullPath))
      self.host.setTextBuffer(
          app.buffer_manager.buffers.loadTextBuffer(expandedPath))
    self.items = None


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
      self.textBuffer.insert(re.escape(selection))
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
    self.textBuffer.insert(str(len(self.document.textBuffer.lines) / 2 + 1))
    self.changeToHostWindow()

  def gotoTop(self):
    app.log.info(self.document)
    self.textBuffer.selectionAll()
    self.textBuffer.insert("0")
    self.changeToHostWindow()

  def cursorMoveTo(self, row, col):
    textBuffer = self.document.textBuffer
    textBuffer.cursorMoveTo(row, col)
    textBuffer.cursorScrollToMiddle()
    textBuffer.redo()

  def onChange(self):
    app.log.info()
    line = ''
    try: line = self.textBuffer.lines[0]
    except: pass
    gotoLine, gotoCol = (line.split(',') + ['0', '0'])[:2]
    self.cursorMoveTo(parseInt(gotoLine)-1, parseInt(gotoCol))
