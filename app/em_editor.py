# Copyright 2016 Google Inc.
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
"""Key bindings for the emacs-like editor."""

# For Python 2to3 support.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses
import curses.ascii
import os
import re

from app.curses_util import *
import app.controller
import app.log
import app.text_buffer


def parseInt(str):
    i = 0
    k = 0
    if len(str) > i and str[i] in ('+', '-'):
        i += 1
    k = i
    while len(str) > k and str[k].isdigit():
        k += 1
    if k > i:
        return int(str[:k])
    return 0


def test_parseInt():
    assert parseInt('0') == 0
    assert parseInt('0e') == 0
    assert parseInt('qwee') == 0
    assert parseInt('10') == 10
    assert parseInt('+10') == 10
    assert parseInt('-10') == -10
    assert parseInt('--10') == 0
    assert parseInt('--10') == 0


class EditText(app.controller.Controller):
    """An EditText is a base class for one-line controllers."""

    def __init__(self, view):
        app.controller.Controller.__init__(self, view, 'EditText')
        self.document = None

    def setTextBuffer(self, textBuffer):
        textBuffer.lines = [u""]
        self.commandSet = {
            KEY_F1: self.info,
            CTRL_A: textBuffer.selectionAll,
            CTRL_C: textBuffer.editCopy,
            CTRL_H: textBuffer.backspace,
            KEY_BACKSPACE1: textBuffer.backspace,
            KEY_BACKSPACE2: textBuffer.backspace,
            KEY_BACKSPACE3: textBuffer.backspace,
            CTRL_Q: self.prg.quit,
            CTRL_S: self.saveDocument,
            CTRL_V: textBuffer.editPaste,
            CTRL_X: textBuffer.editCut,
            CTRL_Y: textBuffer.redo,
            CTRL_Z: textBuffer.undo,

            # KEY_DOWN: textBuffer.cursorDown,
            KEY_LEFT: textBuffer.cursorLeft,
            KEY_RIGHT: textBuffer.cursorRight,
            # KEY_UP: textBuffer.cursorUp,
        }

    def focus(self):
        app.log.info('EditText.focus', repr(self))
        self.commandDefault = self.textBuffer.insertPrintable
        self.commandSet = self.commandSet

    def info(self):
        app.log.info('EditText command set')

    def saveDocument(self):
        app.log.info('saveDocument', self.document)
        if self.document and self.document.textBuffer:
            self.document.textBuffer.fileWrite()

    def unfocus(self):
        pass


