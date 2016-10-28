# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

"""Key bindings for the vi-like editor."""

from app.curses_util import *
import app.controller
import curses
import curses.ascii
import os
import re
import text_buffer


class ViEdit:
  """Vi is a common Unix editor. This mapping supports some common vi/vim
  commands."""
  def __init__(self, prg, host):
    self.prg = prg
    self.host = host
    self.commandDefault = None

  def focus(self):
    self.prg.log('VimEdit.focus')
    if not self.commandDefault:
      self.commandDefault = self.textBuffer.noOp
      self.commandSet = self.commandSet_Normal

  def onChange(self):
    pass

  def setTextBuffer(self, textBuffer):
    self.prg.log('VimEdit.setTextBuffer');
    self.textBuffer = textBuffer
    self.commandSet_Normal = {
      ord('^'): textBuffer.cursorStartOfLine,
      ord('$'): textBuffer.cursorEndOfLine,
      ord('h'): textBuffer.cursorLeft,
      ord('i'): self.switchToCommandSetInsert,
      ord('j'): textBuffer.cursorDown,
      ord('k'): textBuffer.cursorUp,
      ord('l'): textBuffer.cursorRight,
    }
    self.commandSet_Insert = {
      curses.ascii.ESC: self.switchToCommandSetNormal,
    }

  def switchToCommandSetInsert(self, ignored=1):
    self.prg.log('insert mode')
    self.commandDefault = self.textBuffer.insertPrintable
    self.commandSet = self.commandSet_Insert

  def switchToCommandSetNormal(self, ignored=1):
    self.prg.log('normal mode')
    self.commandDefault = self.textBuffer.noOp
    self.commandSet = self.commandSet_Normal

