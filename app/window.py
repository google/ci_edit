#!/usr/bin/python
# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

#import app.curses_util
import app.editor
import app.text_buffer
import sys
import curses
#import time
#import traceback
#import os

class StaticWindow:
  """A static window does not get focus."""
  def __init__(self, prg, rows, cols, top, left):
    self.prg = prg
    self.color = 0
    self.colorSelected = 1
    self.top = top
    self.left = left
    self.rows = rows
    self.cols = cols
    self.cursorWindow = curses.newwin(rows, cols, top, left)

  def addStr(self, row, col, text, colorPair):
    """Overwrite text a row, column with text."""
    try: self.cursorWindow.addstr(row, col, text, colorPair)
    except curses.error: pass

  def contains(self, row, col):
    """Determine whether the position at row, col lay within this window."""
    return (row >= self.top and row < self.top+self.rows and
        col >= self.left and col < self.left + self.cols)

  def layer(self, layerIndex):
    """Move window to specified z order."""
    try: self.prg.zOrder.remove(self)
    except: pass
    self.prg.zOrder.insert(layerIndex, self)

  def hide(self):
    """Remove window from the render list."""
    try: self.prg.zOrder.remove(self)
    except ValueError: self.prg.log('not found')

  def mouseClick(self, row, col, shift, ctrl, alt):
    pass

  def mouseDoubleClick(self, row, col, shift, ctrl, alt):
    pass

  def mouseMoved(self, row, col, shift, ctrl, alt):
    pass

  def mouseRelease(self, row, col, shift, ctrl, alt):
    pass

  def mouseTripleClick(self, row, col, shift, ctrl, alt):
    pass

  def mouseWheelDown(self, shift, ctrl, alt):
    pass

  def mouseWheelUp(self, shift, ctrl, alt):
    pass

  def refresh(self):
    """Redraw window."""
    self.cursorWindow.refresh()

  def moveTo(self, top, left):
    self.prg.log('move')
    self.top = top
    self.left = left
    self.cursorWindow.mvwin(self.top, self.left)

  def moveBy(self, top, left):
    self.prg.log('move')
    self.top += top
    self.left += left
    self.cursorWindow.mvwin(self.top, self.left)

  def resizeTo(self, rows, cols):
    self.prg.log('resize')
    self.rows += rows
    self.cols += cols
    self.cursorWindow.resize(self.rows, self.cols)

  def resizeBy(self, rows, cols):
    self.prg.log('resize')
    self.rows += rows
    self.cols += cols
    self.cursorWindow.resize(self.rows, self.cols)

  def show(self):
    """Show window and bring it to the top layer."""
    try: self.prg.zOrder.remove(self)
    except: pass
    self.prg.zOrder.append(self)


class Window(StaticWindow):
  """A Window may have focus. A Window holds a TextBuffer and a
    controller that operates on the TextBuffer."""
  def __init__(self, prg, rows, cols, top, left, controller=None):
    StaticWindow.__init__(self, prg, rows, cols, top, left)
    self.controller = controller
    self.cursorWindow.keypad(1)
    self.textBuffer = None

  def focus(self):
    try: self.prg.zOrder.remove(self)
    except ValueError: self.prg.log('not found')
    self.prg.zOrder.append(self)
    self.controller.focus()
    self.controller.commandLoop()

  def mouseClick(self, row, col, shift, ctrl, alt):
    self.textBuffer.mouseClick(row, col, shift, ctrl, alt)

  def mouseDoubleClick(self, row, col, shift, ctrl, alt):
    self.textBuffer.mouseDoubleClick(row, col, shift, ctrl, alt)

  def mouseMoved(self, row, col, shift, ctrl, alt):
    self.textBuffer.mouseMoved(row, col, shift, ctrl, alt)

  def mouseRelease(self, row, col, shift, ctrl, alt):
    self.textBuffer.mouseRelease(row, col, shift, ctrl, alt)

  def mouseTripleClick(self, row, col, shift, ctrl, alt):
    self.textBuffer.mouseTripleClick(row, col, shift, ctrl, alt)

  def mouseWheelDown(self, shift, ctrl, alt):
    self.textBuffer.mouseWheelDown(shift, ctrl, alt)

  def mouseWheelUp(self, shift, ctrl, alt):
    self.textBuffer.mouseWheelUp(shift, ctrl, alt)

  def refresh(self):
    self.textBuffer.draw(self)
    if self.prg.zOrder[-1] is self:
      self.prg.debugDraw(self)
    try:
      self.cursorWindow.move(
          self.textBuffer.cursorRow - self.textBuffer.scrollRow,
          self.textBuffer.cursorCol - self.textBuffer.scrollCol)
    except curses.error:
      pass
    self.cursorWindow.refresh()

  def getCh(self):
    self.prg.refresh()
    return self.cursorWindow.getch()

  def log(self, *args):
    self.prg.log(*args)

  def setTextBuffer(self, textBuffer):
    self.textBuffer = textBuffer

  def unfocus(self):
    self.controller.unfocus()


