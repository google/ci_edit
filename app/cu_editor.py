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

from app.curses_util import *
import app.controller
import app.editor
import app.interactive_prompt
import curses
import text_buffer


def initCommandSet(editText, textBuffer):
  """The basic command set includes line editing controls."""
  return {
    #KEY_F10: editText.prg.debugWindowOrder,
    CTRL_A: textBuffer.selectionAll,

    CTRL_C: textBuffer.editCopy,

    CTRL_H: textBuffer.backspace,

    CTRL_L: textBuffer.cursorSelectLine,

    CTRL_Q: editText.quitOrSwitchToConfirmQuit,
    CTRL_S: editText.saveOrChangeToSaveAs,
    CTRL_V: textBuffer.editPaste,
    CTRL_W: editText.closeOrConfirmClose,
    CTRL_X: textBuffer.editCut,
    CTRL_Y: textBuffer.redo,
    CTRL_Z: textBuffer.undo,

    KEY_BACKSPACE1: textBuffer.backspace,
    KEY_BACKSPACE2: textBuffer.backspace,

    KEY_BACKSPACE3: textBuffer.backspace,
    KEY_DELETE: textBuffer.delete,
    KEY_HOME: textBuffer.cursorStartOfLine,
    KEY_END: textBuffer.cursorEndOfLine,

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


class ConfirmClose(app.controller.Controller):
  """Ask about closing a file with unsaved changes."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, textBuffer)
    self.textBuffer = textBuffer
    self.document = host
    commandSet = initCommandSet(self, textBuffer)
    commandSet.update({
      ord('n'): self.closeFile,
      ord('N'): self.closeFile,
      ord('y'): self.saveOrChangeToSaveAs,
      ord('Y'): self.saveOrChangeToSaveAs,
    })
    self.commandSet = commandSet
    self.commandDefault = self.exitConfirmationPrompt


class ConfirmOverwrite(app.controller.Controller):
  """Ask about writing over an existing file."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, textBuffer)
    self.textBuffer = textBuffer
    self.document = host
    commandSet = initCommandSet(self, textBuffer)
    commandSet.update({
      ord('y'): self.overwriteHostFile,
      ord('Y'): self.overwriteHostFile,
    })
    self.commandSet = commandSet
    self.commandDefault = self.exitConfirmationPrompt


class InteractiveFind(app.editor.InteractiveFind):
  """Find text within the current document."""
  def __init__(self, host, textBuffer):
    app.editor.InteractiveFind.__init__(self, host, textBuffer)
    self.document = host
    commandSet = initCommandSet(self, textBuffer)
    commandSet.update({
      KEY_ESCAPE: self.changeToHostWindow,
      KEY_F1: self.info,
      KEY_F3: self.saveEventChangeToHostWindow,
      KEY_SHIFT_F3: self.saveEventChangeToHostWindow,
      CTRL_E: self.findReplaceChangeToHostWindow,
      CTRL_F: self.findNext,
      CTRL_G: self.findNext,
      CTRL_J: self.changeToHostWindow,
      CTRL_R: self.findPrior,
      KEY_DOWN: self.findNext,
      KEY_UP: self.findPrior,
    })
    self.commandSet = commandSet
    self.commandDefault = self.textBuffer.insertPrintable

  def findReplaceChangeToHostWindow(self):
    self.findReplace()
    self.changeToHostWindow()


class InteractiveGoto(app.editor.InteractiveGoto):
  """Jump to a particular line number."""
  def __init__(self, host, textBuffer):
    app.editor.InteractiveGoto.__init__(self, host, textBuffer)
    self.document = host
    commandSet = initCommandSet(self, textBuffer)
    commandSet.update({
      KEY_ESCAPE: self.changeToHostWindow,
      KEY_F1: self.info,
      CTRL_J: self.changeToHostWindow,
      ord('b'): self.gotoBottom,
      ord('B'): self.gotoBottom,
      ord('h'): self.gotoHalfway,
      ord('H'): self.gotoHalfway,
      ord('t'): self.gotoTop,
      ord('T'): self.gotoTop,
    })
    self.commandSet = commandSet
    self.commandDefault = self.textBuffer.insertPrintable


class InteractiveOpener(app.editor.InteractiveOpener):
  """Open a file to edit."""
  def __init__(self, host, textBuffer):
    app.editor.InteractiveOpener.__init__(self, host, textBuffer)
    self.document = host
    commandSet = initCommandSet(self, textBuffer)
    commandSet.update({
      KEY_ESCAPE: self.changeToHostWindow,
      KEY_F1: self.info,
      CTRL_I: self.tabCompleteExtend,
      CTRL_J: self.createOrOpen,
      CTRL_N: self.createOrOpen,
      CTRL_O: self.createOrOpen,
      CTRL_Q: self.saveEventChangeToHostWindow,
    })
    self.commandSet = commandSet
    self.commandDefault = self.textBuffer.insertPrintable


class InteractivePrediction(app.editor.InteractivePrediction):
  """Make a guess."""
  def __init__(self, host, textBuffer):
    app.editor.InteractivePrediction.__init__(self, host, textBuffer)
    self.document = host
    commandSet = initCommandSet(self, textBuffer)
    commandSet.update({
      KEY_ESCAPE: self.cancel,
      KEY_F1: self.info,
      CTRL_J: self.selectItem,
      CTRL_N: self.nextItem,
      CTRL_P: self.priorItem,
      CTRL_Q: self.saveEventChangeToHostWindow,
      KEY_DOWN: self.nextItem,
      KEY_UP: self.priorItem,
    })
    self.commandSet = commandSet
    self.commandDefault = self.textBuffer.insertPrintable


class InteractivePrompt(app.interactive_prompt.InteractivePrompt):
  """Extended command prompt."""
  def __init__(self, host, textBuffer):
    app.interactive_prompt.InteractivePrompt.__init__(self, host, textBuffer)
    self.document = host
    commandSet = initCommandSet(self, textBuffer)
    commandSet.update({
      KEY_ESCAPE: self.changeToHostWindow,
      KEY_F1: self.info,
      CTRL_J: self.execute,
    })
    self.commandSet = commandSet
    self.commandDefault = self.textBuffer.insertPrintable


class InteractiveQuit(app.controller.Controller):
  """Ask about unsaved changes."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, textBuffer)
    self.textBuffer = textBuffer
    self.document = host
    commandSet = initCommandSet(self, textBuffer)
    commandSet.update({
      #KEY_F1: self.info,
      ord('n'): host.quitNow,
      ord('N'): host.quitNow,
      ord('y'): self.saveOrChangeToSaveAs,
      ord('Y'): self.saveOrChangeToSaveAs,
    })
    self.commandSet = commandSet
    self.commandDefault = self.exitConfirmationPrompt


class InteractiveSaveAs(app.controller.Controller):
  """Ask about unsaved files."""
  def __init__(self, host, textBuffer):
    app.controller.Controller.__init__(self, host, textBuffer)
    self.textBuffer = textBuffer
    self.document = host
    commandSet = initCommandSet(self, textBuffer)
    commandSet.update({
      KEY_ESCAPE: self.changeToHostWindow,
      #KEY_F1: self.info,
      CTRL_J: self.saveAs,
    })
    self.commandSet = commandSet
    self.commandDefault = self.textBuffer.insertPrintable

  def saveAs(self):
    app.log.info('saveAs')
    name = self.textBuffer.lines[0]
    if not len(name):
      self.document.textBuffer.setMessage(
          'File not saved (file name was empty).')
      self.changeToHostWindow()
      return
    self.document.textBuffer.setFilePath(self.textBuffer.lines[0])
    # Preload the message with an error that should be overwritten.
    self.document.textBuffer.setMessage('Error saving file')
    self.document.textBuffer.fileWrite()
    self.changeToHostWindow()


class CuaEdit(app.controller.Controller):
  """Keyboard mappings for CUA. CUA is the Cut/Copy/Paste paradigm."""
  def __init__(self, prg, host):
    app.controller.Controller.__init__(self, host, 'CuaEdit')
    self.host = host
    app.log.info('CuaEdit.__init__')

  def setTextBuffer(self, textBuffer):
    self.textBuffer = textBuffer
    commandSet = initCommandSet(self, textBuffer)
    commandSet.update({
      KEY_ESCAPE: textBuffer.normalize,

      KEY_F1: self.info,

      KEY_BTAB: textBuffer.unindent,
      KEY_PAGE_UP: textBuffer.cursorPageUp,
      KEY_PAGE_DOWN: textBuffer.cursorPageDown,

      CTRL_F: self.changeToFind,
      CTRL_G: self.changeToGoto,

      CTRL_I: textBuffer.indent,
      CTRL_J: textBuffer.carriageReturn,

      CTRL_O: self.changeToFileOpen,
      CTRL_R: self.changeToFindPrior,

      KEY_DOWN: textBuffer.cursorDown,
      KEY_SHIFT_LEFT: textBuffer.cursorSelectLeft,
      KEY_SHIFT_RIGHT: textBuffer.cursorSelectRight,
      KEY_UP: textBuffer.cursorUp,

      KEY_SHIFT_DOWN: textBuffer.cursorSelectDown,
      KEY_SHIFT_UP: textBuffer.cursorSelectUp,

      KEY_CTRL_DOWN: textBuffer.cursorDownScroll,
      KEY_CTRL_SHIFT_DOWN: textBuffer.cursorSelectDownScroll,
      KEY_CTRL_UP: textBuffer.cursorUpScroll,
      KEY_CTRL_SHIFT_UP: textBuffer.cursorSelectUpScroll,
    })
    self.commandSet = commandSet
    self.commandDefault = self.textBuffer.insertPrintable

  def info(self):
    app.log.info('CuaEdit Command set main')
    app.log.info(repr(self))

  def onChange(self):
    pass


class CuaPlusEdit(CuaEdit):
  """Keyboard mappings for CUA, plus some extra."""
  def __init__(self, prg, host):
    CuaEdit.__init__(self, prg, host)
    app.log.info('CuaPlusEdit.__init__')

  def info(self):
    app.log.info('CuaPlusEdit Command set main')
    app.log.info(repr(self))

  def setTextBuffer(self, textBuffer):
    app.log.info('CuaPlusEdit.__init__')
    CuaEdit.setTextBuffer(self, textBuffer)
    commandSet = self.commandSet.copy()
    commandSet.update({
      CTRL_E: self.changeToPrompt,
      CTRL_P: self.changeToPrediction,

      KEY_F2: textBuffer.bookmarkNext,
      KEY_F3: textBuffer.findAgain,
      #KEY_F4: self.prg.paletteWindow.focus,
      KEY_SHIFT_F2: textBuffer.bookmarkPrior,
      KEY_SHIFT_F3: textBuffer.findBack,
    })
    self.commandSet = commandSet


class PaletteDialogController(app.controller.Controller):
  """."""
  def __init__(self, prg, view):
    app.controller.Controller.__init__(self, prg, 'Palette')
    self.view = view
    app.log.info('PaletteDialogController.__init__')
    def noOp(c):
      app.log.info('noOp in PaletteDialogController')
    self.commandDefault = noOp
    self.commandSet = {
      CTRL_J: self.changeToHostWindow,
      KEY_ESCAPE: self.changeToHostWindow,
    }

  def changeToHostWindow(self):
    self.view.hide()
    app.controller.Controller.changeToHostWindow(self)

  def info(self):
    app.log.info('PaletteDialogController command set')
    app.log.info(repr(self))

  def setTextBuffer(self, textBuffer):
    pass