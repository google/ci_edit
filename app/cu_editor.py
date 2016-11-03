# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

"""Key bindings for the cua-like editor."""

from app.curses_util import *
import app.controller
import app.editor
import curses
import curses.ascii
import text_buffer


def initCommandSet(editText, textBuffer):
   return {
      CTRL_A: textBuffer.selectionAll,
      curses.KEY_BACKSPACE: textBuffer.backspace,
      127: textBuffer.backspace,

      CTRL_C: textBuffer.editCopy,

      CTRL_H: textBuffer.backspace,
      curses.ascii.DEL: textBuffer.backspace,

      CTRL_Q: editText.prg.quit,
      CTRL_S: editText.saveDocument,
      CTRL_V: textBuffer.editPaste,
      CTRL_X: textBuffer.editCut,
      CTRL_Y: textBuffer.redo,
      CTRL_Z: textBuffer.undo,

      # curses.KEY_DOWN: textBuffer.cursorDown,
      curses.KEY_LEFT: textBuffer.cursorLeft,
      curses.KEY_RIGHT: textBuffer.cursorRight,
      # curses.KEY_UP: textBuffer.cursorUp,
    }


class InteractiveOpener(app.editor.InteractiveOpener):
  """Open a file to edit."""
  def __init__(self, prg, host, textBuffer):
    app.editor.InteractiveOpener.__init__(self, prg, host, textBuffer)
    self.document = host
    commandSet = initCommandSet(self, textBuffer)
    commandSet.update({
      curses.ascii.ESC: self.changeToInputWindow,
      curses.KEY_F1: self.info,
      CTRL_I: self.tabCompleteExtend,
      CTRL_J: self.createOrOpen,
      CTRL_N: self.createOrOpen,
      CTRL_O: self.createOrOpen,
      CTRL_Q: self.prg.quit,
    })
    self.commandSet = commandSet


class InteractiveFind(app.editor.InteractiveFind):
  """Find text within the current document."""
  def __init__(self, prg, host, textBuffer):
    app.editor.InteractiveFind.__init__(self, prg, host, textBuffer)
    self.document = host.host
    commandSet = initCommandSet(self, textBuffer)
    commandSet.update({
      curses.ascii.ESC: self.changeToInputWindow,
      curses.KEY_F1: self.info,
      CTRL_F: self.findNext,
      CTRL_J: self.changeToInputWindow,
      CTRL_R: self.findPrior,
      curses.KEY_DOWN: self.findNext,
      curses.KEY_MOUSE: self.saveEventChangeToInputWindow,
      curses.KEY_UP: self.findPrior,
    })
    self.commandSet = commandSet


class InteractiveGoto(app.editor.InteractiveGoto):
  """Jump to a particular line number."""
  def __init__(self, prg, host, textBuffer):
    app.editor.InteractiveGoto.__init__(self, prg, host, textBuffer)
    self.document = host.host
    commandSet = initCommandSet(self, textBuffer)
    commandSet.update({
      curses.ascii.ESC: self.changeToInputWindow,
      curses.KEY_F1: self.info,
      CTRL_J: self.changeToInputWindow,
      curses.KEY_MOUSE: self.saveEventChangeToInputWindow,
      ord('b'): self.gotoBottom,
      ord('h'): self.gotoHalfway,
      ord('t'): self.gotoTop,
    })
    self.commandSet = commandSet


