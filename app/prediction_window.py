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

import app.config
import app.cu_editor
import app.log
import app.text_buffer
import app.window


class PredictionList(app.window.Window):
  """This <tbd>."""
  def __init__(self, host):
    if app.config.strict_debug:
      assert host
      assert self is not host
    app.window.Window.__init__(self, host)
    self.host = host
    self.isFocusable = False
    self.controller = app.cu_editor.PredictionList(self)
    self.setTextBuffer(app.text_buffer.TextBuffer(
        self.programWindow().program.prefs))
    # Set up table headers.
    color = host.programWindow().program.color.get('top_info')
    self.optionsRow = app.window.OptionsSelectionWindow(self)
    self.optionsRow.setParent(self)
    self.typeColumn = app.window.SortableHeaderWindow(self.optionsRow, 'Type',
        'editor', 'predictionSortAscendingByType', 8)
    label = app.window.LabelWindow(self.optionsRow, '|')
    label.setParent(self.optionsRow)
    label.color = color
    self.nameColumn = app.window.SortableHeaderWindow(self.optionsRow, 'Name',
        'editor', 'predictionSortAscendingByName', -61)
    label = app.window.LabelWindow(self.optionsRow, '|')
    label.setParent(self.optionsRow)
    label.color = color
    self.statusColumn = app.window.SortableHeaderWindow(self.optionsRow,
        'Status ', 'editor', 'predictionSortAscendingByStatus', -7)
    label = app.window.LabelWindow(self.optionsRow, '|')
    label.setParent(self.optionsRow)
    label.color = color

  def highlightLine(self, row):
    self.textBuffer.penRow = min(row, self.textBuffer.parser.rowCount() - 1)
    self.textBuffer.penCol = 0
    app.log.info(self.textBuffer.penRow)

  def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
    self.highlightLine(self.scrollRow + paneRow)
    row = self.scrollRow + paneRow
    if row >= self.textBuffer.parser.rowCount():
      return
    self.controller.openFileOrDir(row)

  def mouseDoubleClick(self, paneRow, paneCol, shift, ctrl, alt):
    app.log.info()
    assert False

  #def mouseMoved(self, paneRow, paneCol, shift, ctrl, alt):
  #  app.log.info()

  #def mouseRelease(self, paneRow, paneCol, shift, ctrl, alt):
  #  app.log.info()

  #def mouseTripleClick(self, paneRow, paneCol, shift, ctrl, alt):
  #  app.log.info()

  def mouseWheelDown(self, shift, ctrl, alt):
    self.textBuffer.mouseWheelDown(shift, ctrl, alt)

  def mouseWheelUp(self, shift, ctrl, alt):
    self.textBuffer.mouseWheelUp(shift, ctrl, alt)

  def update(self, items):
    # Filter the list. (The filter function is not used so as to edit the list
    # in place).
    appPrefs = self.programWindow().program.prefs
    showOpen = appPrefs.editor['predictionShowOpenFiles']
    showAlternate = appPrefs.editor['predictionShowAlternateFiles']
    showRecent = appPrefs.editor['predictionShowRecentFiles']
    if not (showOpen and showAlternate and showRecent):
      i = 0
      while i < len(items):
        if not showOpen and items[i][3] == 'open':
          items.pop(i)
        elif not showAlternate and items[i][3] == 'alt':
          items.pop(i)
        elif not showRecent and items[i][3] == 'recent':
          items.pop(i)
        else:
          i += 1
    # Sort the list
    sortByType = appPrefs.editor['predictionSortAscendingByType']
    sortByName = appPrefs.editor['predictionSortAscendingByName']
    sortByStatus = appPrefs.editor['predictionSortAscendingByStatus']
    if sortByType is not None:
      items.sort(reverse=not sortByType, key=lambda x: x[3])
    elif sortByStatus is not None:
      items.sort(reverse=not sortByStatus, key=lambda x: x[2])
    elif sortByName is not None:
      items.sort(reverse=not sortByName, key=lambda x: x[1])
    # Write the lines to the text buffer.
    def fitPathToWidth(path, width):
      if len(path) < width:
        return path
      return path[-width:]
    if len(items) == 0:
      self.textBuffer.replaceLines(('',))
    else:
      self.textBuffer.replaceLines(tuple([
          "%*s %*s %.*s" % (
              self.typeColumn.cols, i[3],
              -self.nameColumn.cols, fitPathToWidth(i[1], self.nameColumn.cols),
              self.statusColumn.cols, i[2]
              ) for i in items
          ]))
    self.textBuffer.parseScreenMaybe()  # TODO(dschuyler): Add test.
    self.textBuffer.cursorMoveToBegin()

  def onPrefChanged(self, category, name):
    self.controller.optionChanged(category, name)
    app.window.Window.onPrefChanged(self, category, name)

  def reshape(self, top, left, rows, cols):
    """Change self and sub-windows to fit within the given rectangle."""
    app.log.detail('reshape', top, left, rows, cols)
    self.optionsRow.reshape(top, left, 1, cols)
    top += 1
    rows -= 1
    app.window.Window.reshape(self, top, left, rows, cols)

  def setTextBuffer(self, textBuffer):
    if app.config.strict_debug:
      assert textBuffer is not self.host.textBuffer
    textBuffer.lineLimitIndicator = 0
    textBuffer.highlightCursorLine = True
    textBuffer.highlightTrailingWhitespace = False
    app.window.Window.setTextBuffer(self, textBuffer)
    self.controller.setTextBuffer(textBuffer)