class HeaderLine(Window):
  def __init__(self, prg, host, rows, cols, top, left):
    Window.__init__(self, prg, rows, cols, top, left)
    self.setTextBuffer(app.text_buffer.TextBuffer(prg))
    self.controller = app.editor.InteractiveOpener(prg, host, self.textBuffer)


class InteractiveFind(Window):
  def __init__(self, prg, host, rows, cols, top, left):
    Window.__init__(self, prg, rows, cols, top, left)
    self.host = host
    self.setTextBuffer(app.text_buffer.TextBuffer(prg))
    self.controller = app.editor.InteractiveFind(prg, self, self.textBuffer)


class StatusLine(Window):
  """The status line appears at the bottom of the screen. It shows the current
  line and column the cursor is on."""
  def __init__(self, prg, host, rows, cols, top, left):
    Window.__init__(self, prg, rows, cols, top, left)
    self.host = host
    self.setTextBuffer(app.text_buffer.TextBuffer(prg))
    self.controller = app.editor.InteractiveGoto(prg, host, self.textBuffer)

  def refresh(self):
    maxy, maxx = self.cursorWindow.getmaxyx()
    if self.prg.zOrder[-1] is self:
      Window.refresh(self)
    else:
      tb = self.host.textBuffer
      statusLine = ' . '
      if tb.isDirty():
        statusLine = ' * '
      colPercentage = 0
      if len(tb.lines):
         colPercentage = tb.cursorCol*100/(len(tb.lines[tb.cursorRow])+1)
      rightSide = '%s | %d,%d %d%%,%d%%'%(
          app.text_buffer.kSelectionModeNames[tb.selectionMode],
          tb.cursorRow+1, tb.cursorCol,
          tb.cursorRow*100/(len(tb.lines)+1),
          colPercentage)
      statusLine += ' '*(maxx-len(statusLine)-len(rightSide)) + rightSide
      self.addStr(0, 0, statusLine, self.color)
      self.cursorWindow.refresh()


class DirectoryPanel(Window):
  """A content area panel that shows a file directory list."""
  def __init__(self, prg, rows, cols, top, left):
    self.prg = prg
    Window.__init__(self, prg, rows, cols, top, left)
    self.color = curses.color_pair(18)
    self.colorSelected = curses.color_pair(3)


class FilePanel(Window):
  def __init__(self, prg, rows, cols, top, left):
    self.prg = prg
    Window.__init__(self, prg, rows, cols, top, left)
    self.color = curses.color_pair(18)
    self.colorSelected = curses.color_pair(3)


