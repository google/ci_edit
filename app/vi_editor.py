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
"""Key bindings for the vi-like editor."""

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


class ViEdit(app.controller.Controller):
    """Vi is a common Unix editor. This mapping supports some common vi/vim
  commands."""

    def __init__(self, view):
        app.controller.Controller.__init__(self, view, 'ViEdit')
        self.commandDefault = None

    def setTextBuffer(self, textBuffer):
        app.controller.Controller.setTextBuffer(self, textBuffer)
        normalCommandSet = {
            ord('^'): textBuffer.cursorStartOfLine,
            ord('$'): textBuffer.cursorEndOfLine,
            ord('h'): textBuffer.cursorLeft,
            ord('i'): self.switchToCommandSetInsert,
            ord('j'): textBuffer.cursorDown,
            ord('k'): textBuffer.cursorUp,
            ord('l'): textBuffer.cursorRight,
        }
        self.commandSet = normalCommandSet
        self.commandSet_Insert = {
            curses.ascii.ESC: self.switchToCommandSetNormal,
        }
        self.commandDefault = self.textBuffer.insertPrintable

    def info(self):
        app.log.info('ViEdit Command set main')
        app.log.info(repr(self))

    def focus(self):
        app.log.info('VimEdit.focus')
        if not self.commandDefault:
            self.commandDefault = self.textBuffer.noOp
            self.commandSet = self.commandSet_Normal

    def onChange(self):
        pass

    def switchToCommandSetInsert(self, ignored=1):
        app.log.info('insert mode')
        self.commandDefault = self.textBuffer.insertPrintable
        self.commandSet = self.commandSet_Insert

    def switchToCommandSetNormal(self, ignored=1):
        app.log.info('normal mode')
        self.commandDefault = self.textBuffer.noOp
        self.commandSet = self.commandSet_Normal
