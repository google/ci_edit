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

import os
import re
import text_buffer

import app.buffer_manager
import app.config
import app.controller
#import app.window


def parseInt(inStr):
  if app.config.strict_debug:
    assert type(inStr) is unicode, type(inStr)
  i = 0
  k = 0
  if len(inStr) > i and inStr[i] in ('+', '-'):
    i += 1
  k = i
  while len(inStr) > k and inStr[k].isdigit():
    k += 1
  if k > i:
    return int(inStr[:k])
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


class InteractivePrediction(app.controller.Controller):
  """Make a guess about what the user desires."""
  def __init__(self, view):
    if app.config.strict_debug:
      assert issubclass(self.__class__, InteractivePrediction), self
      assert issubclass(view.__class__, app.window.ViewWindow), view
    app.controller.Controller.__init__(self, view, 'prediction')

  def cancel(self):
    self.items = [(self.priorTextBuffer, self.priorTextBuffer.fullPath, '')]
    self.index = 0
    self.changeToHostWindow()

  def cursorMoveTo(self, row, col):
    if app.config.strict_debug:
      assert type(row) is int
      assert type(col) is int
    textBuffer = self.view.host.textBuffer
    textBuffer.cursorMoveTo(row, col)
    textBuffer.cursorScrollToMiddle()
    textBuffer.redo()

  def focus(self):
    app.log.info('InteractivePrediction.focus')
    self.priorTextBuffer = self.view.host.textBuffer
    self.index = self.buildFileList(self.view.host.textBuffer.fullPath)
    self.view.host.setTextBuffer(text_buffer.TextBuffer())
    self.commandDefault = self.view.textBuffer.insertPrintable
    self.view.host.textBuffer.lineLimitIndicator = 0
    self.view.host.textBuffer.rootGrammar = app.prefs.getGrammar('_pre')

  def info(self):
    app.log.info('InteractivePrediction command set')

  def buildFileList(self, currentFile):
    if app.config.strict_debug:
      assert type(currentFile) is str
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
    try:
      contents = os.listdir(
          os.path.expandvars(os.path.expanduser(dirPath)) or '.')
    except OSError:
      contents = []
    contents.sort()
    for i in contents:
      f, e = os.path.splitext(i)
      if file == f and ext != e and e not in ignoreExt:
        self.items.append((None, os.path.join(dirPath, i), '='))
    if 1:
      app.log.info()
      # Chromium specific hack.
      if currentFile.endswith('-extracted.js'):
        chromiumPath = currentFile[:-len('-extracted.js')] + '.html'
        app.log.info(chromiumPath)
        if os.path.isfile(chromiumPath):
          app.log.info()
          self.items.append((None, chromiumPath, '='))
      elif currentFile.endswith('.html'):
        app.log.info()
        chromiumPath = currentFile[:-len('.html')] + '-extracted.js'
        if os.path.isfile(chromiumPath):
          app.log.info()
          self.items.append((None, chromiumPath, '='))
    # Suggest item.
    return (len(app.buffer_manager.buffers.buffers) - 2) % len(self.items)

  def onChange(self):
    clip = []
    limit = max(5, self.view.host.cols-10)
    for i,item in enumerate(self.items):
      prefix = '-->' if i == self.index else '   '
      suffix = ' <--' if i == self.index else ''
      clip.append("%s %s %s%s"%(prefix, item[1][-limit:], item[2], suffix))
    self.view.host.textBuffer.selectionAll()
    self.view.host.textBuffer.editPasteLines(tuple(clip))
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
      self.view.host.setTextBuffer(
          app.buffer_manager.buffers.getValidTextBuffer(textBuffer))
    else:
      expandedPath = os.path.abspath(os.path.expanduser(fullPath))
      textBuffer = app.buffer_manager.buffers.loadTextBuffer(expandedPath,
          self.view.host)
      self.view.host.setTextBuffer(textBuffer)
    self.items = None


