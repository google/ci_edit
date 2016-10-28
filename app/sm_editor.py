# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

"""Key bindings for the slash-menu editor."""

from app.curses_util import *
import app.controller
import curses
import curses.ascii
import app.editor
import os
import re
import text_buffer


class CiEdit(app.controller.Controller):
  """Keyboard mappings for ci."""
  def __init__(self, prg, textBuffer):
    app.controller.Controller.__init__(self, prg, None, 'CiEdit')
    self.prg.log('CiEdit.__init__')
    self.textBuffer = textBuffer
    self.commandSet_Main = {
      CTRL_SPACE: self.switchToCommandSetCmd,

      CTRL_A: textBuffer.cursorStartOfLine,

      CTRL_B: textBuffer.cursorLeft,
      curses.KEY_LEFT: self.cursorLeft,

      CTRL_C: self.editCopy,

      CTRL_H: self.backspace,
      curses.ascii.DEL: self.backspace,
      curses.KEY_BACKSPACE: self.backspace,

      CTRL_D: self.delete,

      CTRL_E: self.cursorEndOfLine,

      CTRL_F: self.cursorRight,
      curses.KEY_RIGHT: self.cursorRight,

      CTRL_J: self.carrageReturn,

      CTRL_K: self.deleteToEndOfLine,

      CTRL_L: self.win.refresh,

      CTRL_N: self.cursorDown,
      curses.KEY_DOWN: self.cursorDown,

      CTRL_O: self.splitLine,

      CTRL_P: self.cursorUp,
      curses.KEY_UP: self.cursorUp,

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
