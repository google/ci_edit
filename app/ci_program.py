#!/usr/bin/python
# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.ci_curses
import app.editor
import app.text_buffer
import sys
import curses
import time
import traceback
import os


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

  def show(self):
    """Show window and bring it to the top layer."""
    try: self.prg.zOrder.remove(self)
    except: pass
    self.prg.zOrder.append(self)

  def refresh(self):
    """Redraw window."""
    self.cursorWindow.refresh()


class Window(StaticWindow):
  """A Window may have focus."""
  def __init__(self, prg, rows, cols, top, left):
    StaticWindow.__init__(self, prg, rows, cols, top, left)
    self.rows = rows
    self.cols = cols
    self.top = top
    self.left = left
    self.cursorWindow.keypad(1)
    self.textBuffer = None

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

  def focus(self):
    try: self.prg.zOrder.remove(self)
    except ValueError: self.prg.log('not found')
    self.prg.zOrder.append(self)

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
    self.prg.log('unfocus', repr(self))


class HeaderLine(Window):
  def __init__(self, prg, host, rows, cols, top, left):
    Window.__init__(self, prg, rows, cols, top, left)
    self.setTextBuffer(app.text_buffer.TextBuffer(prg))
    self.controller = app.editor.InteractiveOpener(prg, host, self.textBuffer)

  def focus(self):
    Window.focus(self)
    self.controller.focus()
    self.controller.commandLoop()


class InteractiveFind(Window):
  def __init__(self, prg, host, rows, cols, top, left):
    Window.__init__(self, prg, rows, cols, top, left)
    self.setTextBuffer(app.text_buffer.TextBuffer(prg))
    self.controller = app.editor.InteractiveFind(prg, host, self.textBuffer)

  def focus(self):
    Window.focus(self)
    self.controller.focus()
    self.controller.commandLoop()

  def refresh(self):
    if self.prg.zOrder[-1] is self:
      Window.refresh(self)


class LineNumberVertical(StaticWindow):
  """The left hand column with the line numbers displayed."""
  def __init__(self, prg, host, rows, cols, top, left):
    Window.__init__(self, prg, rows, cols, top, left)
    self.host = host
    self.setTextBuffer(app.text_buffer.TextBuffer(prg))

  def refresh(self):
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


class RightVertical(StaticWindow):
  """There is a thin vertical panel reserved for long line indicators."""
  def __init__(self, prg, host, rows, cols, top, left):
    Window.__init__(self, prg, rows, cols, top, left)
    self.host = host
    self.setTextBuffer(app.text_buffer.TextBuffer(prg))

  def refresh(self):
    pass


class StatusLine(Window):
  """The status line appears at the bottom of the screen. It shows the current
  line and column the cursor is on."""
  def __init__(self, prg, host, rows, cols, top, left):
    Window.__init__(self, prg, rows, cols, top, left)
    self.host = host
    self.setTextBuffer(app.text_buffer.TextBuffer(prg))
    self.controller = app.editor.InteractiveGoto(prg, host, self.textBuffer)

  def focus(self):
    Window.focus(self)
    self.controller.focus()
    self.controller.commandLoop()

  def refresh(self):
    maxy, maxx = self.cursorWindow.getmaxyx()
    if self.prg.zOrder[-1] is self:
      Window.refresh(self)
    else:
      statusLine = ' * '
      rightSide = '%d,%d '%(
          self.host.textBuffer.cursorRow+1, self.host.textBuffer.cursorCol)
      statusLine += ' '*(maxx-len(statusLine)-len(rightSide)) + rightSide
      self.addStr(0, 0, statusLine, self.color)
      self.cursorWindow.refresh()


class DirectoryPanel(Window):
  """A content area panel that shows a file directory list."""
  def __init__(self, prg, rows, cols, top, left):
    self.prg = prg
    Window.__init__(self, prg, rows, cols, top, left)
    self.color = curses.color_pair(0)
    self.colorSelected = curses.color_pair(3)


class FilePanel(Window):
  def __init__(self, prg, rows, cols, top, left):
    self.prg = prg
    Window.__init__(self, prg, rows, cols, top, left)
    self.color = curses.color_pair(0)
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
      self.interactiveFind = InteractiveFind(prg, self, 1, cols, top+rows-1,
          left)
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
      self.rightColumn.color = curses.color_pair(0)
      self.rightColumn.colorSelected = curses.color_pair(105)
      cols -= 1
    Window.__init__(self, prg, rows, cols, top, left)
    self.color = curses.color_pair(0)
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

  def focus(self):
    Window.focus(self)
    self.controller.focus()

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
      self.rightColumn.addStr(i, 0,
          '       ', self.leftColumn.color)
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
    # textBuffer = self.prg.bufferManager.loadTextBuffer(sys.argv[1])
    # self.controller.setTextBuffer(textBuffer)
    # Window.setTextBuffer(self, textBuffer)

  def draw(self):
    width = 16
    rows = 16
    for i in range(width):
      for k in range(rows):
        self.addStr(k, i*5, ' %3d '%(i+k*width,), curses.color_pair(i+k*width))
    self.cursorWindow.refresh()

  def focus(self):
    Window.focus(self)
    self.controller.focus()

  def refresh(self):
    self.draw()