class InteractiveOpener(EditText):
    """Open a file to edit."""

    def __init__(self, prg, view, textBuffer):
        EditText.__init__(self, prg, view, textBuffer)
        self.document = view.host
        app.log.info('xxxxx', self.document)
        commandSet = self.commandSet.copy()
        commandSet.update({
            KEY_ESCAPE: self.changeToInputWindow,
            KEY_F1: self.info,
            CTRL_I: self.tabCompleteExtend,
            CTRL_J: self.createOrOpen,
            CTRL_N: self.createOrOpen,
            CTRL_O: self.createOrOpen,
            CTRL_Q: self.prg.quit,
        })
        self.commandSet = commandSet

    def focus(self):
        app.log.info('InteractiveOpener.focus')
        EditText.focus(self)
        # Create a new text buffer to display dir listing.
        self.view.host.setTextBuffer(text_buffer.TextBuffer(self.prg))

    def info(self):
        app.log.info('InteractiveOpener command set')

    def createOrOpen(self):
        app.log.info('createOrOpen')
        expandedPath = os.path.abspath(
            os.path.expanduser(self.textBuffer.lines[0]))
        if not os.path.isdir(expandedPath):
            self.view.host.setTextBuffer(
                self.prg.bufferManager.loadTextBuffer(expandedPath),
                self.view.host)
        self.changeToInputWindow()

    def maybeSlash(self, expandedPath):
        if (self.textBuffer.lines[0] and self.textBuffer.lines[0][-1] != '/' and
                os.path.isdir(expandedPath)):
            self.textBuffer.insert('/')

    def tabCompleteFirst(self):
        """Find the first file that starts with the pattern."""
        dirPath, fileName = os.path.split(self.lines[0])
        foundOnce = ''
        for i in os.listdir(
                os.path.expandvars(os.path.expanduser(dirPath)) or '.'):
            if i.startswith(fileName):
                if foundOnce:
                    # Found more than one match.
                    return
                fileName = os.path.join(dirPath, i)
                if os.path.isdir(fileName):
                    fileName += '/'
                self.lines[0] = fileName
                self.onChange()
                return

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
                app.log.info('not', i)
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

    def setFileName(self, path):
        self.textBuffer.lines = [path]
        self.textBuffer.penCol = len(path)
        self.textBuffer.goalCol = self.textBuffer.penCol

    def onChange(self):
        path = os.path.expanduser(os.path.expandvars(self.textBuffer.lines[0]))
        dirPath, fileName = os.path.split(path)
        dirPath = dirPath or '.'
        app.log.info('O.onChange', dirPath, fileName)
        if os.path.isdir(dirPath):
            lines = []
            for i in os.listdir(dirPath):
                if i.startswith(fileName):
                    lines.append(i)
            if len(lines) == 1 and os.path.isfile(
                    os.path.join(dirPath, fileName)):
                self.view.host.setTextBuffer(
                    self.view.program.bufferManager.loadTextBuffer(
                        os.path.join(dirPath, fileName), self.view.host))
            else:
                self.view.host.textBuffer.lines = [
                    os.path.abspath(os.path.expanduser(dirPath)) + ":"
                ] + lines
        else:
            self.view.host.textBuffer.lines = [
                os.path.abspath(os.path.expanduser(dirPath)) + ": not found"
            ]


class InteractiveFind(EditText):
    """Find text within the current document."""

    def __init__(self, prg, view, textBuffer):
        EditText.__init__(self, prg, view, textBuffer)
        self.document = view.host
        self.commandSet.update({
            KEY_ESCAPE: self.changeToInputWindow,
            KEY_F1: self.info,
            CTRL_F: self.findNext,
            CTRL_J: self.changeToInputWindow,
            CTRL_R: self.findPrior,
            #CTRL_S: self.replacementTextEdit,
            KEY_DOWN: self.findNext,
            KEY_MOUSE: self.saveEventChangeToHostWindow,
            KEY_UP: self.findPrior,
        })
        self.height = 1

    def findNext(self):
        self.findCmd = self.document.textBuffer.findNext

    def findPrior(self):
        self.findCmd = self.document.textBuffer.findPrior

    def focus(self):
        #self.document.statusLine.hide()
        #self.document.resizeBy(-self.height, 0)
        #self.view.host.moveBy(-self.height, 0)
        #self.view.host.resizeBy(self.height-1, 0)
        EditText.focus(self)
        self.findCmd = self.document.textBuffer.find
        selection = self.document.textBuffer.getSelectedText()
        if selection:
            self.textBuffer.selectionAll()
            self.textBuffer.insertLines(selection)
        self.textBuffer.selectionAll()
        app.log.info('find tb', self.textBuffer.penCol)

    def info(self):
        app.log.info('InteractiveFind command set')

    def onChange(self):
        app.log.info('InteractiveFind.onChange')
        searchFor = self.textBuffer.lines[0]
        try:
            self.findCmd(searchFor)
        except re.error as e:
            self.error = e.message
        self.findCmd = self.document.textBuffer.find

    #def replacementTextEdit(self):
    #  pass

    def unfocus(self):
        app.log.info('unfocus Find')
        #self.hide()


