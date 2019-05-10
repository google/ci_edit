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

    def __init__(self, program, host):
        if app.config.strict_debug:
            assert host
            assert self is not host
        app.window.Window.__init__(self, program, host)
        self.host = host
        self.isFocusable = False
        self.controller = app.cu_editor.PredictionList(self)
        self.setTextBuffer(app.text_buffer.TextBuffer(self.program))
        # Set up table headers.
        color = host.program.color.get(u'top_info')
        self.optionsRow = app.window.OptionsSelectionWindow(self.program, self)
        self.optionsRow.setParent(self)
        self.typeColumn = app.window.SortableHeaderWindow(
            self.program, self.optionsRow, u'Type', u'editor',
            u'predictionSortAscendingByType', 8)
        label = app.window.LabelWindow(self.program, self.optionsRow, u'|')
        label.setParent(self.optionsRow)
        label.color = color
        self.nameColumn = app.window.SortableHeaderWindow(
            self.program, self.optionsRow, u'Name', u'editor',
            u'predictionSortAscendingByName', -61)
        label = app.window.LabelWindow(self.program, self.optionsRow, u'|')
        label.setParent(self.optionsRow)
        label.color = color
        self.statusColumn = app.window.SortableHeaderWindow(
            self.program, self.optionsRow, u'Status ', u'editor',
            u'predictionSortAscendingByStatus', -7)
        label = app.window.LabelWindow(self.program, self.optionsRow, u'|')
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
        # Filter the list. (The filter function is not used so as to edit the
        # list in place).
        appPrefs = self.program.prefs
        showOpen = appPrefs.editor[u'predictionShowOpenFiles']
        showAlternate = appPrefs.editor[u'predictionShowAlternateFiles']
        showRecent = appPrefs.editor[u'predictionShowRecentFiles']
        if not (showOpen and showAlternate and showRecent):
            i = 0
            while i < len(items):
                if not showOpen and items[i][3] == u'open':
                    items.pop(i)
                elif not showAlternate and items[i][3] == u'alt':
                    items.pop(i)
                elif not showRecent and items[i][3] == u'recent':
                    items.pop(i)
                else:
                    i += 1
        # Sort the list
        sortByPrediction = appPrefs.editor[u'predictionSortAscendingByPrediction']
        sortByType = appPrefs.editor[u'predictionSortAscendingByType']
        sortByName = appPrefs.editor[u'predictionSortAscendingByName']
        sortByStatus = appPrefs.editor[u'predictionSortAscendingByStatus']
        if sortByPrediction is not None:
            items.sort(reverse=not sortByPrediction, key=lambda x: x[4])
        elif sortByType is not None:
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
            self.textBuffer.replaceLines((u'',))
        else:
            self.textBuffer.replaceLines(
                tuple([
                    u"%*s %*s %.*s" %
                    (self.typeColumn.cols, i[3], -self.nameColumn.cols,
                     fitPathToWidth(i[1], self.nameColumn.cols),
                     self.statusColumn.cols, i[2]) for i in items
                ]))
        self.textBuffer.parseScreenMaybe()  # TODO(dschuyler): Add test.
        self.textBuffer.cursorMoveToBegin()

    def onPrefChanged(self, category, name):
        self.controller.optionChanged(category, name)
        app.window.Window.onPrefChanged(self, category, name)

    def reshape(self, top, left, rows, cols):
        """Change self and sub-windows to fit within the given rectangle."""
        app.log.detail(u'reshape', top, left, rows, cols)
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

    def __init__(self, program, host):
        if app.config.strict_debug:
            assert host
            assert issubclass(host.__class__, app.window.ActiveWindow), host
        app.window.Window.__init__(self, program, host)
        self.host = host
        self.controller = app.cu_editor.PredictionInputController(self)
        self.setTextBuffer(app.text_buffer.TextBuffer(self.program))

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

    def __init__(self, program, host):
        app.window.Window.__init__(self, program, host)

        self.showTips = False
        self.controller = app.cu_editor.PredictionController(self)
        self.setTextBuffer(app.text_buffer.TextBuffer(self.program))

        self.titleRow = app.window.OptionsRow(self.program, self)
        self.titleRow.addLabel(u' ci   ')
        self.titleRow.setParent(self)

        self.predictionInputWindow = PredictionInputWindow(self.program, self)
        self.predictionInputWindow.setParent(self)

        self.predictionList = PredictionList(self.program, self)
        self.predictionList.setParent(self)

        if 1:
            self.optionsRow = app.window.RowWindow(self.program, self, 2)
            self.optionsRow.setParent(self)
            colorPrefs = host.program.color
            self.optionsRow.color = colorPrefs.get(u'top_info')
            label = app.window.LabelWindow(self.program, self.optionsRow,
                                           u'Show:')
            label.color = colorPrefs.get(u'top_info')
            label.setParent(self.optionsRow)
            toggle = app.window.OptionsToggle(self.program, self.optionsRow,
                                              u'open', u'editor',
                                              u'predictionShowOpenFiles')
            toggle.color = colorPrefs.get(u'top_info')
            toggle = app.window.OptionsToggle(self.program, self.optionsRow,
                                              u'alternates', u'editor',
                                              u'predictionShowAlternateFiles')
            toggle.color = colorPrefs.get(u'top_info')
            toggle = app.window.OptionsToggle(self.program, self.optionsRow,
                                              u'recent', u'editor',
                                              u'predictionShowRecentFiles')
            toggle.color = colorPrefs.get(u'top_info')

        self.messageLine = app.window.LabelWindow(self.program, self, u"")
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
