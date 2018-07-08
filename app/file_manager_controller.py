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

import os
import re
import time

from app.curses_util import *
import app.buffer_file
import app.buffer_manager
import app.controller


class DirectoryListController(app.controller.Controller):
  """Gather and prepare file directory information.
  """
  def __init__(self, view):
    assert self is not view
    app.controller.Controller.__init__(self, view, 'DirectoryListController')
    self.filter = None
    self.shownDirectory = None

  def focus(self):
    self.onChange()
    app.controller.Controller.focus(self)

  def info(self):
    app.log.info('DirectoryListController command set')

  def onChange(self):
    input = self.view.parent.getPath()
    if self.shownDirectory == input:
      return
    self.shownDirectory = input
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
      showDotFiles = app.prefs.editor['filesShowDotFiles']
      showSizes = app.prefs.editor['filesShowSizes']
      showModified = app.prefs.editor['filesShowModifiedDates']

      sortByName = app.prefs.editor['filesSortAscendingByName']
      sortBySize = app.prefs.editor['filesSortAscendingBySize']
      sortByModifiedDate = app.prefs.editor['filesSortAscendingByModifiedDate']

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
        if sortBySize is not None:
          # Sort by size.
          fileLines.sort(reverse=not sortBySize,
              key=lambda x: x[1])
        elif sortByModifiedDate is not None:
          # Sort by modification date.
          fileLines.sort(reverse=not sortByModifiedDate,
              key=lambda x: x[2])
        else:
          fileLines.sort(reverse=not sortByName,
              key=lambda x: unicode.lower(x[0]))
        lines = ['%-40s  %16s  %24s' % (
            i[0], '%s bytes' % (i[1],) if i[1] is not None else '',
            unicode(time.strftime('%c', time.localtime(i[2]))) if i[2] else '')
            for i in fileLines]
        self.view.contents = [i[0] for i in fileLines]
      except OSError as e:
        lines = ['Error opening directory.']
        lines.append(unicode(e))
      clip = ['./', '../'] + lines
    else:
      clip = [dirPath + ": not found"]
    self.view.textBuffer.replaceLines(tuple(clip))
    #self.view.textBuffer.findPlainText(fileName)
    self.view.textBuffer.penRow = 0
    self.view.textBuffer.penCol = 0
    self.view.scrollRow = 0
    self.view.scrollCol = 0
    self.filter = None

  def openFileOrDir(self, row):
    path = self.view.host.getPath()
    if row == 0:  # Clicked on "./".
      # Clear the shown directory to trigger a refresh.
      self.shownDirectory = None
      return
    elif row == 1:  # Clicked on "../".
      if path[-1] == os.path.sep:
        path = path[:-1]
      path = os.path.dirname(path)
      if len(path) > len(os.path.sep):
        path += os.path.sep
      self.view.host.setPath(path)
      return
    # If there is a partially typed name in the line, clear it.
    if path[-1:] != os.path.sep:
      path = os.path.dirname(path) + os.path.sep
    self.view.host.setPath(path + self.view.contents[row - 2])
    if not os.path.isdir(self.view.host.getPath()):
      self.view.host.controller.performPrimaryAction()

  def optionChanged(self, name, value):
    self.shownDirectory = None
    self.onChange()

  def setFilter(self, filter):
    self.filter = filter
    self.shownDirectory = None  # Cause a refresh.


class FileManagerController(app.controller.Controller):
  """Create or open files.
  """
  def __init__(self, view):
    app.controller.Controller.__init__(self, view, 'FileManagerController')

  def performPrimaryAction(self):
    self.view.pathWindow.controller.performPrimaryAction()

  def info(self):
    app.log.info('FileManagerController command set')

  def onChange(self):
    self.view.directoryList.controller.onChange()
    app.controller.Controller.onChange(self)

  def optionChanged(self, name, value):
    self.view.directoryList.controller.shownDirectory = None

  def passEventToDirectoryList(self):
    self.view.directoryList.controller.doCommand(self.savedCh, None)


class FilePathInputController(app.controller.Controller):
  """Manipulate path string.
  """
  def __init__(self, view):
    app.controller.Controller.__init__(self, view, 'FilePathInputController')
    self.primaryActions = {
      'open': self.doCreateOrOpen,
      'saveAs': self.doSaveAs,
      'selectDir': self.doSelectDir,
    }

  def performPrimaryAction(self):
    directoryList = self.getNamedWindow('directoryList')
    row = directoryList.textBuffer.penRow
    if row == 0:
      if not os.path.isdir(self.view.getPath()):
        self.primaryActions[self.view.parent.mode]()
    else:
      directoryList.controller.openFileOrDir(row)

  def doCreateOrOpen(self):
    path = self.textBuffer.lines[0]
    if not os.access(path, os.R_OK):
      if os.path.isfile(path):
        clip = [path + ":", 'Error opening file.']
        return
    self.view.textBuffer.replaceLines(('',))
    textBuffer = app.buffer_manager.buffers.loadTextBuffer(path)
    assert textBuffer.parser
    inputWindow = self.currentInputWindow()
    inputWindow.setTextBuffer(textBuffer)
    self.changeTo(inputWindow)

  def doSaveAs(self):
    path = self.textBuffer.lines[0]
    inputWindow = self.currentInputWindow()
    tb = inputWindow.textBuffer
    tb.setFilePath(path);
    self.changeTo(inputWindow)
    if not len(path):
      tb.setMessage('File not saved (file name was empty).')
      return
    if not tb.isSafeToWrite():
      self.view.changeFocusTo(inputWindow.confirmOverwrite)
      return
    tb.fileWrite();
    self.view.textBuffer.replaceLines(('',))

  def doSelectDir(self):
    # TODO(dschuyler): not yet implemented.
    self.view.textBuffer.replaceLines(('',))
    self.changeToInputWindow()

  def focus(self):
    if self.view.textBuffer.isEmpty():
      inputWindow = self.currentInputWindow()
      if len(inputWindow.textBuffer.fullPath) == 0:
        path = os.getcwd()
      else:
        path = os.path.dirname(inputWindow.textBuffer.fullPath)
      if len(path) != 0:
        path += os.path.sep
      self.view.textBuffer.replaceLines((path,))
    self.getNamedWindow('directoryList').focus()
    app.controller.Controller.focus(self)

  def info(self):
    app.log.info('FilePathInputController command set')

  def maybeSlash(self, expandedPath):
    if (self.textBuffer.lines[0] and self.textBuffer.lines[0][-1] != '/' and
        os.path.isdir(expandedPath)):
      self.textBuffer.insert('/')

  def onChange(self):
    self.getNamedWindow('directoryList').controller.onChange()
    app.controller.Controller.onChange(self)

  def optionChanged(self, name, value):
    self.getNamedWindow('directoryList').controller.shownDirectory = None

  def passEventToDirectoryList(self):
    self.getNamedWindow('directoryList').controller.doCommand(self.savedCh, None)

  def tabCompleteExtend(self):
    """Extend the selection to match characters in common."""
    expandedPath = os.path.expandvars(os.path.expanduser(
        self.textBuffer.lines[0]))
    dirPath, fileName = os.path.split(expandedPath)
    expandedDir = dirPath or '.'
    matches = []
    if not os.path.isdir(expandedDir):
      return
    for i in os.listdir(expandedDir):
      if i.startswith(fileName):
        matches.append(i)
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
    if expandedPath == os.path.expandvars(os.path.expanduser(
        self.textBuffer.lines[0])):
      # No further expansion found.
      self.getNamedWindow('directoryList').controller.setFilter(fileName)
    self.onChange()