class InteractiveGoto(EditText):
    """Jump to a particular line number."""

    def __init__(self, prg, view, textBuffer):
        EditText.__init__(self, prg, view, textBuffer)
        self.document = view.host
        commandSet = self.commandSet.copy()
        commandSet.update({
            KEY_ESCAPE: self.changeToInputWindow,
            KEY_F1: self.info,
            CTRL_J: self.changeToInputWindow,
            KEY_MOUSE: self.saveEventChangeToHostWindow,
            ord('b'): self.gotoBottom,
            ord('h'): self.gotoHalfway,
            ord('t'): self.gotoTop,
        })
        self.commandSet = commandSet

    def focus(self):
        app.log.info('InteractiveGoto.focus')
        self.textBuffer.selectionAll()
        self.textBuffer.insert(str(self.document.textBuffer.penRow + 1))
        self.textBuffer.selectionAll()
        EditText.focus(self)

    def info(self):
        app.log.info('InteractiveGoto command set')

    def gotoBottom(self):
        self.cursorMoveTo(len(self.document.textBuffer.lines), 0)
        self.changeToInputWindow()

    def gotoHalfway(self):
        self.cursorMoveTo(len(self.document.textBuffer.lines) // 2 + 1, 0)
        self.changeToInputWindow()

    def gotoTop(self):
        self.cursorMoveTo(1, 0)
        self.changeToInputWindow()

    def cursorMoveTo(self, row, col):
        textBuffer = self.document.textBuffer
        penRow = min(max(row - 1, 0), len(textBuffer.lines) - 1)
        app.log.info('cursorMoveTo row', row, penRow)
        textBuffer.cursorMove(penRow - textBuffer.penRow,
                              col - textBuffer.penCol, col - textBuffer.goalCol)

    def onChange(self):
        gotoLine = 0
        line = self.textBuffer.parser.rowText(0)
        gotoLine, gotoCol = (line.split(',') + ['0', '0'])[:2]
        self.cursorMoveTo(parseInt(gotoLine), parseInt(gotoCol))

    #def unfocus(self):
    #  self.hide()


class CiEdit(app.controller.Controller):
    """Keyboard mappings for ci."""

    def __init__(self, prg, textBuffer):
        app.controller.Controller.__init__(self, prg, None, 'CiEdit')
        app.log.info('CiEdit.__init__')
        self.textBuffer = textBuffer
        self.commandSet_Main = {
            CTRL_SPACE: self.switchToCommandSetCmd,
            CTRL_A: textBuffer.cursorStartOfLine,
            CTRL_B: textBuffer.cursorLeft,
            KEY_LEFT: self.cursorLeft,
            CTRL_C: self.editCopy,
            CTRL_D: self.delete,
            CTRL_E: self.cursorEndOfLine,
            CTRL_F: self.cursorRight,
            KEY_RIGHT: self.cursorRight,
            CTRL_H: self.backspace,
            KEY_BACKSPACE1: self.backspace,
            KEY_BACKSPACE2: self.backspace,
            KEY_BACKSPACE3: self.backspace,
            CTRL_J: self.carriageReturn,
            CTRL_K: self.deleteToEndOfLine,
            CTRL_L: self.win.refresh,
            CTRL_N: self.cursorDown,
            KEY_DOWN: self.cursorDown,
            CTRL_O: self.splitLine,
            CTRL_P: self.cursorUp,
            KEY_UP: self.cursorUp,
            CTRL_V: self.editPaste,
            CTRL_X: self.editCut,
            CTRL_Y: self.redo,
            CTRL_Z: self.undo,
            CTRL_BACKSLASH: self.changeToCmdMode,
            #ord('/'): self.switchToCommandSetCmd,
        }

        self.commandSet_Cmd = {
            ord('a'): self.switchToCommandSetApplication,
            ord('f'): self.switchToCommandSetFile,
            ord('s'): self.switchToCommandSetSelect,
            ord(';'): self.switchToCommandSetMain,
            ord("'"): self.markerPlace,
        }

        self.commandSet_Application = {
            ord('q'): self.prg.quit,
            ord('t'): self.test,
            ord('w'): self.fileWrite,
            ord(';'): self.switchToCommandSetMain,
        }

        self.commandSet_File = {
            ord('o'): self.switchToCommandSetFileOpen,
            ord('w'): self.fileWrite,
            ord(';'): self.switchToCommandSetMain,
        }

        self.commandSet_FileOpen = {
            ord(';'): self.switchToCommandSetMain,
        }

        self.commandSet_Select = {
            ord('a'): self.selectionAll,
            ord('b'): self.selectionBlock,
            ord('c'): self.selectionCharacter,
            ord('l'): self.selectionLine,
            ord('x'): self.selectionNone,
            ord(';'): self.switchToCommandSetMain,
        }

        self.commandDefault = self.insertPrintable
        self.commandSet = self.commandSet_Main

    def switchToCommandSetMain(self, ignored=1):
        self.log('ci main', repr(self.prg))
        self.commandDefault = self.insertPrintable
        self.commandSet = self.commandSet_Main

    def switchToCommandSetCmd(self):
        self.log('ci cmd')
        self.commandDefault = self.textBuffer.noOp
        self.commandSet = self.commandSet_Cmd

    def switchToCommandSetApplication(self):
        self.log('ci application')
        self.commandDefault = self.textBuffer.noOp
        self.commandSet = self.commandSet_Application

    def switchToCommandSetFile(self):
        self.commandDefault = self.textBuffer.noOp
        self.commandSet = self.commandSet_File

    def switchToCommandSetFileOpen(self):
        self.log('switchToCommandSetFileOpen')
        self.commandDefault = self.pathInsertPrintable
        self.commandSet = self.commandSet_FileOpen

    def switchToMainAndDoCommand(self, ch):
        self.log('switchToMainAndDoCommand')
        self.switchToCommandSetMain()
        self.doCommand(ch)

    def switchToCommandSetSelect(self):
        self.log('ci select')
        self.commandDefault = self.SwitchToMainAndDoCommand
        self.commandSet = self.commandSet_Select
        self.selectionCharacter()


class EmacsEdit(app.controller.Controller):
    """Emacs is a common Unix based text editor. This keyboard mapping is
    similar to basic Emacs commands."""

    def __init__(self, view):
        app.controller.Controller.__init__(self, view, 'EditText')

    def focus(self):
        app.log.info('EmacsEdit.focus')
        self.commandDefault = self.textBuffer.insertPrintable
        self.commandSet = self.commandSet_Main

    def onChange(self):
        pass

    def setTextBuffer(self, textBuffer):
        app.log.info('EmacsEdit.setTextBuffer')
        self.textBuffer = textBuffer
        self.commandSet_Main = {
            KEY_F1: self.info,
            CTRL_A: textBuffer.cursorStartOfLine,
            CTRL_B: textBuffer.cursorLeft,
            KEY_LEFT: textBuffer.cursorLeft,
            CTRL_D: textBuffer.delete,
            CTRL_E: textBuffer.cursorEndOfLine,
            CTRL_F: textBuffer.cursorRight,
            KEY_RIGHT: textBuffer.cursorRight,

            # CTRL_H: textBuffer.backspace,
            KEY_BACKSPACE1: textBuffer.backspace,
            KEY_BACKSPACE2: textBuffer.backspace,
            KEY_BACKSPACE3: textBuffer.backspace,
            CTRL_J: textBuffer.carriageReturn,
            CTRL_K: textBuffer.deleteToEndOfLine,
            CTRL_L: self.view.host.refresh,
            CTRL_N: textBuffer.cursorDown,
            KEY_DOWN: textBuffer.cursorDown,
            CTRL_O: textBuffer.splitLine,
            CTRL_P: textBuffer.cursorUp,
            KEY_UP: textBuffer.cursorUp,
            CTRL_X: self.switchToCommandSetX,
            CTRL_Y: textBuffer.redo,
            CTRL_Z: textBuffer.undo,
        }
        self.commandSet = self.commandSet_Main

        self.commandSet_X = {
            CTRL_C: self.prg.quit,
        }

    def info(self):
        app.log.info('EmacsEdit Command set main')
        app.log.info(repr(self))

    def switchToCommandSetX(self):
        self.log('emacs x')
        self.commandSet = self.commandSet_X
