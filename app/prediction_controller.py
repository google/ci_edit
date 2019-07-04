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
    unicode
except NameError:
    unicode = str
    unichr = chr

import os
import re
import time
import warnings

import app.buffer_file
import app.controller
import app.string


class PredictionListController(app.controller.Controller):
    """Gather and prepare file directory information.
    """

    def __init__(self, view):
        assert self is not view
        app.controller.Controller.__init__(self, view,
                                           'PredictionListController')
        self.filter = None
        # |items| is a tuple of: buffer, path, flags, type.
        self.items = None
        self.shownList = None

    def _buildFileList(self, currentFile):
        if app.config.strict_debug:
            assert isinstance(currentFile, unicode), repr(currentFile)

        added = set()
        items = self.items = []
        if 1:
            # Add open buffers.
            def add_buffer(items, buffer, prediction):
                dirty = '*' if buffer.isDirty() else '.'
                if buffer.fullPath:
                    items.append((buffer, buffer.fullPath, dirty, 'open', prediction))
                    added.add(buffer.fullPath)
                else:
                    items.append(
                        (buffer, '<new file> %s' % (buffer.parser.rowText(0)[:20]), dirty,
                         'open', prediction))
            bufferManager = self.view.program.bufferManager
            # Add the most resent buffer to allow flipping back and forth
            # between two files.
            if len(bufferManager.buffers) >= 2:
                add_buffer(items, bufferManager.buffers[-2], 30000)
            order = 39999
            for i in bufferManager.buffers[:-2]:
                add_buffer(items, i, order)
                order -= 1
            # This is the current buffer. It's unlikely to be the goal.
            if len(bufferManager.buffers) >= 1:
                add_buffer(items, bufferManager.buffers[-1], 90000)
        if 1:
            # Add recent files.
            for recentFile in self.view.program.history.getRecentFiles():
                if recentFile not in added:
                    items.append((None, recentFile, '=', 'recent', 50000))
                    added.add(recentFile)
        if 1:
            # Add alternate files.
            dirPath, fileName = os.path.split(currentFile)
            fileName, ext = os.path.splitext(fileName)
            # TODO(dschuyler): rework this ignore list.
            ignoreExt = set(('.pyc', '.pyo', '.o', '.obj', '.tgz', '.zip',
                             '.tar'))
            try:
                contents = os.listdir(
                    os.path.expandvars(os.path.expanduser(dirPath)) or '.')
            except OSError:
                contents = []
            contents.sort()
            for i in contents:
                f, e = os.path.splitext(i)
                if fileName == f and ext != e and e not in ignoreExt:
                    fullPath = os.path.join(dirPath, i)
                    if fullPath not in added:
                        items.append((None, fullPath, '=', 'alt', 20000))
                        added.add(fullPath)
            if 1:
                # Chromium specific hack.
                if currentFile.endswith('-extracted.js'):
                    chromiumPath = currentFile[:-len('-extracted.js')] + '.html'
                    if os.path.isfile(
                            chromiumPath) and chromiumPath not in added:
                        items.append((None, chromiumPath, '=', 'alt', 20000))
                        added.add(chromiumPath)
                elif currentFile.endswith('.html'):
                    chromiumPath = currentFile[:-len('.html')] + '-extracted.js'
                    if os.path.isfile(
                            chromiumPath) and chromiumPath not in added:
                        items.append((None, chromiumPath, '=', 'alt', 20000))
                        added.add(chromiumPath)
        if self.filter is not None:
            try:
                with warnings.catch_warnings():
                    # Ignore future warning with '[[' regex.
                    warnings.simplefilter("ignore")
                    regex = re.compile(self.filter)
                i = 0
                while i < len(items):
                    if not regex.search(items[i][1]):
                        # Filter the list in-place.
                        items.pop(i)
                    else:
                        i += 1
            except re.error:
                self.view.textBuffer.setMessage(u"invalid regex")

    def focus(self):
        #app.log.info('PredictionListController')
        self.onChange()
        app.controller.Controller.focus(self)

    def info(self):
        app.log.info('PredictionListController command set')

    def onChange(self):
        controller = self.view.parent.predictionInputWindow.controller
        self.filter = controller.decodedPath()
        if self.shownList == self.filter:
            return
        self.shownList = self.filter

        inputWindow = self.currentInputWindow()
        self._buildFileList(inputWindow.textBuffer.fullPath)
        if self.items is not None:
            self.view.update(self.items)
        self.filter = None

    def openAltFile(self):
        for row, item in enumerate(self.items):
            if item[3] == 'alt':
                self.openFileOrDir(row)

    def openFileOrDir(self, row):
        if app.config.strict_debug:
            assert isinstance(row, int)
        if self.items is None or len(self.items) == 0:
            return
        bufferManager = self.view.program.bufferManager
        textBuffer, fullPath = self.items[row][:2]
        self.items = None
        self.shownList = None
        if textBuffer is not None:
            textBuffer = bufferManager.getValidTextBuffer(textBuffer)
        else:
            expandedPath = os.path.abspath(os.path.expanduser(fullPath))
            textBuffer = bufferManager.loadTextBuffer(expandedPath)
        inputWindow = self.currentInputWindow()
        inputWindow.setTextBuffer(textBuffer)
        self.changeTo(inputWindow)

    def optionChanged(self, name, value):
        if app.config.strict_debug:
            assert isinstance(name, unicode)
            assert isinstance(value, unicode)
        self.shownList = None
        self.onChange()

    def setFilter(self, listFilter):
        if app.config.strict_debug:
            assert isinstance(listFilter, unicode)
        self.filter = listFilter
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
        #app.log.info('PredictionController')
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
        app.controller.Controller.__init__(self, view,
                                           'PredictionInputController')

    def decodedPath(self):
        if app.config.strict_debug:
            assert self.view.textBuffer is self.textBuffer
        return app.string.pathDecode(self.textBuffer.lines[0])

    def setEncodedPath(self, path):
        if app.config.strict_debug:
            assert isinstance(path, unicode)
            assert self.view.textBuffer is self.textBuffer
        return self.textBuffer.replaceLines((app.string.pathEncode(path),))

    def focus(self):
        #app.log.info('PredictionInputController')
        self.setEncodedPath(u"")
        #self.getNamedWindow('predictionList').controller.setFilter(u"py")
        self.getNamedWindow('predictionList').focus()
        app.controller.Controller.focus(self)

    def info(self):
        app.log.info('PredictionInputController command set')

    def onChange(self):
        #app.log.info('PredictionInputController', self.view.parent.getPath())
        self.getNamedWindow('predictionList').controller.onChange()
        app.controller.Controller.onChange(self)

    def optionChanged(self, name, value):
        if app.config.strict_debug:
            assert isinstance(name, unicode)
            assert isinstance(value, unicode)
        self.getNamedWindow('predictionList').controller.shownList = None

    def passEventToPredictionList(self):
        self.getNamedWindow('predictionList').controller.doCommand(
            self.savedCh, None)

    def openAlternateFile(self):
        app.log.info('PredictionInputController')
        predictionList = self.getNamedWindow('predictionList')
        predictionList.controller.openAltFile()

    def performPrimaryAction(self):
        app.log.info('PredictionInputController')
        predictionList = self.getNamedWindow('predictionList')
        row = predictionList.textBuffer.penRow
        predictionList.controller.openFileOrDir(row)

    def predictionListNext(self):
        predictionList = self.getNamedWindow('predictionList')
        if (predictionList.textBuffer.penRow ==
                predictionList.textBuffer.parser.rowCount() - 1):
            predictionList.textBuffer.cursorMoveTo(0, 0)
        else:
            predictionList.textBuffer.cursorDown()

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
