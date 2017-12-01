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

import app.buffer_manager
import app.controller
import os


class FileManagerController(app.controller.Controller):
  """

          Work in progress.

  """
  def __init__(self, host):
    app.controller.Controller.__init__(self, host, 'FileManagerController')
    self.counter = 0
    self.inputWindow = host
    self.shownDirectory = None

  def doCommand(self, ch, meta):
    app.log.info(ch, meta)
    pass

  def focus(self):
    self.onChange()
    app.controller.Controller.focus(self)

  def onChange(self):
    app.log.info()
    self.counter += 1  ############# remove
    input = self.host.path
    if self.shownDirectory == input:
      return
    self.shownDirectory = input
    path = os.path.abspath(os.path.expanduser(os.path.expandvars(input)))
    if os.path.isfile(path) and os.access(path, os.R_OK):
      app.log.info('got a file', path)
      textBuffer = app.buffer_manager.buffers.loadTextBuffer(path,
          self.inputWindow)
      self.inputWindow.setTextBuffer(textBuffer)
      return
    dirPath = path or '.'
    fileName = ''
    if len(input) > 0 and input[-1] != os.sep:
      dirPath, fileName = os.path.split(path)
    if os.path.isdir(dirPath):
      lines = [str(self.counter)]
      try:
        contents = os.listdir(dirPath)
        contents.sort()
        for i in contents:
          if os.path.isdir(os.path.join(dirPath, i)):
            i += '/'
          lines.append(i)
      except OSError as e:
        lines.append('Error opening directory.')
        lines.append(unicode(e))
      clip = [dirPath + ":"] + lines
    else:
      clip = [dirPath + ": not found"]
    #app.log.info(clip)
    self.host.textBuffer.selectionAll()
    self.host.textBuffer.editPasteLines(tuple(clip))
    #self.host.textBuffer.findPlainText(fileName)
    self.host.textBuffer.penRow = 0
    self.host.textBuffer.penCol = 0
    self.host.scrollRow = 0
    self.host.scrollCol = 0

  if 0:
    def setTextBuffer(self, textBuffer):
      pass

    def unfocus(self):
      pass
