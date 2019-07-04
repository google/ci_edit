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
"""Key bindings for the cua-like editor."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses

from app.curses_util import *
import app.controller
import app.editor
import app.file_manager_controller
import app.interactive_prompt
import app.prediction_controller
import app.text_buffer


def initCommandSet(controller, textBuffer):
    """The basic command set includes line editing controls."""
    return {
        CTRL_A: textBuffer.selectionAll,
        CTRL_C: textBuffer.editCopy,
        #CTRL_H: textBuffer.backspace,
        CTRL_L: textBuffer.cursorSelectLine,
        CTRL_Q: controller.quitOrSwitchToConfirmQuit,
        CTRL_S: controller.saveOrChangeToSaveAs,
        CTRL_V: textBuffer.editPaste,
        CTRL_W: controller.closeOrConfirmClose,
        CTRL_X: textBuffer.editCut,
        CTRL_Y: textBuffer.editRedo,
        CTRL_Z: textBuffer.editUndo,
        KEY_BACKSPACE1: textBuffer.backspace,
        KEY_BACKSPACE2: textBuffer.backspace,
        KEY_BACKSPACE3: textBuffer.backspace,
        CTRL_BACKSPACE: textBuffer.backspaceWord,
        KEY_DELETE: textBuffer.delete,
        KEY_HOME: textBuffer.cursorStartOfLine,
        KEY_END: textBuffer.cursorEndOfLine,
        KEY_SHOME: textBuffer.cursorSelectToStartOfLine,
        KEY_SEND: textBuffer.cursorSelectToEndOfLine,

        # KEY_DOWN: textBuffer.cursorDown,
        KEY_LEFT: textBuffer.cursorLeft,
        KEY_RIGHT: textBuffer.cursorRight,
        # KEY_UP: textBuffer.cursorUp,
        KEY_ALT_LEFT: textBuffer.cursorMoveSubwordLeft,
        KEY_ALT_SHIFT_LEFT: textBuffer.cursorSelectSubwordLeft,
        KEY_ALT_RIGHT: textBuffer.cursorMoveSubwordRight,
        KEY_ALT_SHIFT_RIGHT: textBuffer.cursorSelectSubwordRight,
        KEY_CTRL_LEFT: textBuffer.cursorMoveWordLeft,
        KEY_CTRL_SHIFT_LEFT: textBuffer.cursorSelectWordLeft,
        KEY_CTRL_RIGHT: textBuffer.cursorMoveWordRight,
        KEY_CTRL_SHIFT_RIGHT: textBuffer.cursorSelectWordRight,
    }


def mainWindowCommands(controller, textBuffer):
    """The command set for a window (rather than a single line)."""
    commands = initCommandSet(controller, textBuffer).copy()
    commands.update({
        KEY_ESCAPE:
        textBuffer.normalize,
        KEY_F1:
        controller.info,
        KEY_BTAB:
        textBuffer.unindent,
        KEY_PAGE_UP:
        textBuffer.cursorSelectNonePageUp,
        KEY_PAGE_DOWN:
        textBuffer.cursorSelectNonePageDown,
        KEY_SHIFT_PAGE_UP:
        textBuffer.cursorSelectCharacterPageUp,
        KEY_SHIFT_PAGE_DOWN:
        textBuffer.cursorSelectCharacterPageDown,
        KEY_ALT_SHIFT_PAGE_UP:
        textBuffer.cursorSelectBlockPageUp,
        KEY_ALT_SHIFT_PAGE_DOWN:
        textBuffer.cursorSelectBlockPageDown,
        #CTRL_B:
        #textBuffer.jumpToMatchingBracket,
        CTRL_F:
        controller.changeToFind,
        CTRL_G:
        controller.changeToGoto,
        CTRL_I:
        textBuffer.indent,
        CTRL_J:
        textBuffer.carriageReturn,
        CTRL_N:
        controller.createNewTextBuffer,
        CTRL_O:
        controller.changeToFileManagerWindow,
        CTRL_Q:
        controller.initiateQuit,
        CTRL_R:
        controller.changeToFindPrior,
        CTRL_S:
        controller.initiateSave,
        CTRL_W:
        controller.initiateClose,
        KEY_DOWN:
        textBuffer.cursorDown,
        KEY_SHIFT_LEFT:
        textBuffer.cursorSelectLeft,
        KEY_SHIFT_RIGHT:
        textBuffer.cursorSelectRight,
        KEY_UP:
        textBuffer.cursorUp,
        KEY_SHIFT_DOWN:
        textBuffer.cursorSelectDown,
        KEY_SHIFT_UP:
        textBuffer.cursorSelectUp,
        KEY_CTRL_DOWN:
        textBuffer.cursorDownScroll,
        KEY_CTRL_SHIFT_DOWN:
        textBuffer.cursorSelectDownScroll,
        KEY_CTRL_UP:
        textBuffer.cursorUpScroll,
        KEY_CTRL_SHIFT_UP:
        textBuffer.cursorSelectUpScroll,
    })
    return commands


class ConfirmClose(app.controller.Controller):
    """Ask about closing a file with unsaved changes."""

    def __init__(self, view):
        app.controller.Controller.__init__(self, view, 'confirmClose')

    def setTextBuffer(self, textBuffer):
        app.controller.Controller.setTextBuffer(self, textBuffer)
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            ord('n'): self.closeFile,
            ord('N'): self.closeFile,
            ord('y'): self.saveOrChangeToSaveAs,
            ord('Y'): self.saveOrChangeToSaveAs,
        })
        self.commandSet = commandSet
        self.commandDefault = self.confirmationPromptFinish


class ConfirmOverwrite(app.controller.Controller):
    """Ask about writing over an existing file."""

    def __init__(self, view):
        app.controller.Controller.__init__(self, view, 'confirmOverwrite')

    def setTextBuffer(self, textBuffer):
        app.controller.Controller.setTextBuffer(self, textBuffer)
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            ord('y'): self.overwriteHostFile,
            ord('Y'): self.overwriteHostFile,
        })
        self.commandSet = commandSet
        self.commandDefault = self.confirmationPromptFinish


class InteractiveFind(app.editor.InteractiveFind):

    def __init__(self, view):
        app.editor.InteractiveFind.__init__(self, view)

    def setTextBuffer(self, textBuffer):
        pass


class InteractiveFindInput(app.editor.InteractiveFindInput):
    """Find text within the current document."""

    def __init__(self, view):
        app.editor.InteractiveFindInput.__init__(self, view)

    def focus(self):
        if self.view.parent.expanded:
            self.view.parent.parent.textBuffer.setMessage(
                'Press ctrl+g to find again; ctrl+r find prior.')
        else:
            self.view.parent.parent.textBuffer.setMessage(
                'Press tab for more options; ctrl+g to find next;'
                ' ctrl+r find prior.')

    def setTextBuffer(self, textBuffer):
        app.editor.InteractiveFindInput.setTextBuffer(self, textBuffer)
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            KEY_BTAB: self.priorFocusableWindow,
            KEY_ESCAPE: self.changeToHostWindow,
            KEY_F1: self.info,
            KEY_F3: self.saveEventChangeToHostWindow,
            KEY_SHIFT_F3: self.saveEventChangeToHostWindow,
            #CTRL_E: self.extendFindWindow,
            CTRL_F: self.findNext,
            CTRL_G: self.findNext,
            CTRL_I: self.nextFocusableWindow,
            CTRL_J: self.changeToHostWindow,
            CTRL_N: self.saveEventChangeToHostWindow,
            CTRL_O: self.changeToFileManagerWindow,
            CTRL_P: self.changeToPrediction,
            CTRL_R: self.findPrior,
            #KEY_DOWN: self.findNext,
            #KEY_UP: self.findPrior,
        })
        self.commandSet = commandSet
        self.commandDefault = self.textBuffer.insertPrintable


class InteractiveReplaceInput(app.editor.InteractiveFindInput):
    """Find text within the current document."""

    def __init__(self, view):
        app.editor.InteractiveFindInput.__init__(self, view)

    def focus(self):
        self.view.parent.parent.textBuffer.setMessage(
            'Press ctrl+g to replace and find next; ctrl+r to replace and find'
            ' prior.')

    def setTextBuffer(self, textBuffer):
        app.editor.InteractiveFindInput.setTextBuffer(self, textBuffer)
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            KEY_BTAB: self.priorFocusableWindow,
            KEY_ESCAPE: self.changeToHostWindow,
            KEY_F1: self.info,
            KEY_F3: self.saveEventChangeToHostWindow,
            KEY_SHIFT_F3: self.saveEventChangeToHostWindow,
            CTRL_E: self.extendFindWindow,
            CTRL_F: self.findNext,
            CTRL_G: self.replaceAndNext,
            CTRL_I: self.nextFocusableWindow,
            CTRL_J: self.changeToHostWindow,
            CTRL_N: self.saveEventChangeToHostWindow,
            CTRL_O: self.changeToFileManagerWindow,
            CTRL_P: self.changeToPrediction,
            CTRL_R: self.replaceAndPrior,
            #KEY_DOWN: self.findNext,
            #KEY_UP: self.findPrior,
        })
        self.commandSet = commandSet
        self.commandDefault = self.textBuffer.insertPrintable

    def extendFindWindow(self):
        self.view.host.toggleExtendedFindWindow()


class InteractiveGoto(app.editor.InteractiveGoto):
    """Jump to a particular line number."""

    def __init__(self, view):
        app.editor.InteractiveGoto.__init__(self, view)

    def setTextBuffer(self, textBuffer):
        app.editor.InteractiveGoto.setTextBuffer(self, textBuffer)
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            KEY_ESCAPE: self.changeToHostWindow,
            KEY_F1: self.info,
            CTRL_F: self.changeToFind,
            CTRL_J: self.changeToHostWindow,
            CTRL_N: self.saveEventChangeToHostWindow,
            CTRL_P: self.changeToPrediction,
            ord('b'): self.gotoBottom,
            ord('B'): self.gotoBottom,
            ord('h'): self.gotoHalfway,
            ord('H'): self.gotoHalfway,
            ord('t'): self.gotoTop,
            ord('T'): self.gotoTop,
        })
        self.commandSet = commandSet
        self.commandDefault = self.textBuffer.insertPrintable


class DirectoryList(app.file_manager_controller.DirectoryListController):
    """Open a file to edit."""

    def __init__(self, view):
        app.file_manager_controller.DirectoryListController.__init__(self, view)

    def setTextBuffer(self, textBuffer):
        assert textBuffer is self.view.textBuffer, textBuffer
        app.file_manager_controller.DirectoryListController.setTextBuffer(
            self, textBuffer)
        commandSet = {
            KEY_BTAB: self.priorFocusableWindow,
            CTRL_I: self.nextFocusableWindow,
            CTRL_J: self.performOpen,
            KEY_ESCAPE: self.changeToInputWindow,
            KEY_F1: self.info,
            KEY_PAGE_DOWN: textBuffer.cursorSelectNonePageDown,
            KEY_PAGE_UP: textBuffer.cursorSelectNonePageUp,
            KEY_DOWN: textBuffer.cursorDown,
            KEY_UP: textBuffer.cursorUp,
        }
        self.commandSet = commandSet
        self.commandDefault = self.passDefaultToPathInput


class FileOpener(app.file_manager_controller.FileManagerController):
    """Open a file to edit."""

    def __init__(self, view):
        app.file_manager_controller.FileManagerController.__init__(self, view)

    def setTextBuffer(self, textBuffer):
        app.file_manager_controller.FileManagerController.setTextBuffer(
            self, textBuffer)
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            KEY_ESCAPE: self.changeToInputWindow,
            KEY_F1: self.info,
            KEY_PAGE_DOWN: self.passEventToDirectoryList,
            KEY_PAGE_UP: self.passEventToDirectoryList,
            KEY_DOWN: self.passEventToDirectoryList,
            KEY_UP: self.passEventToDirectoryList,
            CTRL_I: self.tabCompleteExtend,
            CTRL_J: self.performPrimaryAction,
            CTRL_N: self.saveEventChangeToHostWindow,
            CTRL_O: self.performPrimaryAction,
            CTRL_P: self.changeToPrediction,
            CTRL_Q: self.saveEventChangeToHostWindow,
            CTRL_S: self.saveEventChangeToHostWindow,
        })
        self.commandSet = commandSet
        self.commandDefault = self.textBuffer.insertPrintable


class FilePathInput(app.file_manager_controller.FilePathInputController):
    """Open a file to edit."""

    def __init__(self, view):
        app.file_manager_controller.FilePathInputController.__init__(self, view)

    def setTextBuffer(self, textBuffer):
        app.file_manager_controller.FilePathInputController.setTextBuffer(
            self, textBuffer)
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            KEY_BTAB: self.priorFocusableWindow,
            KEY_ESCAPE: self.changeToInputWindow,
            KEY_F1: self.info,
            KEY_PAGE_DOWN: self.passEventToDirectoryList,
            KEY_PAGE_UP: self.passEventToDirectoryList,
            KEY_DOWN: self.passEventToDirectoryList,
            KEY_UP: self.passEventToDirectoryList,
            CTRL_I: self.tabCompleteExtend,
            CTRL_J: self.performPrimaryAction,
            CTRL_N: self.saveEventChangeToHostWindow,
            CTRL_O: self.performPrimaryAction,
            CTRL_P: self.changeToPrediction,
            CTRL_Q: self.saveEventChangeToHostWindow,
            CTRL_S: self.saveEventChangeToHostWindow,
        })
        self.commandSet = commandSet
        self.commandDefault = self.textBuffer.insertPrintable


class InteractivePrediction(app.editor.InteractivePrediction):
    """Make a guess."""

    def __init__(self, view):
        app.editor.InteractivePrediction.__init__(self, view)

    def setTextBuffer(self, textBuffer):
        app.editor.InteractivePrediction.setTextBuffer(self, textBuffer)
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            KEY_ESCAPE: self.cancel,
            KEY_F1: self.info,
            CTRL_F: self.changeToFind,
            CTRL_G: self.changeToGoto,
            CTRL_J: self.selectItem,
            CTRL_N: self.nextItem,
            CTRL_O: self.changeToFileManagerWindow,
            CTRL_P: self.priorItem,
            CTRL_Q: self.saveEventChangeToHostWindow,
            KEY_DOWN: self.nextItem,
            KEY_UP: self.priorItem,
        })
        self.commandSet = commandSet
        self.commandDefault = self.textBuffer.insertPrintable


class InteractivePrompt(app.interactive_prompt.InteractivePrompt):
    """Extended command prompt."""

    def __init__(self, view):
        app.interactive_prompt.InteractivePrompt.__init__(self, view)

    def setTextBuffer(self, textBuffer):
        app.interactive_prompt.InteractivePrompt.setTextBuffer(self, textBuffer)
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            KEY_ESCAPE: self.changeToHostWindow,
            KEY_F1: self.info,
            CTRL_J: self.execute,
            CTRL_N: self.saveEventChangeToHostWindow,
        })
        self.commandSet = commandSet
        self.commandDefault = self.textBuffer.insertPrintable


class InteractiveQuit(app.controller.Controller):
    """Ask about unsaved changes."""

    def __init__(self, view):
        app.controller.Controller.__init__(self, view, 'interactiveQuit')

    def setTextBuffer(self, textBuffer):
        app.controller.Controller.setTextBuffer(self, textBuffer)
        self.textBuffer = textBuffer
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            #KEY_F1: self.info,
            ord('n'): self.view.quitNow,
            ord('N'): self.view.quitNow,
            ord('y'): self.saveOrChangeToSaveAs,
            ord('Y'): self.saveOrChangeToSaveAs,
        })
        self.commandSet = commandSet
        self.commandDefault = self.confirmationPromptFinish


class CuaEdit(app.controller.Controller):
    """Keyboard mappings for CUA. CUA is the Cut/Copy/Paste paradigm."""

    def __init__(self, view):
        app.controller.Controller.__init__(self, view, 'CuaEdit')
        #self.view = view

    def setTextBuffer(self, textBuffer):
        app.controller.Controller.setTextBuffer(self, textBuffer)
        self.commandSet = mainWindowCommands(self, textBuffer)
        self.commandDefault = self.textBuffer.insertPrintable

    def info(self):
        app.log.info('CuaEdit Command set main')
        app.log.info(repr(self))

    def onChange(self):
        pass


class CuaPlusEdit(CuaEdit):
    """Keyboard mappings for CUA, plus some extra."""

    def __init__(self, view):
        CuaEdit.__init__(self, view)
        app.log.info('CuaPlusEdit.__init__')

    def info(self):
        app.log.info('CuaPlusEdit Command set main')
        app.log.info(repr(self))

    def setTextBuffer(self, textBuffer):
        CuaEdit.setTextBuffer(self, textBuffer)
        commandSet = self.commandSet.copy()
        commandSet.update({
            CTRL_E: self.changeToPrompt,
            CTRL_P: self.changeToPrediction,
            KEY_F1: textBuffer.toggleShowTips,
            KEY_F2: textBuffer.bookmarkNext,
            KEY_F3: textBuffer.findAgain,
            KEY_F4: self.changeToPaletteWindow,
            KEY_F5: self.changeToPopup,
            KEY_SHIFT_F2: textBuffer.bookmarkPrior,
            KEY_SHIFT_F3: textBuffer.findBack,
        })
        self.commandSet = commandSet
        self.commandDefault = self.textBuffer.insertPrintableWithPairing


class PopupController(app.controller.Controller):
    """
  A controller for pop up boxes to notify the user.
  """

    def __init__(self, view):
        app.controller.Controller.__init__(self, view, 'popup')
        self.callerSemaphore = None

        def noOp(ch, meta):
            app.log.info('noOp in PopupController')

        self.commandDefault = noOp
        self.commandSet = {
            KEY_ESCAPE: self.changeToInputWindow,
        }

    def changeToInputWindow(self):
        self.findAndChangeTo('inputWindow')
        if self.callerSemaphore:
            self.callerSemaphore.release()
            self.callerSemaphore = None

    def setOptions(self, options):
        """
    This function is used to change the options that are displayed in the
    popup window as well as their functions.

    Args:
      options (dict): A dictionary mapping keys (ints) to its
                      corresponding action.

    Returns;
      None.
    """
        self.commandSet = options

    def setTextBuffer(self, textBuffer):
        self.textBuffer = textBuffer


class PaletteDialogController(app.controller.Controller):
    """."""

    def __init__(self, view):
        app.controller.Controller.__init__(self, view, 'Palette')
        self.view = view
        app.log.info('PaletteDialogController.__init__')

        def noOp(c, meta):
            app.log.info('noOp in PaletteDialogController')

        self.commandDefault = noOp
        self.commandSet = {
            KEY_F4: self.changeToHostWindow,
            CTRL_J: self.changeToHostWindow,
            KEY_ESCAPE: self.changeToHostWindow,
        }

    def changeToHostWindow(self):
        mainProgram = self.view.prg
        mainProgram.changeFocusTo(mainProgram.inputWindow)

    def info(self):
        app.log.info('PaletteDialogController command set')
        app.log.info(repr(self))

    def setTextBuffer(self, textBuffer):
        self.textBuffer = textBuffer


class PredictionList(app.prediction_controller.PredictionListController):
    """Open a file to edit."""

    def __init__(self, view):
        app.prediction_controller.PredictionListController.__init__(self, view)

    def setTextBuffer(self, textBuffer):
        assert textBuffer is self.view.textBuffer, textBuffer
        app.prediction_controller.PredictionListController.setTextBuffer(
            self, textBuffer)
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            KEY_ESCAPE: self.changeToInputWindow,
            KEY_F1: self.info,
            KEY_PAGE_DOWN: textBuffer.cursorSelectNonePageDown,
            KEY_PAGE_UP: textBuffer.cursorSelectNonePageUp,
            KEY_DOWN: textBuffer.cursorDown,
            KEY_UP: textBuffer.cursorUp,
        })
        self.commandSet = commandSet
        self.commandDefault = self.textBuffer.insertPrintable


class PredictionController(app.prediction_controller.PredictionController):
    """Open a file to edit."""

    def __init__(self, view):
        app.prediction_controller.PredictionController.__init__(self, view)

    def setTextBuffer(self, textBuffer):
        app.prediction_controller.PredictionController.setTextBuffer(
            self, textBuffer)
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            KEY_ESCAPE: self.changeToInputWindow,
            KEY_F1: self.info,
            KEY_PAGE_DOWN: self.passEventToDirectoryList,
            KEY_PAGE_UP: self.passEventToDirectoryList,
            KEY_DOWN: self.passEventToDirectoryList,
            KEY_UP: self.passEventToDirectoryList,
            #CTRL_I: self.tabCompleteExtend,
            CTRL_J: self.performPrimaryAction,
            CTRL_N: self.saveEventChangeToHostWindow,
            CTRL_O: self.performPrimaryAction,
            CTRL_P: self.changeToPrediction,
            CTRL_Q: self.saveEventChangeToHostWindow,
            CTRL_S: self.saveEventChangeToHostWindow,
        })
        self.commandSet = commandSet
        self.commandDefault = self.textBuffer.insertPrintable


class PredictionInputController(
        app.prediction_controller.PredictionInputController):
    """Open a file to edit."""

    def __init__(self, view):
        app.prediction_controller.PredictionInputController.__init__(self, view)

    def setTextBuffer(self, textBuffer):
        app.prediction_controller.PredictionInputController.setTextBuffer(
            self, textBuffer)
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            KEY_BTAB: self.priorFocusableWindow,
            KEY_ESCAPE: self.changeToInputWindow,
            KEY_F1: self.info,
            KEY_PAGE_DOWN: self.passEventToPredictionList,
            KEY_PAGE_UP: self.passEventToPredictionList,
            KEY_DOWN: self.passEventToPredictionList,
            KEY_UP: self.passEventToPredictionList,
            CTRL_L: self.openAlternateFile,
            CTRL_I: self.nextFocusableWindow,
            CTRL_J: self.performPrimaryAction,
            CTRL_N: self.saveEventChangeToHostWindow,
            CTRL_O: self.performPrimaryAction,
            CTRL_P: self.predictionListNext,
            CTRL_Q: self.saveEventChangeToHostWindow,
            CTRL_S: self.saveEventChangeToHostWindow,
        })
        self.commandSet = commandSet
        self.commandDefault = self.textBuffer.insertPrintable


class ToggleController(app.editor.ToggleController):
    """Find text within the current document."""

    def __init__(self, view):
        app.editor.ToggleController.__init__(self, view)

    def setTextBuffer(self, textBuffer):
        app.editor.ToggleController.setTextBuffer(self, textBuffer)
        commandSet = initCommandSet(self, textBuffer)
        commandSet.update({
            KEY_BTAB: self.priorFocusableWindow,
            KEY_ESCAPE: self.changeToHostWindow,
            KEY_F3: self.saveEventChangeToHostWindow,
            KEY_SHIFT_F3: self.saveEventChangeToHostWindow,
            #CTRL_E: self.extendFindWindow,
            CTRL_F: self.changeToFind,
            CTRL_G: self.changeToFind,
            CTRL_I: self.nextFocusableWindow,
            CTRL_J: self.toggleValue,
            CTRL_N: self.saveEventChangeToHostWindow,
            CTRL_O: self.changeToFileManagerWindow,
            CTRL_P: self.changeToPrediction,
            CTRL_R: self.changeToFindPrior,
            ord(' '): self.toggleValue,
        })
        self.commandSet = commandSet

        def noOp(ch, meta):
            app.log.info('noOp in ToggleController')

        self.commandDefault = noOp
