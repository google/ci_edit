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
        fullPath, openToRow, openToColumn = app.buffer_file.pathRowColumn(
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
                    fileLines.sort(reverse=not sortBySize,
                        key=lambda x: x[1] if x[1] is not None else -1)
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
        self.view.textBuffer.goalCol = 0
        self.view.scrollRow = 0
        self.view.scrollCol = 0
        self.filter = None

    def performOpen(self):
        self.openFileOrDir(self.textBuffer.penRow)

    def openFileOrDir(self, row):
        if app.config.strict_debug:
            assert isinstance(row, int)
        path = self.pathForRow(row)
        # Clear the shown directory to trigger a refresh.
        self.shownDirectory = None
        self.view.parent.pathWindow.controller.setEncodedPath(path)
        self.view.host.controller.performPrimaryAction()

    def currentDirectory(self):
        pathController = self.view.parent.pathWindow.controller
        path = pathController.decodedPath()
        if len(path) > 0 and path[-1] != os.path.sep:
            path = os.path.dirname(path)
            # Test that path is non-empty and there's more than just a '/'.
            if len(path) > len(os.path.sep):
                path += os.path.sep
        if app.config.strict_debug:
            assert isinstance(path, unicode)
        return path

    def passDefaultToPathInput(self, ch, meta):
        pathInput = self.findAndChangeTo(u'pathWindow')
        pathInput.controller.doCommand(ch, meta)

    def pathForRow(self, row):
        if app.config.strict_debug:
            assert isinstance(row, int)
            assert row >= 0, row
        path = self.currentDirectory()
        if row == 0:
            return path + u"./"
        elif row == 1:
            return path + u"../"
        return path + self.view.contents[row - 2]

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
        path = self.decodedPath()
        if len(path) == 0:
            app.log.info('path is empty')
            return
        if path.endswith(u"/./"):
            #self.shownDirectory = None
            self.setEncodedPath(path[:-2])
            return
        if path.endswith(u"/../"):
            path = os.path.dirname(path[:-4])
            if len(path) > len(os.path.sep):
                path += os.path.sep
            self.setEncodedPath(path)
            return

        self.primaryActions[self.view.parent.mode]()

    def doCreateOrOpen(self):
        decodedPath = self.decodedPath()
        if os.path.isdir(decodedPath):
            app.log.info("is dir", repr(decodedPath))
            return
        appPrefs = self.view.program.prefs
        path, openToRow, openToColumn = app.buffer_file.pathRowColumn(
            decodedPath, appPrefs.editor[u"baseDirEnv"])
        if not os.access(path, os.R_OK):
            if os.path.isfile(path):
                app.log.info(u"File not readable.")
                return
        self.setEncodedPath(u"")
        textBuffer = self.view.program.bufferManager.loadTextBuffer(path)
        if textBuffer is None:
            return
        if openToRow is not None:
            textBuffer.penRow = openToRow if openToRow > 0 else 0
        if openToColumn is not None:
            textBuffer.penCol = openToColumn if openToColumn > 0 else 0
            textBuffer.goalCol = textBuffer.penCol
        #assert textBuffer.parser
        inputWindow = self.currentInputWindow()
        inputWindow.setTextBuffer(textBuffer)
        textBuffer.scrollToOptimalScrollPosition()
        self.changeTo(inputWindow)

    def doSaveAs(self):
        path = self.decodedPath()
        if os.path.isdir(path):
            return
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

    def decodedPath(self):
        if app.config.strict_debug:
            assert self.view.textBuffer is self.textBuffer
        return app.string.pathDecode(self.textBuffer.lines[0])

    def setEncodedPath(self, path):
        if app.config.strict_debug:
            assert isinstance(path, unicode)
            assert self.view.textBuffer is self.textBuffer
        self.textBuffer.replaceLines((app.string.pathEncode(path),))
        self.textBuffer.parseDocument()

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
        directoryList = self.findAndChangeTo(u'directoryList')
        directoryList.controller.doCommand(self.savedCh, None)

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