class InteractiveFind(app.controller.Controller):
  """Find text within the current document."""
  def __init__(self, view):
    if app.config.strict_debug:
      assert issubclass(self.__class__, InteractiveFind), self
      assert issubclass(view.__class__, app.window.ViewWindow), view
    app.controller.Controller.__init__(self, view, 'find')

  def findNext(self):
    self.findCmd = self.view.host.textBuffer.findNext

  def findPrior(self):
    self.findCmd = self.view.host.textBuffer.findPrior

  def focus(self):
    self.findCmd = self.view.host.textBuffer.find
    selection = self.view.host.textBuffer.getSelectedText()
    if selection:
      self.view.findLine.textBuffer.selectionAll()
      # Make a single regex line.
      selection = "\\n".join(selection)
      app.log.info(selection)
      self.view.findLine.textBuffer.insert(re.escape(selection))
    self.view.findLine.textBuffer.selectionAll()

  def onChange(self):
    searchFor = self.view.findLine.textBuffer.lines[0]
    try:
      self.findCmd(searchFor)
    except re.error, e:
      self.error = e.message
    self.findCmd = self.view.host.textBuffer.find

  def replaceAndNext(self):
    replaceWith = self.view.replaceLine.textBuffer.lines[0]
    self.view.host.textBuffer.editPasteData(replaceWith)
    self.findCmd = self.view.host.textBuffer.findNext

  def replaceAndPrior(self):
    replaceWith = self.view.replaceLine.textBuffer.lines[0]
    self.view.host.textBuffer.editPasteData(replaceWith)
    self.findCmd = self.view.host.textBuffer.findPrior


class InteractiveFindInput(app.controller.Controller):
  """Find text within the current document."""
  def __init__(self, view):
    if app.config.strict_debug:
      assert issubclass(self.__class__, InteractiveFindInput), self
      assert issubclass(view.__class__, app.window.ViewWindow), view
    app.controller.Controller.__init__(self, view, 'find')

  def nextFocusableWindow(self):
    self.view.parent.expandFindWindow(True)
    app.controller.Controller.nextFocusableWindow(self)

  def priorFocusableWindow(self):
    if not app.controller.Controller.priorFocusableWindow(self):
      self.view.host.expandFindWindow(False)

  def findNext(self):
    self.parentController().findNext()

  def findPrior(self):
    self.parentController().findPrior()

  def info(self):
    app.log.info('InteractiveFind command set')

  def onChange(self):
    self.parentController().onChange()

  def replaceAndNext(self):
    self.parentController().replaceAndNext()

  def replaceAndPrior(self):
    self.parentController().replaceAndPrior()


class InteractiveGoto(app.controller.Controller):
  """Jump to a particular line number."""
  def __init__(self, view):
    if app.config.strict_debug:
      assert issubclass(self.__class__, InteractiveGoto), self
      assert issubclass(view.__class__, app.window.ViewWindow), view
    app.controller.Controller.__init__(self, view, 'goto')

  def focus(self):
    app.log.info('InteractiveGoto.focus')
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(self.view.host.textBuffer.penRow + 1))
    self.textBuffer.selectionAll()

  def info(self):
    app.log.info('InteractiveGoto command set')

  def gotoBottom(self):
    app.log.info()
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(len(self.view.host.textBuffer.lines)))
    self.changeToHostWindow()

  def gotoHalfway(self):
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(len(self.view.host.textBuffer.lines) / 2 + 1))
    self.changeToHostWindow()

  def gotoTop(self):
    self.textBuffer.selectionAll()
    self.textBuffer.insert("0")
    self.changeToHostWindow()

  def cursorMoveTo(self, row, col):
    if app.config.strict_debug:
      assert type(row) is int
      assert type(col) is int
    textBuffer = self.view.host.textBuffer
    textBuffer.cursorMoveTo(row, col)
    textBuffer.cursorScrollToMiddle()
    textBuffer.redo()

  def onChange(self):
    app.log.info()
    line = U''
    try: line = self.textBuffer.lines[0]
    except: pass
    gotoLine, gotoCol = (line.split(U',') + [U'0', U'0'])[:2]
    self.cursorMoveTo(parseInt(gotoLine)-1, parseInt(gotoCol))


class ToggleController(app.controller.Controller):
  def __init__(self, view):
    if app.config.strict_debug:
      assert issubclass(self.__class__, ToggleController), self
      assert issubclass(view.__class__, app.window.ViewWindow), view
    app.controller.Controller.__init__(self, view, 'toggle')

  def toggleValue(self):
    category = self.view.prefCategory
    name = self.view.prefName
    prefs = app.prefs
    prefs.save(category, name, not prefs.prefs[category][name])


