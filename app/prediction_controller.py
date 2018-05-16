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
    # |items| is a tuple of: buffer, path, flags, type.
    self.items = None
    self.shownList = None

  def buildFileList(self, currentFile):
    if app.config.strict_debug:
      assert type(currentFile) is str

    self.items = []
    for i in app.buffer_manager.buffers.buffers:
      dirty = '*' if i.isDirty() else '.'
      if i.fullPath:
        self.items.append((i, i.fullPath, dirty, 'open'))
      else:
        self.items.append((i, '<new file> %s'%(i.lines[0][:20]), dirty, 'new'))
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
        self.items.append((None, os.path.join(dirPath, i), '=', 'alt'))
    if 1:
      app.log.info()
      # Chromium specific hack.
      if currentFile.endswith('-extracted.js'):
        chromiumPath = currentFile[:-len('-extracted.js')] + '.html'
        app.log.info(chromiumPath)
        if os.path.isfile(chromiumPath):
          app.log.info()
          self.items.append((None, chromiumPath, '=', 'alt'))
      elif currentFile.endswith('.html'):
        app.log.info()
        chromiumPath = currentFile[:-len('.html')] + '-extracted.js'
        if os.path.isfile(chromiumPath):
          app.log.info()
          self.items.append((None, chromiumPath, '=', 'alt'))

  def focus(self):
    self.onChange()
    app.controller.Controller.focus(self)

  def info(self):
    app.log.info('PredictionListController command set')

  def onChange(self):
    app.log.info(repr(self.items), repr(self.shownList))
    app.log.info(self.view.textBuffer.penRow)

    input = self.view.parent.getPath()
    if self.shownList == input:
      return
    self.shownList = input

    inputWindow = self.currentInputWindow()
    self.buildFileList(inputWindow.textBuffer.fullPath)
    app.log.info(self.items)
    if self.items is not None:
      self.view.update(self.items)
    self.filter = None

  def openFileOrDir(self, row):
    if app.config.strict_debug:
      assert type(row) is int
    if self.items is None:
      return
    textBuffer, fullPath = self.items[row][:2]
    self.items = None
    self.shownList = None
    app.log.info(self.items)
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

  def performPrimaryAction(self):
    app.log.info()
    predictionList = self.getNamedWindow('predictionList')
    row = predictionList.textBuffer.penRow
    predictionList.controller.openFileOrDir(row)

  def unfocus(self):
    self.getNamedWindow('predictionList').unfocus()
    app.controller.Controller.unfocus(self)
