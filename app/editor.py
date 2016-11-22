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
    self.document = None
    self.textBuffer = textBuffer
    textBuffer.lines = [""]

  def focus(self):
    app.log.info('EditText.focus', repr(self))
    self.commandDefault = self.textBuffer.insertPrintable

  def info(self):
    self.prg.log('EditText command set')

  def saveDocument(self):
    self.prg.log('saveDocument', self.document)
    if self.document and self.document.textBuffer:
      self.document.textBuffer.fileWrite()


class InteractiveOpener(EditText):
  """Open a file to edit."""
  def __init__(self, prg, host, textBuffer):
    EditText.__init__(self, prg, host, textBuffer)

  def focus(self):
    app.log.info('InteractiveOpener.focus')
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
    self.height = 1

  def findNext(self):
    self.findCmd = self.document.textBuffer.findNext

  def findPrior(self):
    self.findCmd = self.document.textBuffer.findPrior

  def focus(self):
    app.log.info('InteractiveFind focus()')
    #self.document.statusLine.hide()
    #self.document.resizeBy(-self.height, 0)
    #self.host.moveBy(-self.height, 0)
    #self.host.resizeBy(self.height-1, 0)
    EditText.focus(self)
    self.findCmd = self.document.textBuffer.find
    selection = self.document.textBuffer.getSelectedText()
    if selection:
      self.textBuffer.selectionAll()
      selection = "\\n".join(selection)
      app.log.info(selection)
      self.textBuffer.insert(selection)
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

  def unfocus(self):
    self.prg.log('unfocus Find')
    #self.hide()


class InteractiveGoto(EditText):
  """Jump to a particular line number."""
  def __init__(self, prg, host, textBuffer):
    EditText.__init__(self, prg, host, textBuffer)

  def focus(self):
    app.log.info('InteractiveGoto.focus')
    self.textBuffer.selectionAll()
    self.textBuffer.insert(str(self.document.textBuffer.cursorRow+1))
    self.textBuffer.selectionAll()
    EditText.focus(self)

  def info(self):
    self.prg.log('InteractiveGoto command set')

  def gotoBottom(self):
    self.cursorMoveTo(len(self.document.textBuffer.lines), 0)
    self.changeToInputWindow()

  def gotoHalfway(self):
    self.cursorMoveTo(len(self.document.textBuffer.lines)/2+1, 0)
    self.changeToInputWindow()

  def gotoTop(self):
    self.cursorMoveTo(1, 0)
    self.changeToInputWindow()

  def cursorMoveTo(self, row, col):
    textBuffer = self.document.textBuffer
    cursorRow = min(max(row - 1, 0), len(textBuffer.lines)-1)
    #self.prg.log('cursorMoveTo row', row, cursorRow)
    textBuffer.cursorMove(cursorRow-textBuffer.cursorRow,
        col-textBuffer.cursorCol,
        col-textBuffer.goalCol)
    textBuffer.redo()
    textBuffer.cursorScrollToMiddle()
    textBuffer.redo()

  def onChange(self):
    gotoLine = 0
    try: line = self.textBuffer.lines[0]
    except: pass
    gotoLine, gotoCol = (line.split(',') + ['0', '0'])[:2]
    self.cursorMoveTo(parseInt(gotoLine), parseInt(gotoCol))
