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

import app.color
import app.config
import app.cu_editor
import app.log
import app.text_buffer
import app.window


# todo remove or use this.
class PathRow(app.window.ViewWindow):
  def __init__(self, host):
    if app.config.strict_debug:
      assert(host)
    app.window.ViewWindow.__init__(self, host)
    self.host = host
    self.path = ''

  def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
    row = self.scrollRow + paneRow
    col = self.scrollCol + paneCol
    line = self.path
    col = self.scrollCol + paneCol
    self.host.controller.shownDirectory = None
    if col >= len(line):
      return
    slash = line[col:].find('/')
    self.path = line[:col + slash + 1]

  def render(self):
    app.log.debug()
    offset = 0
    color = app.color.get('message_line')
    #self.addStr(0, 0, self.path, color)
    self.writeLineRow = 0
    self.writeLine(self.path, color)


class DirectoryList(app.window.Window):
  """This <tbd>."""
  def __init__(self, host, inputWindow):
    if app.config.strict_debug:
      assert host
      assert self is not host
    app.window.Window.__init__(self, host)
    self.host = host
    self.inputWindow = inputWindow
    self.controller = app.cu_editor.DirectoryList(self)
    self.setTextBuffer(app.text_buffer.TextBuffer())
    self.optionsRow = app.window.OptionsRow(self)
    self.opt = {
      'Name': True,
      'Size': None,
      'Modified': None,
    }
    self.optionsRow.beginGroup()
    for key, size in [('Name', -40), ('Size', 15), ('Modified', 24)]:
      self.optionsRow.addSortHeader(key, self.opt, size)
    self.optionsRow.setParent(self, 0)
    self.optionsRow.endGroup()

  def reshape(self, top, left, rows, cols):
    """Change self and sub-windows to fit within the given rectangle."""
    app.log.detail('reshape', top, left, rows, cols)
    self.optionsRow.reshape(top, left, 1, cols)
    top += 1
    rows -= 1
    app.window.Window.reshape(self, top, left, rows, cols)

  def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
    row = self.scrollRow + paneRow
    if row >= len(self.textBuffer.lines):
      return
    self.controller.openFileOrDir(row)

  def mouseDoubleClick(self, paneRow, paneCol, shift, ctrl, alt):
    self.changeFocusTo(self.host)

  def mouseMoved(self, paneRow, paneCol, shift, ctrl, alt):
    self.changeFocusTo(self.host)

  def mouseRelease(self, paneRow, paneCol, shift, ctrl, alt):
    self.changeFocusTo(self.host)

  def mouseTripleClick(self, paneRow, paneCol, shift, ctrl, alt):
    self.changeFocusTo(self.host)

  def mouseWheelDown(self, shift, ctrl, alt):
    self.textBuffer.mouseWheelDown(shift, ctrl, alt)
    self.changeFocusTo(self.host)

  def mouseWheelUp(self, shift, ctrl, alt):
    self.textBuffer.mouseWheelUp(shift, ctrl, alt)
    self.changeFocusTo(self.host)

  def onPrefChanged(self, category, name):
    self.controller.optionChanged(category, name)
    app.window.Window.onPrefChanged(self, category, name)

  def setTextBuffer(self, textBuffer):
    if app.config.strict_debug:
      assert textBuffer is not self.host.textBuffer
    textBuffer.lineLimitIndicator = 0
    textBuffer.highlightCursorLine = True
    textBuffer.highlightTrailingWhitespace = False
    app.window.Window.setTextBuffer(self, textBuffer)
    self.controller.setTextBuffer(textBuffer)


class FileManagerWindow(app.window.Window):
  def __init__(self, host, inputWindow):
    if app.config.strict_debug:
      assert host
      assert issubclass(host.__class__, app.window.ActiveWindow), host
    app.window.Window.__init__(self, host)
    self.host = host
    self.inputWindow = inputWindow
    self.inputWindow.fileManagerWindow = self
    self.mode = 'open'
    self.showTips = False
    self.controller = app.cu_editor.FileOpener(self)
    self.setTextBuffer(app.text_buffer.TextBuffer())

    self.titleRow = app.window.OptionsRow(self)
    self.titleRow.addLabel(' ci   ')
    self.modeTitle = self.titleRow.addLabel('x')
    self.setMode('open')
    self.titleRow.setParent(self, 0)

    self.directoryList = DirectoryList(self, inputWindow)
    self.directoryList.setParent(self, 0)
    self.messageLine = app.window.LabeledLine(self, "")
    self.messageLine.setParent(self, 0)

    if 1:
      self.optionsRow = app.window.RowWindow(self, 2)
      self.optionsRow.setParent(self)
      self.optionsRow.color = app.color.get('top_info')
      label = app.window.LabelWindow(self.optionsRow, 'Show:')
      label.color = app.color.get('top_info')
      label.setParent(self.optionsRow)
      toggle = app.window.OptionsToggle(self.optionsRow, 'dotFiles', 'editor',
          'filesShowDotFiles')
      toggle.color = app.color.get('top_info')
      toggle = app.window.OptionsToggle(self.optionsRow, 'sizes', 'editor',
          'filesShowSizes')
      toggle.color = app.color.get('top_info')
      toggle = app.window.OptionsToggle(self.optionsRow, 'modified', 'editor',
          'filesShowModifiedDates')
      toggle.color = app.color.get('top_info')

  def getPath(self):
    return self.textBuffer.lines[0]

  def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
    row = self.scrollRow + paneRow
    col = self.scrollCol + paneCol
    line = self.textBuffer.lines[0]
    col = self.scrollCol + paneCol
    self.directoryList.controller.shownDirectory = None
    if col >= len(line):
      return
    slash = line[col:].find('/')
    self.setPath(line[:col + slash + 1])

  def onPrefChanged(self, category, name):
    self.directoryList.controller.optionChanged(category, name)
    app.window.Window.onPrefChanged(self, category, name)

  def quitNow(self):
    app.log.debug()
    self.host.quitNow()

  def reshape(self, top, left, rows, cols):
    """Change self and sub-windows to fit within the given rectangle."""
    app.log.detail('reshape', top, left, rows, cols)
    originalRows = rows
    self.titleRow.reshape(top, left, 1, cols)
    top += 1
    rows -= 1
    app.window.Window.reshape(self, top, left, 1, cols)
    top += 1
    rows -= 1
    self.optionsRow.reshape(originalRows - 2, left, 1, cols)
    rows -= 1
    self.messageLine.reshape(originalRows - 1, left, 1, cols)
    rows -= 1
    self.directoryList.reshape(top, left, rows, cols)

  def setMode(self, mode):
    self.mode = mode
    modeTitles = {
      'open': 'Open File',
      'saveAs': 'Save File As',
      'selectDir': 'Select a Directory',
    }
    self.modeTitle['name'] = modeTitles[mode]

  def setTextBuffer(self, textBuffer):
    textBuffer.lineLimitIndicator = 0
    textBuffer.highlightTrailingWhitespace = False
    app.window.Window.setTextBuffer(self, textBuffer)
    self.controller.setTextBuffer(textBuffer)

  def setPath(self, path):
    self.textBuffer.replaceLines((path,))

