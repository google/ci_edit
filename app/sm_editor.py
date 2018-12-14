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
"""Key bindings for the slash-menu editor."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses
import curses.ascii
import app.editor
import os
import re
import text_buffer

from app.curses_util import *
import app.controller


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
            KEY_LEFT: self.cursorLeft,
            CTRL_C: self.editCopy,
            CTRL_H: self.backspace,
            KEY_BACKSPACE1: textBuffer.backspace,
            KEY_BACKSPACE2: textBuffer.backspace,
            KEY_BACKSPACE3: textBuffer.backspace,
            CTRL_D: self.delete,
            CTRL_E: self.cursorEndOfLine,
            CTRL_F: self.cursorRight,
            KEY_RIGHT: self.cursorRight,
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
