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
"""Manager for key bindings."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses
import curses.ascii

import app.config
import app.curses_util
import app.log
import app.selectable

#import app.window


class Controller:
    """A Controller is a keyboard mapping from keyboard/mouse events to editor
    commands."""

    def __init__(self, view, name):
        if app.config.strict_debug:
            assert issubclass(self.__class__, Controller)
            assert issubclass(view.__class__, app.window.Window)
        self.view = view
        self.commandDefault = None
        self.commandSet = None
        self.textBuffer = None
        self.name = name

    def parentController(self):
        view = self.view.parent
        while view is not None:
            if view.controller is not None:
                return view.controller
            view = view.parent

    def changeToConfirmClose(self):
        self.findAndChangeTo('confirmClose')

    def changeToConfirmOverwrite(self):
        self.findAndChangeTo('confirmOverwrite')

    def changeToFileManagerWindow(self, *args):
        self.findAndChangeTo('fileManagerWindow')

    def changeToConfirmQuit(self):
        self.findAndChangeTo('interactiveQuit')

    def changeToHostWindow(self, *args):
        host = self.getNamedWindow('inputWindow')
        if app.config.strict_debug:
            assert issubclass(self.view.__class__, app.window.Window), self.view
            assert issubclass(host.__class__, app.window.Window), host
        self.view.changeFocusTo(host)

    def changeToInputWindow(self, *args):
        self.findAndChangeTo('inputWindow')

    def changeToFind(self):
        self.findAndChangeTo('interactiveFind')

    def changeToFindPrior(self):
        curses.ungetch(self.savedCh)
        self.findAndChangeTo('interactiveFind')

    def changeToGoto(self):
        self.findAndChangeTo('interactiveGoto')

    def changeToPaletteWindow(self):
        self.findAndChangeTo('paletteWindow')

    def changeToPopup(self):
        self.findAndChangeTo('popupWindow')

    def changeToPrediction(self):
        self.findAndChangeTo('predictionWindow')
        #self.findAndChangeTo('interactivePrediction')

    def changeToPrompt(self):
        self.findAndChangeTo('interactivePrompt')

    def changeToQuit(self):
        self.findAndChangeTo('interactiveQuit')

    def changeToSaveAs(self):
        view = self.getNamedWindow('fileManagerWindow')
        view.setMode('saveAs')
        view.bringToFront()
        view.changeFocusTo(view)

    def createNewTextBuffer(self):
        bufferManager = self.view.program.bufferManager
        self.view.setTextBuffer(bufferManager.newTextBuffer())

    def doCommand(self, ch, meta):
        # Check the commandSet for the input with both its string and integer
        # representation.
        self.savedCh = ch

        cmd = (self.commandSet.get(ch) or
               self.commandSet.get(app.curses_util.cursesKeyName(ch)))

        if cmd:
            cmd()
        else:
            self.commandDefault(ch, meta)
        self.textBuffer.compoundChangePush()

    def getNamedWindow(self, windowName):
        view = self.view
        while view is not None:
            if hasattr(view, windowName):
                return getattr(view, windowName)
            view = view.parent
        app.log.fatal(windowName + ' not found')
        return None

    def currentInputWindow(self):
        return self.getNamedWindow('inputWindow')

    def findAndChangeTo(self, windowName):
        window = self.getNamedWindow(windowName)
        window.bringToFront()
        self.view.changeFocusTo(window)
        return window

    def changeTo(self, window):
        window.bringToFront()
        self.view.changeFocusTo(window)

    def focus(self):
        pass

    def confirmationPromptFinish(self, *args):
        window = self.getNamedWindow('inputWindow')
        window.userIntent = 'edit'
        window.bringToFront()
        self.view.changeFocusTo(window)

    def __closeHostFile(self, host):
        """Close the current file and switch to another or create an empty
        file."""
        bufferManager = host.program.bufferManager
        bufferManager.closeTextBuffer(host.textBuffer)
        host.userIntent = 'edit'
        tb = bufferManager.getUnsavedBuffer()
        if not tb:
            tb = bufferManager.nextBuffer()
            if not tb:
                tb = bufferManager.newTextBuffer()
        host.setTextBuffer(tb)

    def closeFile(self):
        app.log.info()
        host = self.getNamedWindow('inputWindow')
        self.__closeHostFile(host)
        self.confirmationPromptFinish()

    def closeOrConfirmClose(self):
        """If the file is clean, close it. If it is dirty, prompt the user
        about whether to lose unsaved changes."""
        host = self.getNamedWindow('inputWindow')
        tb = host.textBuffer
        if not tb.isDirty():
            self.__closeHostFile(host)
            return
        if host.userIntent == 'edit':
            host.userIntent = 'close'
        self.changeToConfirmClose()

    def initiateClose(self):
        """Called from input window controller."""
        self.view.userIntent = 'close'
        tb = self.view.textBuffer
        if not tb.isDirty():
            self.__closeHostFile(self.view)
            return
        self.view.changeFocusTo(self.view.confirmClose)

    def initiateQuit(self):
        """Called from input window controller."""
        self.view.userIntent = 'quit'
        tb = self.view.textBuffer
        if tb.isDirty():
            self.view.changeFocusTo(self.view.interactiveQuit)
            return
        bufferManager = self.view.program.bufferManager
        tb = bufferManager.getUnsavedBuffer()
        if tb:
            self.view.setTextBuffer(tb)
            self.view.changeFocusTo(self.view.interactiveQuit)
            return
        bufferManager.debugLog()
        self.view.quitNow()

    def initiateSave(self):
        """Called from input window controller."""
        self.view.userIntent = 'edit'
        tb = self.view.textBuffer
        if tb.fullPath:
            if not tb.isSafeToWrite():
                self.view.changeFocusTo(self.view.confirmOverwrite)
                return
            tb.fileWrite()
            return
        self.changeToSaveAs()

    def overwriteHostFile(self):
        """Close the current file and switch to another or create an empty
        file.
        """
        host = self.getNamedWindow('inputWindow')
        host.textBuffer.fileWrite()
        if host.userIntent == 'quit':
            self.quitOrSwitchToConfirmQuit()
            return
        if host.userIntent == 'close':
            self.__closeHostFile(host)
        self.changeToHostWindow()

    def nextFocusableWindow(self):
        window = self.view.nextFocusableWindow(self.view)
        if window is not None:
            self.view.changeFocusTo(window)
        return window is not None

    def priorFocusableWindow(self):
        window = self.view.priorFocusableWindow(self.view)
        if window is not None:
            self.view.changeFocusTo(window)
        return window is not None

    def writeOrConfirmOverwrite(self):
        """Ask whether the file should be overwritten."""
        app.log.debug()
        host = self.getNamedWindow('inputWindow')
        tb = host.textBuffer
        if not tb.isSafeToWrite():
            self.changeToConfirmOverwrite()
            return
        tb.fileWrite()
        # TODO(dschuyler): Is there a deeper issue here that necessitates saving
        # the message? Does this only need to wrap the changeToHostWindow()?
        # Store the save message so it is not overwritten.
        saveMessage = tb.message
        if host.userIntent == 'quit':
            self.quitOrSwitchToConfirmQuit()
            return
        if host.userIntent == 'close':
            self.__closeHostFile(host)
        self.changeToHostWindow()
        tb.message = saveMessage  # Restore the save message.

    def quitOrSwitchToConfirmQuit(self):
        app.log.debug(self, self.view)
        host = self.getNamedWindow('inputWindow')
        tb = host.textBuffer
        host.userIntent = 'quit'
        if tb.isDirty():
            self.changeToConfirmQuit()
            return
        bufferManager = self.view.program.bufferManager
        tb = bufferManager.getUnsavedBuffer()
        if tb:
            host.setTextBuffer(tb)
            self.changeToConfirmQuit()
            return
        bufferManager.debugLog()
        host.quitNow()

    def saveOrChangeToSaveAs(self):
        app.log.debug()
        host = self.getNamedWindow('inputWindow')
        if app.config.strict_debug:
            assert issubclass(self.__class__, Controller), self
            assert issubclass(self.view.__class__, app.window.Window), self
            assert issubclass(host.__class__, app.window.Window), self
            assert self.view.textBuffer is self.textBuffer
            assert self.view.textBuffer is not host.textBuffer
        if host.textBuffer.fullPath:
            self.writeOrConfirmOverwrite()
            return
        self.changeToSaveAs()

    def onChange(self):
        pass

    def saveEventChangeToHostWindow(self, *args):
        curses.ungetch(self.savedCh)
        host = self.getNamedWindow('inputWindow')
        host.bringToFront()
        self.view.changeFocusTo(host)

    def setTextBuffer(self, textBuffer):
        if app.config.strict_debug:
            assert issubclass(textBuffer.__class__,
                              app.text_buffer.TextBuffer), textBuffer
            assert self.view.textBuffer is textBuffer
        self.textBuffer = textBuffer

    def unfocus(self):
        pass


class MainController:
    """The different keyboard mappings are different controllers. This class
    manages a collection of keyboard mappings and allows the user to switch
    between them."""

    def __init__(self, view):
        if app.config.strict_debug:
            assert issubclass(view.__class__, app.window.Window)
        self.view = view
        self.commandDefault = None
        self.commandSet = None
        self.controllers = {}
        self.controller = None

    def add(self, controller):
        self.controllers[controller.name] = controller
        self.controller = controller

    def currentInputWindow(self):
        return self.controller.currentInputWindow()

    def doCommand(self, ch, meta):
        self.controller.doCommand(ch, meta)

    def focus(self):
        app.log.info('MainController.focus')
        self.controller.focus()
        if 0:
            self.commandDefault = self.controller.commandDefault
            commandSet = self.controller.commandSet.copy()
            commandSet.update({
                app.curses_util.KEY_F2: self.nextController,
            })
            self.controller.commandSet = commandSet

    def onChange(self):
        tb = self.view.textBuffer
        if tb.message is None and tb.selectionMode != app.selectable.kSelectionNone:
            charCount, lineCount = tb.countSelected()
            tb.setMessage(
                u'%d characters (%d lines) selected' % (charCount, lineCount))
        self.controller.onChange()

    def nextController(self):
        app.log.info('nextController')
        if 0:
            if self.controller is self.controllers['cuaPlus']:
                app.log.info('MainController.nextController cua')
                self.controller = self.controllers['cua']
            elif self.controller is self.controllers['cua']:
                app.log.info('MainController.nextController emacs')
                self.controller = self.controllers['emacs']
            elif self.controller is self.controllers['emacs']:
                app.log.info('MainController.nextController vi')
                self.controller = self.controllers['vi']
            else:
                app.log.info('MainController.nextController cua')
                self.controller = self.controllers['cua']
            self.controller.setTextBuffer(self.textBuffer)
            self.focus()

    def setTextBuffer(self, textBuffer):
        app.log.info('MainController.setTextBuffer', self.controller)
        if app.config.strict_debug:
            assert issubclass(textBuffer.__class__, app.text_buffer.TextBuffer)
        self.textBuffer = textBuffer
        self.controller.setTextBuffer(textBuffer)

    def unfocus(self):
        self.controller.unfocus()
