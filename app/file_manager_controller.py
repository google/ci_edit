# Copyright 2017 Google Inc.
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

from app.curses_util import *
import app.buffer_manager
import app.controller
import os
import time


class DirectoryListController(app.controller.Controller):
  """

          Work in progress.

  """
  def __init__(self, host):
    app.controller.Controller.__init__(self, host, 'DirectoryListController')
    self.shownDirectory = None

  def focus(self):
    self.onChange()
    app.controller.Controller.focus(self)

  def onChange(self):
    input = self.host.getPath()
    app.log.debug(input, "\n", self.shownDirectory)
    if self.shownDirectory == input:
      return
    self.shownDirectory = input
    path = os.path.abspath(os.path.expanduser(os.path.expandvars(input)))
    if os.path.isfile(path):
      return
      if not os.access(path, os.R_OK):
        clip = [input + ":", 'Error opening file.']
      else:
        app.log.info('got a file', path)
        textBuffer = app.buffer_manager.buffers.loadTextBuffer(path,
            self.host.host.inputWindow)
        self.host.host.inputWindow.setTextBuffer(textBuffer)
        self.changeToInputWindow()
        return
    else:
      dirPath = path or '.'
      fileName = ''
      if len(input) > 0 and input[-1] != os.sep:
        dirPath, fileName = os.path.split(path)
      if os.path.isdir(dirPath):
        lines = []
        try:
          fileLines = []
          contents = os.listdir(dirPath)
          for i in contents:
            if not self.host.host.opt['dotFiles'] and i[0] == '.':
              continue
            fullPath = os.path.join(dirPath, i)
            if os.path.isdir(fullPath):
              i += os.path.sep
            iSize = ''
            iModified = ''
            if self.host.host.opt['sizes'] and os.path.isfile(fullPath):
              iSize = '%d bytes' % os.path.getsize(fullPath)
            if self.host.host.opt['modified']:
              iModified = os.path.getmtime(fullPath)
            fileLines.append([i, iSize, iModified])
          if self.host.opt['Size'] is not None:
            # Sort by size.
            fileLines.sort(reverse=not self.host.opt['Size'],
                key=lambda x: x[1])
          elif self.host.opt['Modified'] is not None:
            # Sort by modification date.
            fileLines.sort(reverse=not self.host.opt['Modified'],
                key=lambda x: x[2])
          else:
            fileLines.sort(reverse=not self.host.opt['Name'],
                key=lambda x: unicode.lower(x[0]))
          lines = ['%-40s  %16s  %24s' % (
              i[0], i[1], unicode(time.strftime('%c', time.localtime(i[2]))))
              for i in fileLines]
          self.host.contents = [i[0] for i in fileLines]
        except OSError as e:
          lines = ['Error opening directory.']
          lines.append(unicode(e))
        clip = ['./', '../'] + lines
      else:
        clip = [dirPath + ": not found"]
    self.host.textBuffer.selectionAll()
    self.host.textBuffer.editPasteLines(tuple(clip))
    #self.host.textBuffer.findPlainText(fileName)
    self.host.textBuffer.penRow = 0
    self.host.textBuffer.penCol = 0
    self.host.scrollRow = 0
    self.host.scrollCol = 0

  def optionChanged(self, name, value):
    self.shownDirectory = None

  def setTextBuffer(self, textBuffer):
    app.controller.Controller.setTextBuffer(self, textBuffer)
    self.commandSet = {
      CTRL_Q: self.saveEventChangeToInputWindow,

      KEY_ESCAPE: self.changeToInputWindow,
    }
    self.commandDefault = self.textBuffer.noOpDefault


class FileManagerController(app.controller.Controller):
  """

          Work in progress.

  """
  def __init__(self, host):
    app.controller.Controller.__init__(self, host, 'FileManagerController')

  def createOrOpen(self):
    path = self.textBuffer.lines[0]
    if not os.path.isfile(path):
      return
    if not os.access(path, os.R_OK):
      clip = [input + ":", 'Error opening file.']
    else:
      app.log.info('got a file', path)
      textBuffer = app.buffer_manager.buffers.loadTextBuffer(path,
          self.host.host.inputWindow)
      self.host.host.inputWindow.setTextBuffer(textBuffer)
      self.changeToInputWindow()

  def focus(self):
    self.textBuffer.selectionAll()
    if len(self.host.inputWindow.textBuffer.fullPath) == 0:
      path = os.getcwd()
    else:
      path = os.path.dirname(self.host.inputWindow.textBuffer.fullPath)
    if len(path) != 0:
      path += os.path.sep
    self.textBuffer.editPasteLines((path,))
    self.host.directoryList.focus()
    app.controller.Controller.focus(self)

  def info(self):
    app.log.info('FileManagerController command set')

  def onChange(self):
    self.host.directoryList.controller.onChange()
    app.controller.Controller.onChange(self)

  def optionChanged(self, name, value):
    self.host.directoryList.controller.shownDirectory = None

  def maybeSlash(self, expandedPath):
    if (self.textBuffer.lines[0] and self.textBuffer.lines[0][-1] != '/' and
        os.path.isdir(expandedPath)):
      self.textBuffer.insert('/')

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