class PredictionInputWindow(app.window.Window):
  def __init__(self, host):
    if app.config.strict_debug:
      assert host
      assert issubclass(host.__class__, app.window.ActiveWindow), host
    app.window.Window.__init__(self, host)
    self.host = host
    self.controller = app.cu_editor.PredictionInputController(self)
    self.setTextBuffer(app.text_buffer.TextBuffer(
        self.programWindow().program.prefs))

  def getPath(self):
    return self.textBuffer.parser.rowText(0)

  def setPath(self, path):
    self.textBuffer.replaceLines((path,))

  def setTextBuffer(self, textBuffer):
    textBuffer.lineLimitIndicator = 0
    textBuffer.highlightTrailingWhitespace = False
    app.window.Window.setTextBuffer(self, textBuffer)
    self.controller.setTextBuffer(textBuffer)


class PredictionWindow(app.window.Window):
  def __init__(self, host):
    app.window.Window.__init__(self, host)

    self.showTips = False
    self.controller = app.cu_editor.PredictionController(self)
    self.setTextBuffer(app.text_buffer.TextBuffer(
        self.programWindow().program.prefs))

    self.titleRow = app.window.OptionsRow(self)
    self.titleRow.addLabel(' ci   ')
    self.titleRow.setParent(self)

    self.predictionInputWindow = PredictionInputWindow(self)
    self.predictionInputWindow.setParent(self)

    self.predictionList = PredictionList(self)
    self.predictionList.setParent(self)

    if 1:
      self.optionsRow = app.window.RowWindow(self, 2)
      self.optionsRow.setParent(self)
      colorPrefs = host.programWindow().program.color
      self.optionsRow.color = colorPrefs.get('top_info')
      label = app.window.LabelWindow(self.optionsRow, 'Show:')
      label.color = colorPrefs.get('top_info')
      label.setParent(self.optionsRow)
      toggle = app.window.OptionsToggle(self.optionsRow, 'open', 'editor',
          'predictionShowOpenFiles')
      toggle.color = colorPrefs.get('top_info')
      toggle = app.window.OptionsToggle(self.optionsRow, 'alternates', 'editor',
          'predictionShowAlternateFiles')
      toggle.color = colorPrefs.get('top_info')
      toggle = app.window.OptionsToggle(self.optionsRow, 'recent', 'editor',
          'predictionShowRecentFiles')
      toggle.color = colorPrefs.get('top_info')

    self.messageLine = app.window.LabelWindow(self, "")
    self.messageLine.setParent(self)

  def bringChildToFront(self, child):
    # The PredictionWindow window doesn't reorder children.
    pass

  def focus(self):
    self.reattach()
    self.parent.layout()
    app.window.Window.focus(self)
    self.changeFocusTo(self.predictionInputWindow)

  def getPath(self):
    return self.predictionInputWindow.getPath()

  def onPrefChanged(self, category, name):
    self.predictionList.controller.optionChanged(category, name)
    app.window.Window.onPrefChanged(self, category, name)

  def reshape(self, top, left, rows, cols):
    """Change self and sub-windows to fit within the given rectangle."""
    app.window.Window.reshape(self, top, left, rows, cols)
    self.titleRow.reshape(top, left, 1, cols)
    top += 1
    rows -= 1
    self.predictionInputWindow.reshape(top, left, 1, cols)
    top += 1
    rows -= 1
    self.messageLine.reshape(top + rows - 1, left, 1, cols)
    rows -= 1
    self.optionsRow.reshape(top + rows - 1, left, 1, cols)
    rows -= 1
    self.predictionList.reshape(top, left, rows, cols)

  def setPath(self, path):
    self.predictionInputWindow.setPath(path)

  def unfocus(self):
    app.window.Window.unfocus(self)
    self.detach()
