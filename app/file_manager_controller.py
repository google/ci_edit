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


class DirectoryListController(app.controller.Controller):
  """

          Work in progress.

  """
  def __init__(self, host):
    app.controller.Controller.__init__(self, host, 'DirectoryListController')
    self.shownDirectory = None

  #def doCommand(self, ch, meta):
  #  app.log.info(ch, meta)
  #  pass

  def focus(self):
    self.onChange()
    app.controller.Controller.focus(self)

  def onChange(self):
    input = self.host.host.path
    if self.shownDirectory == input:
      return
    self.shownDirectory = input
    path = os.path.abspath(os.path.expanduser(os.path.expandvars(input)))
    if os.path.isfile(path):
      if not os.access(path, os.R_OK):
        clip = [self.host.host.path + ":", 'Error opening file.']
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
        self.host.contents = []
        try:
          contents = os.listdir(dirPath)
          lines.append('./')
          lines.append('../')
          contents.sort(reverse=not self.host.host.opt['sortUp'])
          for i in contents:
            if not self.host.host.opt['dotFiles'] and i[0] == '.':
              continue
            fullPath = os.path.join(dirPath, i)
            if os.path.isdir(fullPath):
              i += os.path.sep
            self.host.contents.append(i)
            if self.host.host.opt['sizes'] and os.path.isfile(fullPath):
              i = '%-30s %9d bytes' % (i, os.path.getsize(fullPath))
            lines.append(i)
        except OSError as e:
          lines.append('Error opening directory.')
          lines.append(unicode(e))
        clip = lines
      else:
        clip = [dirPath + ": not found"]
    self.host.textBuffer.selectionAll()
    self.host.textBuffer.editPasteLines(tuple(clip))
    #self.host.textBuffer.findPlainText(fileName)
    self.host.textBuffer.penRow = 0
    self.host.textBuffer.penCol = 0
    self.host.scrollRow = 0
    self.host.scrollCol = 0

  def setTextBuffer(self, textBuffer):
    app.controller.Controller.setTextBuffer(self, textBuffer)
    self.commandSet = {
      CTRL_Q: self.saveEventChangeToInputWindow,

      KEY_ESCAPE: self.changeToInputWindow,
    }
    self.commandDefault = self.textBuffer.noOpDefault

  if 0:
    def unfocus(self):
      pass


class FileManagerController(app.controller.Controller):
  """

          Work in progress.

  """
  def __init__(self, host):
    app.controller.Controller.__init__(self, host, 'FileManagerController')
    self.shownDirectory = None

  #def doCommand(self, ch, meta):
  #  app.log.info(ch, meta)
  #  pass

  def focus(self):
    path = self.host.host.inputWindow.textBuffer.fullPath
    path, fileName = os.path.split(path)
    path = os.path.abspath(os.path.expanduser(os.path.expandvars(path)))
    path += os.path.sep
    self.host.path = path
    self.host.directoryList.focus()
    app.controller.Controller.focus(self)

  def onChange(self):
    self.host.directoryList.controller.onChange()
    app.controller.Controller.onChange(self)

  def aaaaonChange(self):
    input = self.host.path
    if self.shownDirectory == input:
      return
    self.shownDirectory = input
    path = os.path.abspath(os.path.expanduser(os.path.expandvars(input)))
    if os.path.isfile(path):
      if not os.access(path, os.R_OK):
        clip = [self.host.path + ":", 'Error opening file.']
      else:
        app.log.info('got a file', path)
        textBuffer = app.buffer_manager.buffers.loadTextBuffer(path,
            self.host.inputWindow)
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
        self.host.contents = []
        try:
          contents = os.listdir(dirPath)
          lines.append('./')
          lines.append('../')
          contents.sort(reverse=not self.host.opt['sortUp'])
          for i in contents:
            if not self.host.opt['dotFiles'] and i[0] == '.':
              continue
            fullPath = os.path.join(dirPath, i)
            if os.path.isdir(fullPath):
              i += os.path.sep
            self.host.contents.append(i)
            if self.host.opt['sizes'] and os.path.isfile(fullPath):
              i = '%-30s %9d bytes' % (i, os.path.getsize(fullPath))
            lines.append(i)
        except OSError as e:
          lines.append('Error opening directory.')
          lines.append(unicode(e))
        clip = lines
      else:
        clip = [dirPath + ": not found"]
    self.host.textBuffer.selectionAll()
    self.host.textBuffer.editPasteLines(tuple(clip))
    #self.host.textBuffer.findPlainText(fileName)
    self.host.textBuffer.penRow = 0
    self.host.textBuffer.penCol = 0
    self.host.scrollRow = 0
    self.host.scrollCol = 0

  def setTextBuffer(self, textBuffer):
    app.controller.Controller.setTextBuffer(self, textBuffer)
    self.commandSet = {
      CTRL_Q: self.saveEventChangeToInputWindow,

      KEY_ESCAPE: self.changeToInputWindow,
    }
    self.commandDefault = self.textBuffer.noOpDefault
