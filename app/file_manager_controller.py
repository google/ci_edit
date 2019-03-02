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

import app.buffer_file
import app.config
import app.controller
import app.string


class DirectoryListController(app.controller.Controller):
    """Gather and prepare file directory information.
    """

    def __init__(self, view):
        if app.config.strict_debug:
            assert self is not view
        app.controller.Controller.__init__(self, view,
                                           u'DirectoryListController')
        self.filter = None
        self.shownDirectory = None

    def focus(self):
        self.onChange()
        app.controller.Controller.focus(self)

    def info(self):
        app.log.info(u'DirectoryListController command set')

    def onChange(self):
        pathInput = self.view.parent.pathWindow.controller.decodedPath()
        if self.shownDirectory == pathInput:
            return
        self.shownDirectory = pathInput
        appPrefs = self.view.program.prefs
        fullPath, openToLine, openToColumn = app.buffer_file.pathLineColumn(
            pathInput, appPrefs.editor[u"baseDirEnv"])
        fullPath = app.buffer_file.expandFullPath(fullPath)
        dirPath = fullPath
        fileName = ''
        if len(pathInput) > 0 and pathInput[-1] != os.sep:
            dirPath, fileName = os.path.split(fullPath)
            self.view.textBuffer.findRe = re.compile('()^' +
                                                     re.escape(fileName))
        else:
            self.view.textBuffer.findRe = None
        dirPath = dirPath or '.'
        if os.path.isdir(dirPath):
            showDotFiles = appPrefs.editor[u'filesShowDotFiles']
            showSizes = appPrefs.editor[u'filesShowSizes']
            showModified = appPrefs.editor[u'filesShowModifiedDates']

            sortByName = appPrefs.editor[u'filesSortAscendingByName']
            sortBySize = appPrefs.editor[u'filesSortAscendingBySize']
            sortByModifiedDate = appPrefs.editor[
                u'filesSortAscendingByModifiedDate']

            lines = []
            try:
                fileLines = []
                dirContents = os.listdir(dirPath)
                for dirItem in dirContents:
                    if not showDotFiles and dirItem[0] == u'.':
                        continue
                    if self.filter is not None and not dirItem.startswith(
                            self.filter):
                        continue
                    fullPath = os.path.join(dirPath, dirItem)
                    if os.path.isdir(fullPath):
                        dirItem += os.path.sep
                    iSize = None
                    iModified = 0
                    if showSizes and os.path.isfile(fullPath):
                        iSize = os.path.getsize(fullPath)
                    if showModified:
                        iModified = os.path.getmtime(fullPath)
                    # Handle \r and similar characters in file paths.
                    encodedPath = app.string.pathEncode(dirItem)
                    fileLines.append([encodedPath, iSize, iModified, dirItem])
                if sortBySize is not None:
                    # Sort by size.
                    fileLines.sort(reverse=not sortBySize, key=lambda x: x[1])
                elif sortByModifiedDate is not None:
                    # Sort by modification date.
                    fileLines.sort(
                        reverse=not sortByModifiedDate, key=lambda x: x[2])
                else:
                    fileLines.sort(
                        reverse=not sortByName,
                        key=lambda x: unicode.lower(x[0]))
                lines = [
                    u'%-40s  %16s  %24s' %
                    (i[0], u'%s bytes' % (i[1],) if i[1] is not None else u'',
                     time.strftime(u'%c', time.localtime(i[2]))
                     if i[2] else u'') for i in fileLines
                ]
                self.view.contents = [i[3] for i in fileLines]
            except OSError as e:
                lines = [u'Error opening directory.']
                lines.append(unicode(e))
            clip = [u'./', u'../'] + lines
        else:
            clip = [dirPath + u": not found"]
        self.view.textBuffer.replaceLines(tuple(clip))
        self.view.textBuffer.parseScreenMaybe()
        self.view.textBuffer.penRow = 0
        self.view.textBuffer.penCol = 0
        self.view.scrollRow = 0
        self.view.scrollCol = 0
        self.filter = None

    def openFileOrDir(self, row):
        if app.config.strict_debug:
            assert isinstance(row, int)
        pathController = self.view.parent.pathWindow.controller
        path = pathController.decodedPath()
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
            pathController.setEncodedPath(path)
            return
        # If there is a partially typed name in the line, clear it.
        if path[-1:] != os.path.sep:
            path = os.path.dirname(path) + os.path.sep
        pathController.setEncodedPath(path + self.view.contents[row - 2])
        if not os.path.isdir(pathController.decodedPath()):
            self.view.host.controller.performPrimaryAction()

    def optionChanged(self, name, value):
        self.shownDirectory = None
        self.onChange()

    def setFilter(self, listFilter):
        self.filter = listFilter
        self.shownDirectory = None  # Cause a refresh.