class CuaEdit(app.controller.Controller):
  """Keyboard mappings for CUA. CUA is the Cut/Copy/Paste paradigm."""
  def __init__(self, prg, host):
    app.controller.Controller.__init__(self, prg, None, 'CuaEdit')
    self.prg = prg
    self.host = host
    self.prg.log('CuaEdit.__init__')

  def setTextBuffer(self, textBuffer):
    self.textBuffer = textBuffer
    self.commandSet_Main = {
      curses.ascii.ESC: textBuffer.selectionNone,
      curses.KEY_DC: textBuffer.delete,
      curses.KEY_MOUSE: self.prg.handleMouse,
      curses.KEY_RESIZE: self.prg.handleScreenResize,

      curses.KEY_F1: self.info,
      curses.KEY_F3: self.testPalette,
      curses.KEY_F4: self.showPalette,
      curses.KEY_F5: self.hidePalette,

      curses.KEY_BTAB: textBuffer.unindent,
      curses.KEY_HOME: textBuffer.cursorStartOfLine,
      curses.KEY_END: textBuffer.cursorEndOfLine,
      curses.KEY_PPAGE: textBuffer.cursorPageUp,
      curses.KEY_NPAGE: textBuffer.cursorPageDown,

      CTRL_A: textBuffer.selectionAll,
      CTRL_C: textBuffer.editCopy,
      CTRL_E: textBuffer.nextSelectionMode,
      CTRL_F: self.switchToFind,
      CTRL_G: self.switchToGoto,

      #CTRL_H: textBuffer.backspace,
      curses.ascii.DEL: textBuffer.backspace,
      curses.KEY_BACKSPACE: textBuffer.backspace,

      CTRL_I: textBuffer.indent,
      CTRL_J: textBuffer.carriageReturn,
      CTRL_N: textBuffer.cursorDown,

      CTRL_O: self.switchToCommandSetInteractiveOpen,
      CTRL_Q: self.prg.quit,
      CTRL_S: textBuffer.fileWrite,
      CTRL_V: textBuffer.editPaste,
      CTRL_X: textBuffer.editCut,
      CTRL_Y: textBuffer.redo,
      CTRL_Z: textBuffer.undo,

      curses.KEY_DOWN: textBuffer.cursorDown,
      curses.KEY_LEFT: textBuffer.cursorLeft,
      curses.KEY_RIGHT: textBuffer.cursorRight,
      curses.KEY_SLEFT: textBuffer.cursorSelectLeft,
      curses.KEY_SRIGHT: textBuffer.cursorSelectRight,
      curses.KEY_UP: textBuffer.cursorUp,

      KEY_SHIFT_DOWN: textBuffer.cursorSelectDown,
      KEY_SHIFT_UP: textBuffer.cursorSelectUp,

      KEY_CTRL_DOWN: textBuffer.cursorDownScroll,
      KEY_CTRL_SHIFT_DOWN: textBuffer.cursorSelectDownScroll,
      KEY_CTRL_LEFT: textBuffer.cursorMoveWordLeft,
      KEY_CTRL_SHIFT_LEFT: textBuffer.cursorSelectWordLeft,
      KEY_CTRL_RIGHT: textBuffer.cursorMoveWordRight,
      KEY_CTRL_SHIFT_RIGHT: textBuffer.cursorSelectWordRight,
      KEY_CTRL_UP: textBuffer.cursorUpScroll,
      KEY_CTRL_SHIFT_UP: textBuffer.cursorSelectUpScroll,
    }

  def focus(self):
    self.commandDefault = self.textBuffer.insertPrintable
    self.commandSet = self.commandSet_Main

  def info(self):
    self.prg.log('CuaEdit Command set main')
    self.prg.log(repr(self))

  def onChange(self):
    pass

  def switchToCommandSetInteractiveOpen(self):
    self.prg.changeTo = self.host.headerLine

  def switchToFind(self):
    self.prg.changeTo = self.host.interactiveFind

  def switchToGoto(self):
    self.prg.changeTo = self.host.interactiveGoto

  def showPalette(self):
    self.prg.paletteWindow.focus()

  def hidePalette(self):
    self.prg.paletteWindow.hide()

  def testPalette(self):
    self.prg.shiftPalette()


class CuaPlusEdit(CuaEdit):
  """Keyboard mappings for CUA, plus some extra."""
  def __init__(self, prg, host):
    CuaEdit.__init__(self, prg, host)
    self.prg.log('CuaPlusEdit.__init__')

  def info(self):
    self.prg.log('CuaPlusEdit Command set main')
    self.prg.log(repr(self))

  def setTextBuffer(self, textBuffer):
    self.prg.log('CuaPlusEdit.__init__')
    CuaEdit.setTextBuffer(self, textBuffer)
    commandSet = self.commandSet_Main.copy()
    commandSet.update({
      CTRL_E: textBuffer.nextSelectionMode,
    })
    self.commandSet_Main = commandSet