class InputWindow(Window):
  """This is the main content window. Often the largest pane displayed."""
  def __init__(self, prg, rows, cols, top, left, header, footer, lineNumbers):
    assert(prg)
    self.prg = prg
    self.showHeader = header
    if header:
      self.headerLine = HeaderLine(prg, self, 1, cols, top, left)
      self.headerLine.color = curses.color_pair(168)
      self.headerLine.colorSelected = curses.color_pair(47)
      self.headerLine.show()
      rows -= 1
      top += 1
    self.showFooter = footer
    if footer:
      findReplaceHeight = 1
      self.interactiveFind = InteractiveFind(prg, self, findReplaceHeight, cols,
          top+rows-findReplaceHeight, left)
      self.interactiveFind.color = curses.color_pair(205)
      self.interactiveFind.colorSelected = curses.color_pair(87)
    if footer:
      self.statusLine = StatusLine(prg, self, 1, cols, top+rows-1, left)
      self.statusLine.color = curses.color_pair(168)
      self.statusLine.colorSelected = curses.color_pair(47)
      self.statusLine.show()
      rows -= 1
    self.showLineNumbers = lineNumbers
    if lineNumbers:
      self.leftColumn = StaticWindow(prg, rows, 7, top, left)
      self.leftColumn.color = curses.color_pair(211)
      self.leftColumn.colorSelected = curses.color_pair(146)
      cols -= 7
      left += 7
    if 1:
      self.rightColumn = StaticWindow(prg, rows, 1, top, left+cols-1)
      self.rightColumn.color = curses.color_pair(18)
      self.rightColumn.colorSelected = curses.color_pair(105)
      cols -= 1
    Window.__init__(self, prg, rows, cols, top, left)
    self.color = curses.color_pair(18)
    self.colorSelected = curses.color_pair(228)
    self.controller = app.editor.MainController(prg, self)
    if header:
      if self.prg.cliFiles:
        self.headerLine.controller.setFileName(self.prg.cliFiles[0]['path'])
        self.setTextBuffer(self.prg.bufferManager.loadTextBuffer(
            self.prg.cliFiles[0]['path']))
      else:
        scratchPath = "~/ci_scratch"
        self.headerLine.controller.setFileName(scratchPath)
        self.setTextBuffer(self.prg.bufferManager.loadTextBuffer(scratchPath))

  def drawLineNumbers(self):
    maxy, maxx = self.cursorWindow.getmaxyx()
    limit = min(maxy, len(self.textBuffer.lines)-self.textBuffer.scrollRow)
    for i in range(limit):
      self.leftColumn.addStr(i, 0,
          ' %5d  '%(self.textBuffer.scrollRow+i+1), self.leftColumn.color)
    for i in range(limit, maxy):
      self.leftColumn.addStr(i, 0,
          '       ', self.leftColumn.color)
    if 1:
      cursorAt = self.textBuffer.cursorRow-self.textBuffer.scrollRow
      self.leftColumn.addStr(cursorAt, 1,
          '%5d'%(self.textBuffer.cursorRow+1), self.leftColumn.colorSelected)
    self.leftColumn.cursorWindow.refresh()

  def drawRightEdge(self):
    """Draw makers to indicate text extending past the right edge of the
    window."""
    maxy, maxx = self.cursorWindow.getmaxyx()
    limit = min(maxy, len(self.textBuffer.lines)-self.textBuffer.scrollRow)
    for i in range(limit):
      color = self.rightColumn.color
      if len(self.textBuffer.lines[
          i+self.textBuffer.scrollRow])-self.textBuffer.scrollCol > maxx:
        color = self.rightColumn.colorSelected
      self.rightColumn.addStr(i, 0, ' ', color)
    for i in range(limit, maxy):
      self.rightColumn.addStr(i, 0, ' ', self.leftColumn.color)
    self.rightColumn.cursorWindow.refresh()

  def refresh(self):
    Window.refresh(self)
    if self.showLineNumbers:
      self.drawLineNumbers()
    self.drawRightEdge()
    self.cursorWindow.refresh()

  def setTextBuffer(self, textBuffer):
    self.prg.log('setTextBuffer')
    self.controller.setTextBuffer(textBuffer)
    Window.setTextBuffer(self, textBuffer)
    self.textBuffer.debugRedo = self.prg.debugRedo

  def unfocus(self):
    self.statusLine.cursorWindow.addstr(0, 0, ".")
    self.statusLine.refresh()


class PaletteWindow(Window):
  """A window with example foreground and background text colors."""
  def __init__(self, prg):
    Window.__init__(self, prg, 16, 16*5, 8, 8);
    self.controller = app.editor.MainController(prg, self)
    textBuffer = app.text_buffer.TextBuffer(self.prg)
    self.controller.setTextBuffer(textBuffer)
    Window.setTextBuffer(self, textBuffer)

  def draw(self):
    width = 16
    rows = 16
    for i in range(width):
      for k in range(rows):
        self.addStr(k, i*5, ' %3d '%(i+k*width,), curses.color_pair(i+k*width))
    self.cursorWindow.refresh()

  def refresh(self):
    self.draw()

