# Copyright 2018 Google Inc.
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

import os
import re
import time

from app.curses_util import *
import app.buffer_file
import app.buffer_manager
import app.controller


class PredictionListController(app.controller.Controller):
  """Gather and prepare file directory information.
  """
  def __init__(self, view):
    assert self is not view
    app.controller.Controller.__init__(self, view, 'PredictionListController')
    self.filter = None
    self.shownList = None

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
    return len(app.buffer_manager.buffers.buffers) % len(self.items)

  def focus(self):
    self.onChange()
    app.controller.Controller.focus(self)

  def info(self):
    app.log.info('PredictionListController command set')

  def onChange(self):
    app.log.info(self.view.textBuffer.penRow)
    savedRow = self.view.textBuffer.penRow
    self.index = self.buildFileList(self.view.host.textBuffer.fullPath)
    app.log.info(self.items)
    self.view.textBuffer.replaceLines(tuple([
        "%*s %.*s" % (16, '', 41, i[1][-41:]) for i in self.items
        ]))
    self.view.textBuffer.penRow = max(savedRow, self.index)
    self.view.textBuffer.penCol = 0
    self.view.scrollRow = 0
    self.view.scrollCol = 0
    self.filter = None






    return
    input = self.view.parent.getPath()
    if self.shownList == input:
      return
    self.shownList = input
    fullPath = app.buffer_file.fullPath(input)
    dirPath = fullPath
    fileName = ''
    if len(input) > 0 and input[-1] != os.sep:
      dirPath, fileName = os.path.split(fullPath)
      self.view.textBuffer.findRe = re.compile('()^' + re.escape(fileName))
    else:
      self.view.textBuffer.findRe = None
    dirPath = dirPath or '.'
    if os.path.isdir(dirPath):
      showDotFiles = app.prefs.editor['predictionShowOpenFiles']
      showSizes = app.prefs.editor['predictionShowAlternateFiles']
      showModified = app.prefs.editor['predictionShowRecentFiles']

      sortByType = app.prefs.editor['predictionSortAscendingByType']
      sortByName = app.prefs.editor['predictionSortAscendingByName']
      sortByStatus = app.prefs.editor['predictionSortAscendingByStatus']

      lines = []
      try:
        fileLines = []
        contents = os.listdir(dirPath)
        for i in contents:
          if not showDotFiles and i[0] == '.':
            continue
          if self.filter is not None and not i.startswith(self.filter):
            continue
          fullPath = os.path.join(dirPath, i)
          if os.path.isdir(fullPath):
            i += os.path.sep
          iSize = None
          iModified = 0
          if showSizes and os.path.isfile(fullPath):
            iSize = os.path.getsize(fullPath)
          if showModified:
            iModified = os.path.getmtime(fullPath)
          fileLines.append([i, iSize, iModified])
        if sortByName is not None:
          # Sort by name.
          fileLines.sort(reverse=not sortByName,
              key=lambda x: x[1])
        elif sortByStatus is not None:
          # Sort by status.
          fileLines.sort(reverse=not sortByStatus,
              key=lambda x: x[2])
        else:
          # Sort by type
          fileLines.sort(reverse=not sortByType,
              key=lambda x: unicode.lower(x[0]))
        lines = ['%-40s  %16s  %24s' % (
            i[0], '%s bytes' % (i[1],) if i[1] is not None else '',
            unicode(time.strftime('%c', time.localtime(i[2]))) if i[2] else '')
            for i in fileLines]
        self.view.contents = [i[0] for i in fileLines]
      except OSError as e:
        lines = ['Error creating list.']
        lines.append(unicode(e))
      clip = lines
    else:
      clip = [dirPath + ": not found"]
    self.view.textBuffer.replaceLines(tuple(clip))
    self.view.textBuffer.penRow = 0
    self.view.textBuffer.penCol = 0
    self.view.scrollRow = 0
    self.view.scrollCol = 0
    self.filter = None

  def openFileOrDir(self, row):
    if self.items is None:
      return
    textBuffer, fullPath = self.items[row][:2]
    self.items = None
    if textBuffer is not None:
      textBuffer = app.buffer_manager.buffers.getValidTextBuffer(textBuffer)
    else:
      expandedPath = os.path.abspath(os.path.expanduser(fullPath))
      textBuffer = app.buffer_manager.buffers.loadTextBuffer(expandedPath)
    inputWindow = self.currentInputWindow()
    inputWindow.setTextBuffer(textBuffer)
    self.changeTo(inputWindow)

  def optionChanged(self, name, value):
    self.shownList = None
    self.onChange()

  def setFilter(self, filter):
    self.filter = filter
    self.shownList = None  # Cause a refresh.


class PredictionController(app.controller.Controller):
  """Create or open files.
  """
  def __init__(self, view):
    app.controller.Controller.__init__(self, view, 'PredictionController')

  def performPrimaryAction(self):
    self.view.pathWindow.controller.performPrimaryAction()

  def info(self):
    app.log.info('PredictionController command set')

  def onChange(self):
    self.view.predictionList.controller.onChange()
    app.controller.Controller.onChange(self)

  def optionChanged(self, name, value):
    self.view.predictionList.controller.shownList = None

  def passEventToPredictionList(self):
    self.view.predictionList.controller.doCommand(self.savedCh, None)


class PredictionInputController(app.controller.Controller):
  """Manipulate query string.
  """
  def __init__(self, view):
    app.controller.Controller.__init__(self, view, 'PredictionInputController')

  def focus(self):
    self.getNamedWindow('predictionList').focus()
    app.controller.Controller.focus(self)

  def info(self):
    app.log.info('PredictionInputController command set')

  def onChange(self):
    self.getNamedWindow('predictionList').controller.onChange()
    app.controller.Controller.onChange(self)

  def optionChanged(self, name, value):
    self.getNamedWindow('predictionList').controller.shownList = None

  def passEventToPredictionList(self):
    self.getNamedWindow('predictionList').controller.doCommand(self.savedCh,
        None)

  def performPrimaryAction(self):
    predictionList = self.getNamedWindow('predictionList')
    row = predictionList.textBuffer.penRow
    predictionList.controller.openFileOrDir(row)
