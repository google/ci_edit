# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

"""Key bindings for the ciEditor."""

from app.curses_util import *
import app.controller
import curses
import curses.ascii
import os
import re
import text_buffer


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
  def __init__(self, prg, host, textBuffer):
    app.controller.Controller.__init__(self, prg, host, 'EditText')
    self.textBuffer = textBuffer
    textBuffer.lines = [""]
    self.commandSet = {
      curses.KEY_F1: self.info,
      CTRL_A: textBuffer.selectionAll,
      curses.KEY_BACKSPACE: textBuffer.backspace,
      127: textBuffer.backspace,

      CTRL_C: textBuffer.editCopy,

      CTRL_H: textBuffer.backspace,
      curses.ascii.DEL: textBuffer.backspace,

      CTRL_Q: self.prg.quit,
      CTRL_S: self.saveDocument,
      CTRL_V: textBuffer.editPaste,
      CTRL_X: textBuffer.editCut,
      CTRL_Y: textBuffer.redo,
      CTRL_Z: textBuffer.undo,

      # curses.KEY_DOWN: textBuffer.cursorDown,
      curses.KEY_LEFT: textBuffer.cursorLeft,
      curses.KEY_RIGHT: textBuffer.cursorRight,
      # curses.KEY_UP: textBuffer.cursorUp,
    }

  def focus(self):
    self.prg.log('EditText.focus', repr(self))
    self.commandDefault = self.textBuffer.insertPrintable
    self.commandSet = self.commandSet

  def info(self):
    self.prg.log('EditText command set')

  def saveDocument(self):
    if self.host.host.textBuffer:
      self.host.host.textBuffer.fileWrite()

  def unfocus(self):
    pass


class InteractiveOpener(EditText):
  """Open a file to edit."""
  def __init__(self, prg, host, textBuffer):
    EditText.__init__(self, prg, host, textBuffer)
    commandSet = self.commandSet.copy()
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

  def focus(self):
    self.prg.log('InteractiveOpener.focus')
    EditText.focus(self)
    # Create a new text buffer to display dir listing.
    self.host.setTextBuffer(text_buffer.TextBuffer(self.prg))

  def info(self):
    self.prg.log('InteractiveOpener command set')

  def createOrOpen(self):
    self.prg.log('createOrOpen')
    expandedPath = os.path.abspath(os.path.expanduser(self.textBuffer.lines[0]))
    if not os.path.isdir(expandedPath):
      self.host.setTextBuffer(
          self.prg.bufferManager.loadTextBuffer(expandedPath))
    self.changeToInputWindow()

  def maybeSlash(self, expandedPath):
    if (self.textBuffer.lines[0] and self.textBuffer.lines[0][-1] != '/' and
        os.path.isdir(expandedPath)):
      self.textBuffer.insert('/')

  def tabCompleteFirst(self):
    """Find the first file that starts with the pattern."""
    dirPath, fileName = os.path.split(self.lines[0])
    foundOnce = ''
    for i in os.listdir(os.path.expandvars(os.path.expanduser(dirPath)) or '.'):
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
        self.prg.log('not', i)
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
    self.textBuffer.cursorCol = len(path)
    self.textBuffer.goalCol = self.textBuffer.cursorCol

  def onChange(self):
    path = os.path.expanduser(os.path.expandvars(self.textBuffer.lines[0]))
    dirPath, fileName = os.path.split(path)
    dirPath = dirPath or '.'
    self.prg.log('O.onChange', dirPath, fileName)
    if os.path.isdir(dirPath):
      lines = []
      for i in os.listdir(dirPath):
        if i.startswith(fileName):
          lines.append(i)
      if len(lines) == 1 and os.path.isfile(os.path.join(dirPath, fileName)):
        self.host.setTextBuffer(self.prg.bufferManager.loadTextBuffer(
            os.path.join(dirPath, fileName)))
      else:
        self.host.textBuffer.lines = [
            os.path.abspath(os.path.expanduser(dirPath))+":"] + lines
    else:
      self.host.textBuffer.lines = [
          os.path.abspath(os.path.expanduser(dirPath))+": not found"]


