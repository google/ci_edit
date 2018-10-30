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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
try:
  unicode('')
except:
  unicode = str
  unichr = chr

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
    # |items| is a tuple of: buffer, path, flags, type.
    self.items = None
    self.shownList = None

  def buildFileList(self, currentFile):
    if app.config.strict_debug:
      assert type(currentFile) is unicode, repr(currentFile)

    added = set()
    items = self.items = []
    if 1:
      # Add open buffers.
      for i in app.buffer_manager.buffers.buffers:
        dirty = '*' if i.isDirty() else '.'
        if i.fullPath:
          items.append((i, i.fullPath, dirty, 'open'))
          added.add(i.fullPath)
        else:
          items.append((i, '<new file> %s'%(i.parser.rowText(0)[:20]), dirty,
              'open'))
    if 1:
      # Add recent files.
      for recentFile in app.history.getRecentFiles():
        if recentFile not in added:
          items.append((None, recentFile, '=', 'recent'))
          added.add(recentFile)
    if 1:
      # Add alternate files.
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
          fullPath = os.path.join(dirPath, i)
          if fullPath not in added:
            items.append((None, fullPath, '=', 'alt'))
            added.add(fullPath)
      if 1:
        # Chromium specific hack.
        if currentFile.endswith('-extracted.js'):
          chromiumPath = currentFile[:-len('-extracted.js')] + '.html'
          if os.path.isfile(chromiumPath) and chromiumPath not in added:
            items.append((None, chromiumPath, '=', 'alt'))
            added.add(chromiumPath)
        elif currentFile.endswith('.html'):
          chromiumPath = currentFile[:-len('.html')] + '-extracted.js'
          if os.path.isfile(chromiumPath) and chromiumPath not in added:
            items.append((None, chromiumPath, '=', 'alt'))
            added.add(chromiumPath)
    if self.filter is not None:
      regex = re.compile(self.filter)
      i = 0
      while i < len(items):
        if not regex.search(items[i][1]):
          # Filter the list in-place.
          items.pop(i)
        else:
          i += 1

  def focus(self):
    self.onChange()
    app.controller.Controller.focus(self)

  def info(self):
    app.log.info('PredictionListController command set')

  def onChange(self):
    self.filter = self.view.parent.getPath()
    if self.shownList == self.filter:
      return
    self.shownList = self.filter

    inputWindow = self.currentInputWindow()
    self.buildFileList(inputWindow.textBuffer.fullPath)
    if self.items is not None:
      self.view.update(self.items)
    self.filter = None

  def openAltFile(self):
    for row,item in enumerate(self.items):
      if item[3] == 'alt':
        self.openFileOrDir(row)

  def openFileOrDir(self, row):
    if app.config.strict_debug:
      assert type(row) is int
    if self.items is None or len(self.items) == 0:
      return
    textBuffer, fullPath = self.items[row][:2]
    self.items = None
    self.shownList = None
    if textBuffer is not None:
      textBuffer = app.buffer_manager.buffers.getValidTextBuffer(textBuffer)
    else:
      expandedPath = os.path.abspath(os.path.expanduser(fullPath))
      textBuffer = app.buffer_manager.buffers.loadTextBuffer(expandedPath)
    inputWindow = self.currentInputWindow()
    inputWindow.setTextBuffer(textBuffer)
    self.changeTo(inputWindow)

  def optionChanged(self, name, value):
    if app.config.strict_debug:
      assert type(name) is str
      assert type(value) is str
    self.shownList = None
    self.onChange()

  def setFilter(self, filter):
    if app.config.strict_debug:
      assert type(filter) is str
    self.filter = filter
    self.shownList = None  # Cause a refresh.

  def unfocus(self):
    self.items = None
    self.shownList = None


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
    if app.config.strict_debug:
      assert type(name) is str
      assert type(value) is str
    self.getNamedWindow('predictionList').controller.shownList = None

  def passEventToPredictionList(self):
    self.getNamedWindow('predictionList').controller.doCommand(self.savedCh,
        None)

  def openAlternateFile(self):
    app.log.info()
    predictionList = self.getNamedWindow('predictionList')
    predictionList.controller.openAltFile()

  def performPrimaryAction(self):
    app.log.info()
    predictionList = self.getNamedWindow('predictionList')
    row = predictionList.textBuffer.penRow
    predictionList.controller.openFileOrDir(row)

  def predictionListPrior(self):
    predictionList = self.getNamedWindow('predictionList')
    if predictionList.textBuffer.penRow == 0:
      predictionList.textBuffer.cursorMoveTo(
          predictionList.textBuffer.parser.rowCount(), 0)
    else:
      predictionList.textBuffer.cursorUp()

  def unfocus(self):
    self.getNamedWindow('predictionList').unfocus()
    app.controller.Controller.unfocus(self)