class CiProgram:
  """This is the main editor program. It holds top level information and runs
  the main loop. The CiProgram is intended as a singleton."""
  def __init__(self, stdscr):
    self.bufferManager = app.text_buffer.BufferManager(self)
    self.exiting = False
    self.modeStack = []
    self.priorClick = 0
    self.savedMouseX = -1
    self.savedMouseY = -1
    self.stdscr = stdscr
    self.ch = 0
    curses.mousemask(-1)
    curses.mouseinterval(0)
    # Enable mouse tracking in xterm.
    print '\033[?1002;h'
    #print '\033[?1005;h'
    curses.meta(1)
    curses.raw()
    curses.start_color()
    curses.use_default_colors()
    assert(curses.COLORS == 256)
    assert(curses.can_change_color() == 1)
    assert(curses.has_colors() == 1)
    #for i in range(1, curses.COLORS):
    #  curses.init_color(i, 1000, 0, 0)
    self.showPalette = 0
    self.shiftPalette()

    self.zOrder = []

  def startup(self):
    """A second init-like function. Called after command line arguments are
    parsed."""
    maxy, maxx = self.stdscr.getmaxyx()
    if self.showLogWindow:
      inputWidth = min(78, maxx)
      debugWidth = max(maxx-inputWidth-1, 0)
      debugRows = 10

      self.debugWindow = StaticWindow(self, debugRows, debugWidth, 0,
          inputWidth+1)
      self.zOrder += [
        self.debugWindow,
      ]
      self.logWindow = Window(self, maxy-debugRows, debugWidth, debugRows,
          inputWidth+1)
      self.logWindow.setTextBuffer(app.text_buffer.TextBuffer(self))

      self.paletteWindow = PaletteWindow(self)
    else:
      inputWidth = maxx
      self.debugWindow = None
      self.logWindow = None
      self.paletteWindow = None

    self.inputWindow = InputWindow(self, maxy, inputWidth, 0, 0, True, True,
        True)
    self.log('db', self.debugWindow)
    self.log('in', self.inputWindow)

  def debugDraw(self, win):
    """Draw real-time debug information to the screen."""
    if not self.debugWindow:
      return
    textBuffer = win.textBuffer
    y, x = win.cursorWindow.getyx()
    maxy, maxx = win.cursorWindow.getmaxyx()
    self.debugWindow.addStr(0, 0,
        "debug cRow %3d cCol %3d goalCol %2d lines %3d      "
        %(textBuffer.cursorRow, textBuffer.cursorCol, textBuffer.goalCol,
          len(textBuffer.lines)), self.debugWindow.color)
    self.debugWindow.addStr(1, 0,
        "scrlRow %3d scrlCol %2d mkrRow %3d mkrCol %2d     "
        %(textBuffer.scrollRow, textBuffer.scrollCol, textBuffer.markerRow,
          textBuffer.markerCol), self.debugWindow.color)
    self.debugWindow.addStr(2, 0,
        "y %2d x %2d maxy %d maxx %d baud %d color %d   "
        %(y, x, maxy, maxx, curses.baudrate(), curses.can_change_color()),
        self.debugWindow.color)
    self.debugWindow.addStr(3, 0,
        "ch %3s %s          "
        %(self.ch, curses.keyname(self.ch)),
        self.debugWindow.color)
    self.debugWindow.addStr(4, 0,
        "sm %d win %r    "
        %(textBuffer.selectionMode, win), self.debugWindow.color)
    try:
      (id, mousex, mousey, mousez, bstate) = curses.getmouse()
      self.debugWindow.addStr(6, 0,
          "mouse id %d, mousex %d, mousey %d, mousez %d         "
          %(id, mousex, mousey, mousez),
          self.debugWindow.color)
      self.debugWindow.addStr(7, 0,
          "bstate %s %d         "
          %(app.ci_curses.mouseButtonName(bstate), bstate),
          self.debugWindow.color)
    except curses.error:
      self.debugWindow.addStr(6, 0, "mouse is not available.  ",
          self.debugWindow.color)
    self.debugWindow.cursorWindow.refresh()

  def handleMouse(self):
    """Mouse handling is a special case. The getch() curses function will
    signal the existence of a mouse event, but the event must be fetched and
    parsed separately."""
    (id, mousex, mousey, mousez, bstate) = curses.getmouse()
    rapidClickTimeout = .5
    for i in reversed(self.zOrder):
      if i.contains(mousey, mousex):
        mousey -= i.top
        mousex -= i.left
        #self.log('bstate', app.ci_curses.mouseButtonName(bstate))
        if bstate & curses.BUTTON1_RELEASED:
          if self.priorClick + rapidClickTimeout <= time.time():
            i.mouseRelease(mousey, mousex, bstate&curses.BUTTON_SHIFT,
                bstate&curses.BUTTON_CTRL, bstate&curses.BUTTON_ALT)
        elif bstate & curses.BUTTON1_PRESSED:
          if self.priorClick + rapidClickTimeout > time.time():
            self.clicks += 1
            self.priorClick = time.time()
            if self.clicks == 2:
              i.mouseDoubleClick(mousey, mousex, bstate&curses.BUTTON_SHIFT,
                  bstate&curses.BUTTON_CTRL, bstate&curses.BUTTON_ALT)
            else:
              i.mouseTripleClick(mousey, mousex, bstate&curses.BUTTON_SHIFT,
                  bstate&curses.BUTTON_CTRL, bstate&curses.BUTTON_ALT)
              self.clicks = 1
          else:
            self.clicks = 1
            self.priorClick = time.time()
            i.mouseClick(mousey, mousex, bstate&curses.BUTTON_SHIFT,
                bstate&curses.BUTTON_CTRL, bstate&curses.BUTTON_ALT)
        elif bstate & curses.BUTTON2_PRESSED:
          i.mouseWheelUp(bstate&curses.BUTTON_SHIFT,
              bstate&curses.BUTTON_CTRL, bstate&curses.BUTTON_ALT)
        elif bstate & curses.BUTTON4_PRESSED:
          if self.savedMouseX == mousex and self.savedMouseY == mousey:
            i.mouseWheelDown(bstate&curses.BUTTON_SHIFT,
                bstate&curses.BUTTON_CTRL, bstate&curses.BUTTON_ALT)
          else:
            i.mouseMoved(mousey, mousex, bstate&curses.BUTTON_SHIFT,
                bstate&curses.BUTTON_CTRL, bstate&curses.BUTTON_ALT)
        elif bstate & curses.REPORT_MOUSE_POSITION:
          #self.log('REPORT_MOUSE_POSITION')
          if self.savedMouseX == mousex and self.savedMouseY == mousey:
            i.mouseWheelUp(bstate&curses.BUTTON_SHIFT,
                bstate&curses.BUTTON_CTRL, bstate&curses.BUTTON_ALT)
          else:
            self.log('unhandled REPORT_MOUSE_POSITION')
        else:
          self.log('got bstate', app.ci_curses.mouseButtonName(bstate), bstate)
        self.savedMouseX = mousex
        self.savedMouseY = mousey
        return
    self.log('click landed on screen')

  def logNoRefresh(self, *args):
    """Most code will want the log() function rather than this one. This is
    useful to log information while currently logging information (which would
    otherwise create an unending recursion)."""
    if not self.logWindow:
      return
    msg = str(args[0])
    for i in args[1:]:
      msg += ' '+str(i)
    self.logWindow.textBuffer.addLine(msg)
    self.logWindow.textBuffer.cursorScrollTo(-1, self.logWindow.cursorWindow)

  def log(self, *args):
    """Log text to the logging window (for debugging)."""
    if not self.logWindow:
      return
    self.logNoRefresh(*args)
    self.logWindow.refresh()

  def parseArgs(self):
    """Interpret the command line arguments."""
    self.debugRedo = False
    self.showLogWindow = False
    self.cliFiles = []
    takeAll = False
    for i in sys.argv[1:]:
      if not takeAll and i[:2] == '--':
        self.debugRedo = self.debugRedo or i == '--debugRedo'
        self.showLogWindow = self.showLogWindow or i == '--log'
        if i == '--':
          # All remaining args are file paths.
          takeAll = True
        continue
      self.cliFiles.append({'path': i})

  def quit(self):
    """Set the intent to exit the program. The actual exit will occur a bit
    later."""
    self.exiting = True

  def refresh(self):
    """Repaint stacked windows, furthest to nearest."""
    #self.log('-'*80)
    for i,k in enumerate(self.zOrder):
      #self.log("[[%d]] %r"%(i, k))
      k.refresh()

  def run(self):
    self.parseArgs()
    self.startup()
    self.changeTo = self.inputWindow
    while not self.exiting:
      # try:
        #self.log(self.changeTo.__name__)
        win = self.changeTo
        self.changeTo = None
        win.focus()
        win.unfocus()
      # except:
      #   self.log('exception')

  def shiftPalette(self):
    """Test different palette options. Each call to shiftPalette will change the
    palette to the next one in the ring of palettes."""
    self.showPalette = (self.showPalette+1)%3
    if self.showPalette == 1:
      dark = [
         #1,   2,  3,   4,    5,  7,  8,  9,   10, 11, 57, 12,   12, 13, 14, 15,
         0,   1,   2,   3,    4,  5,  6,  7,    8,  9, 10, 11,   12, 13, 14, 160,
        94, 134,  18, 240,  138, 21, 22, 23,   24, 25, 26, 27,   28, 29, 30, 57,
      ]
      light = [231, 230, 228, 221,   255, 254, 253, 14]
      for i in range(1, curses.COLORS):
        curses.init_pair(i, dark[i%len(dark)], light[i/32])
        #curses.init_pair(i, i, i)
    elif self.showPalette == 2:
      for i in range(1, curses.COLORS):
        curses.init_pair(i, i, 231)
    else:
      for i in range(1, curses.COLORS):
        curses.init_pair(i, 16, i)

def run_ci(stdscr):
  prg = CiProgram(stdscr)
  prg.run()

if __name__ == '__main__':
    curses.wrapper(run_ci)