class InteractiveFind(EditText):
  """Find text within the current document."""
  def __init__(self, prg, host, textBuffer):
    EditText.__init__(self, prg, host, textBuffer)
    self.document = host.host
    self.commandSet.update({
      curses.ascii.ESC: self.changeToInputWindow,
      curses.KEY_F1: self.info,
      CTRL_F: self.findNext,
      CTRL_J: self.changeToInputWindow,
      CTRL_R: self.findPrior,
      #CTRL_S: self.replacementTextEdit,
      curses.KEY_DOWN: self.findNext,
      curses.KEY_MOUSE: self.saveEventChangeToInputWindow,
      curses.KEY_UP: self.findPrior,
    })
    self.height = 1

  def findNext(self):
    self.findCmd = self.document.textBuffer.findNext

  def findPrior(self):
    self.findCmd = self.document.textBuffer.findPrior

  def focus(self):
    #self.document.statusLine.hide()
    #self.document.resizeBy(-self.height, 0)
    #self.host.moveBy(-self.height, 0)
    #self.host.resizeBy(self.height-1, 0)
    EditText.focus(self)
    self.findCmd = self.document.textBuffer.find
    selection = self.document.textBuffer.getSelectedText()
    if selection:
      self.textBuffer.selectionAll()
      self.textBuffer.insertLines(selection)
    self.textBuffer.selectionAll()
    self.prg.log('find tb', self.textBuffer.cursorCol)

  def info(self):
    self.prg.log('InteractiveFind command set')

  def onChange(self):
    self.prg.log('InteractiveFind.onChange')
    searchFor = self.textBuffer.lines[0]
    try:
      self.findCmd(searchFor)
    except re.error, e:
      self.error = e.message
    self.findCmd = self.document.textBuffer.find

  #def replacementTextEdit(self):
  #  pass

  def unfocus(self):
    self.prg.log('unfocus Find')
    #self.hide()
    return
    self.document.resizeBy(self.height, 0)
    #self.host.resizeBy(-self.height, 0)
    #self.host.moveBy(self.height, 0)
    self.document.statusLine.show()


class InteractiveGoto(EditText):
  """Jump to a particular line number."""
  def __init__(self, prg, host, textBuffer):
    EditText.__init__(self, prg, host, textBuffer)
    commandSet = self.commandSet.copy()
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

  def focus(self):
    self.prg.log('InteractiveGoto.focus')
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(self.host.textBuffer.cursorRow+1))
    self.textBuffer.selectionAll()
    EditText.focus(self)

  def info(self):
    self.prg.log('InteractiveGoto command set')

  def gotoBottom(self):
    self.cursorMoveTo(len(self.host.textBuffer.lines), 0)
    self.changeToInputWindow()

  def gotoHalfway(self):
    self.cursorMoveTo(len(self.host.textBuffer.lines)/2+1, 0)
    self.changeToInputWindow()

  def gotoTop(self):
    self.cursorMoveTo(1, 0)
    self.changeToInputWindow()

  def cursorMoveTo(self, row, col):
    textBuffer = self.host.textBuffer
    cursorRow = min(max(row - 1, 0), len(textBuffer.lines)-1)
    self.prg.log('cursorMoveTo row', row, cursorRow)
    textBuffer.cursorMove(cursorRow-textBuffer.cursorRow,
        col-textBuffer.cursorCol,
        col-textBuffer.goalCol)
    textBuffer.redo()

  def onChange(self):
    gotoLine = 0
    try: line = self.textBuffer.lines[0]
    except: pass
    gotoLine, gotoCol = (line.split(',') + ['0', '0'])[:2]
    self.cursorMoveTo(parseInt(gotoLine), parseInt(gotoCol))

  #def unfocus(self):
  #  self.hide()


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

      CTRL_J: textBuffer.carrageReturn,

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


class EmacsEdit:
  """Emacs is a common Unix based text editor. This keyboard mapping is similar
  to basic Emacs commands."""
  def __init__(self, prg, host):
    self.prg = prg
    self.host = host

  def focus(self):
    self.prg.log('EmacsEdit.focus')
    self.commandDefault = self.textBuffer.insertPrintable
    self.commandSet = self.commandSet_Main

  def onChange(self):
    pass

  def setTextBuffer(self, textBuffer):
    self.prg.log('EmacsEdit.setTextBuffer')
    self.textBuffer = textBuffer
    self.commandSet_Main = {
      curses.KEY_F1: self.info,

      CTRL_A: textBuffer.cursorStartOfLine,

      CTRL_B: textBuffer.cursorLeft,
      curses.KEY_LEFT: textBuffer.cursorLeft,

      CTRL_H: textBuffer.backspace,
      curses.ascii.DEL: textBuffer.backspace,
      curses.KEY_BACKSPACE: textBuffer.backspace,

      CTRL_D: textBuffer.delete,

      CTRL_E: textBuffer.cursorEndOfLine,

      CTRL_F: textBuffer.cursorRight,
      curses.KEY_RIGHT: textBuffer.cursorRight,

      CTRL_J: textBuffer.carrageReturn,

      CTRL_K: textBuffer.deleteToEndOfLine,

      CTRL_L: self.host.refresh,

      CTRL_N: textBuffer.cursorDown,
      curses.KEY_DOWN: textBuffer.cursorDown,

      CTRL_O: textBuffer.splitLine,

      CTRL_P: textBuffer.cursorUp,
      curses.KEY_UP: textBuffer.cursorUp,

      CTRL_X: self.switchToCommandSetX,
      CTRL_Y: textBuffer.redo,
      CTRL_Z: textBuffer.undo,
    }
    self.commandSet = self.commandSet_Main

    self.commandSet_X = {
      CTRL_C: self.prg.quit,
    }

  def info(self):
    self.prg.log('EmacsEdit Command set main')
    self.prg.log(repr(self))

  def switchToCommandSetX(self):
    self.log('emacs x')
    self.commandSet = self.commandSet_X


class VimEdit:
  """Vim is a common Unix editor. This mapping supports some common vi/vim
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