class FileManagerController(app.controller.Controller):
    """Create or open files.
    """

    def __init__(self, view):
        app.controller.Controller.__init__(self, view, u'FileManagerController')

    def performPrimaryAction(self):
        self.view.pathWindow.controller.performPrimaryAction()

    def info(self):
        app.log.info(u'FileManagerController command set')

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
        app.controller.Controller.__init__(self, view,
                                           u'FilePathInputController')
        self.primaryActions = {
            u'open': self.doCreateOrOpen,
            u'saveAs': self.doSaveAs,
            u'selectDir': self.doSelectDir,
        }

    def performPrimaryAction(self):
        directoryList = self.getNamedWindow(u'directoryList')
        row = directoryList.textBuffer.penRow
        if row == 0:
            if not os.path.isdir(self.decodedPath()):
                self.primaryActions[self.view.parent.mode]()
        else:
            directoryList.controller.openFileOrDir(row)

    def doCreateOrOpen(self):
        appPrefs = self.view.program.prefs
        path, openToLine, openToColumn = app.buffer_file.pathLineColumn(
            self.decodedPath(), appPrefs.editor[u"baseDirEnv"])
        if len(path) == 0:
            app.log.info('path is empty')
            return
        if not os.access(path, os.R_OK):
            if os.path.isfile(path):
                return
        self.setEncodedPath(u"")
        textBuffer = self.view.program.bufferManager.loadTextBuffer(path)
        if openToLine is not None:
            textBuffer.penRow = openToLine - 1 if openToLine > 0 else 0
        if openToColumn is not None:
            textBuffer.penCol = openToColumn - 1 if openToColumn > 0 else 0
        #assert textBuffer.parser
        inputWindow = self.currentInputWindow()
        inputWindow.setTextBuffer(textBuffer)
        textBuffer.scrollToOptimalScrollPosition()
        self.changeTo(inputWindow)

    def doSaveAs(self):
        path = self.decodedPath()
        inputWindow = self.currentInputWindow()
        tb = inputWindow.textBuffer
        tb.setFilePath(path)
        self.changeTo(inputWindow)
        if not len(path):
            tb.setMessage(u'File not saved (file name was empty).')
            return
        if not tb.isSafeToWrite():
            self.view.changeFocusTo(inputWindow.confirmOverwrite)
            return
        tb.fileWrite()
        self.setEncodedPath(u"")

    def doSelectDir(self):
        # TODO(dschuyler): not yet implemented.
        self.setEncodedPath(u"")
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
            self.setEncodedPath(unicode(path))
        self.getNamedWindow(u'directoryList').focus()
        app.controller.Controller.focus(self)

    def decodedPath(self):
        if app.config.strict_debug:
            assert self.view.textBuffer is self.textBuffer
        return app.string.pathDecode(self.textBuffer.lines[0])

    def setEncodedPath(self, path):
        if app.config.strict_debug:
            assert isinstance(path, unicode)
            assert self.view.textBuffer is self.textBuffer
        return self.textBuffer.replaceLines((app.string.pathEncode(path),))

    def info(self):
        app.log.info(u'FilePathInputController command set')

    def maybeSlash(self, expandedPath):
        if (self.textBuffer.lines[0] and
                self.textBuffer.lines[0][-1] != u'/' and
                os.path.isdir(expandedPath)):
            self.textBuffer.insert(u'/')

    def onChange(self):
        self.getNamedWindow(u'directoryList').controller.onChange()
        app.controller.Controller.onChange(self)

    def optionChanged(self, name, value):
        self.getNamedWindow(u'directoryList').controller.shownDirectory = None

    def passEventToDirectoryList(self):
        self.getNamedWindow(u'directoryList').controller.doCommand(
            self.savedCh, None)

    def tabCompleteExtend(self):
        """Extend the selection to match characters in common."""
        decodedPath = self.decodedPath()
        expandedPath = os.path.expandvars(os.path.expanduser(decodedPath))
        dirPath, fileName = os.path.split(expandedPath)
        expandedDir = dirPath or u'.'
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
            self.setEncodedPath(decodedPath + matches[0][len(fileName):])
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
        self.setEncodedPath(decodedPath + matches[0][len(fileName):prefixLen])
        if expandedPath == os.path.expandvars(
                os.path.expanduser(self.decodedPath())):
            # No further expansion found.
            self.getNamedWindow(u'directoryList').controller.setFilter(fileName)
        self.onChange()
