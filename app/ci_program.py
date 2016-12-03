#!/usr/bin/python
# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.buffer_manager
import app.curses_util
import app.log
import app.text_buffer
import app.window
import sys
import curses
import time
import traceback


class CiProgram:
  """This is the main editor program. It holds top level information and runs
  the main loop. The CiProgram is intended as a singleton."""
  def __init__(self, stdscr):
    self.bufferManager = app.buffer_manager.BufferManager()
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
    # Access ^c before shell does.
    curses.raw()
    #curses.start_color()
    curses.use_default_colors()
    if 0:
      assert(curses.COLORS == 256)
      assert(curses.can_change_color() == 1)
      assert(curses.has_colors() == 1)
      app.log.detail("color_content:")
      for i in range(0, curses.COLORS):
        app.log.detail("color", i, ": ", curses.color_content(i))
      for i in range(16, curses.COLORS):
        curses.init_color(i, 500, 500, i*787%1000)
      app.log.detail("color_content, after:")
      for i in range(0, curses.COLORS):
        app.log.detail("color", i, ": ", curses.color_content(i))
    self.showPalette = 0
    self.shiftPalette()

    self.zOrder = []

  def commandLoop(self, window):
    app.log.debug('commandLoop', window)
    while not self.exiting and not self.changeTo:
      window.controller.onChange()
      self.refresh()
      ch = window.cursorWindow.getch()
      if ch == -1:
        self.quit()
      self.ch = ch
      window.controller.doCommand(ch)

  def startup(self):
    """A second init-like function. Called after command line arguments are
    parsed."""
    if self.showLogWindow:
      self.debugWindow = app.window.StaticWindow(self)
      self.zOrder += [self.debugWindow]
      self.logWindow = app.window.LogWindow(self)
      #self.zOrder += [self.logWindow]
    else:
      self.debugWindow = None
      self.logWindow = None
      self.paletteWindow = None
    self.paletteWindow = app.window.PaletteWindow(self)
    self.inputWindow = app.window.InputWindow(self, 10, 10, 0, 0, True, True,
        True)
    self.layout()

  def layout(self):
    """Arrange the debug, log, and input windows."""
    rows, cols = self.stdscr.getmaxyx()
    #app.log.detail('layout', rows, cols)
    if self.showLogWindow:
      inputWidth = min(78, cols)
      debugWidth = max(cols-inputWidth-1, 0)
      debugRows = 15
      self.debugWindow.reshape(debugRows, debugWidth, 0,
          inputWidth+1)
      self.logWindow.reshape(rows-debugRows, debugWidth, debugRows,
          inputWidth+1)
    else:
      inputWidth = cols
    self.inputWindow.reshape(rows, inputWidth, 0, 0)

  def debugDraw(self, win):
    """Draw real-time debug information to the screen."""
    if not self.debugWindow:
      return
    textBuffer = win.textBuffer
    y, x = win.cursorWindow.getyx()
    maxy, maxx = win.cursorWindow.getmaxyx()
    self.debugWindow.writeLineRow = 0
    self.debugWindow.writeLine(
        "   cRow %3d    cCol %2d goalCol %2d"
        %(textBuffer.cursorRow, textBuffer.cursorCol,
          textBuffer.goalCol), self.debugWindow.color)
    self.debugWindow.writeLine(
        " mkrRow %3d  mkrCol %2d sm %d"
        %(textBuffer.markerRow, textBuffer.markerCol,
          textBuffer.selectionMode),
        self.debugWindow.color)
    self.debugWindow.writeLine(
        "scrlRow %3d scrlCol %2d lines %3d"
        %(textBuffer.scrollRow, textBuffer.scrollCol,
          len(textBuffer.lines)),
        self.debugWindow.color)
    self.debugWindow.writeLine(
        "y %2d x %2d maxy %d maxx %d baud %d color %d"
        %(y, x, maxy, maxx, curses.baudrate(), curses.can_change_color()),
        self.debugWindow.color)
    self.debugWindow.writeLine(
        "ch %3s %s"
        %(self.ch, app.curses_util.cursesKeyName(self.ch)),
        self.debugWindow.color)
    self.debugWindow.writeLine("win %r"%(win,),
        self.debugWindow.color)
    self.debugWindow.writeLine("tb %r"%(textBuffer,),
        self.debugWindow.color)
    try:
      (id, mousex, mousey, mousez, bstate) = curses.getmouse()
      self.debugWindow.writeLine(
          "mouse id %d, mousex %d, mousey %d, mousez %d"
          %(id, mousex, mousey, mousez),
          self.debugWindow.color)
      self.debugWindow.writeLine(
          "bstate %s %d"
          %(app.curses_util.mouseButtonName(bstate), bstate),
          self.debugWindow.color)
    except curses.error:
      self.debugWindow.writeLine("mouse is not available.",
          self.debugWindow.color)
    # Display some of the redo chain.
    self.debugWindow.writeLine(
        "redoIndex %3d savedAt %3d depth %3d"
        %(textBuffer.redoIndex, textBuffer.savedAtRedoIndex,
          len(textBuffer.redoChain)),
        self.debugWindow.color+100)
    lenChain = textBuffer.redoIndex
    for i in range(textBuffer.redoIndex-3, textBuffer.redoIndex):
      text = i >= 0 and textBuffer.redoChain[i] or ''
      self.debugWindow.writeLine(text, 101)
    for i in range(textBuffer.redoIndex, textBuffer.redoIndex+2):
      text = i < len(textBuffer.redoChain) and textBuffer.redoChain[i] or ''
      self.debugWindow.writeLine(text, 1)
    # Refresh the display.
    self.debugWindow.cursorWindow.refresh()

  def debugWindowOrder(self):
    self.log('debugWindowOrder')
    def recurse(list, indent):
      for i in list:
        self.log(indent, i)
        recurse(i.zOrder, indent+'  ')
    recurse(self.zOrder, '  ')
    self.log('top window', self.topWindow())

  def topWindow(self):
    top = self
    while len(top.zOrder):
      top = top.zOrder[-1]
    return top

  def clickedNearby(self, row, col):
    y, x = self.priorClickRowCol
    return y-1 <= row <= y+1 and x-1 <= col <= x+1

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
        #self.log('bstate', app.curses_util.mouseButtonName(bstate))
        if bstate & curses.BUTTON1_RELEASED:
          if self.priorClick + rapidClickTimeout <= time.time():
            i.mouseRelease(mousey, mousex, bstate&curses.BUTTON_SHIFT,
                bstate&curses.BUTTON_CTRL, bstate&curses.BUTTON_ALT)
        elif bstate & curses.BUTTON1_PRESSED:
          if (self.priorClick + rapidClickTimeout > time.time() and
              self.clickedNearby(mousey, mousex)):
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
            self.priorClickRowCol = (mousey, mousex)
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
            # This is a hack for dtterm on Mac OS X.
            i.mouseWheelUp(bstate&curses.BUTTON_SHIFT,
                bstate&curses.BUTTON_CTRL, bstate&curses.BUTTON_ALT)
          else:
            i.mouseMoved(mousey, mousex, bstate&curses.BUTTON_SHIFT,
                bstate&curses.BUTTON_CTRL, bstate&curses.BUTTON_ALT)
        else:
          self.log('got bstate', app.curses_util.mouseButtonName(bstate), bstate)
        self.savedMouseX = mousex
        self.savedMouseY = mousey
        return
    self.log('click landed on screen')

  def handleScreenResize(self):
    self.log('handleScreenResize')
    self.layout()

  def log(self, *args):
    """Log text to the logging window (for debugging)."""
    if not self.logWindow:
      return
    app.log.info(*args)

  def parseArgs(self):
    """Interpret the command line arguments."""
    self.debugRedo = False
    self.showLogWindow = False
    self.cliFiles = []
    self.readStdin = False
    takeAll = False
    for i in sys.argv[1:]:
      if not takeAll and i[:2] == '--':
        self.debugRedo = self.debugRedo or i == '--debugRedo'
        self.showLogWindow = self.showLogWindow or i == '--log'
        app.log.shouldWritePrintLog = app.log.shouldWritePrintLog or i == '--logDetail'
        app.log.shouldWritePrintLog = app.log.shouldWritePrintLog or i == '--p'
        if i == '--':
          # All remaining args are file paths.
          takeAll = True
        continue
      if i == '-':
        self.readStdin = True
      else:
        self.cliFiles.append({'path': i})

  def quit(self):
    """Set the intent to exit the program. The actual exit will occur a bit
    later."""
    app.log.info('self.exiting = True')
    self.exiting = True

  def refresh(self):
    """Repaint stacked windows, furthest to nearest."""
    if self.showLogWindow:
      self.logWindow.refresh()
    for i,k in enumerate(self.zOrder):
      #self.log("[[%d]] %r"%(i, k))
      k.refresh()

  def run(self):
    self.parseArgs()
    self.startup()
    self.changeTo = self.inputWindow
    while not self.exiting:
        win = self.changeTo
        self.changeTo = None
        win.refresh()
        win.focus()
        self.commandLoop(win)
        win.unfocus()

  def shiftPalette(self):
    """Test different palette options. Each call to shiftPalette will change the
    palette to the next one in the ring of palettes."""
    self.showPalette = (self.showPalette+1)%3
    if self.showPalette == 1:
      dark = [
        0,   1,   2,   3,    4,   5,  6,  7,    8,  9, 10, 11,   12, 13, 14,  15,
        94, 134,  18, 240, 138,  21, 22, 23,   24, 25, 26, 27,   28, 29, 30,  57,
      ]
      light = [-1, 230, 147, 221,   255, 254, 253, 14]
      for i in range(1, curses.COLORS):
        curses.init_pair(i, dark[i%len(dark)], light[i/32])
    elif self.showPalette == 2:
      for i in range(1, curses.COLORS):
        curses.init_pair(i, i, 231)
    else:
      for i in range(1, curses.COLORS):
        curses.init_pair(i, 16, i)

def wrapped_ci(stdscr):
  try:
    prg = CiProgram(stdscr)
    prg.run()
  except Exception, e:
    errorType, value, tb = sys.exc_info()
    out = traceback.format_exception(errorType, value, tb)
    for i in out:
      app.log.error(i[:-1])

def run_ci():
  try:
    curses.wrapper(wrapped_ci)
  finally:
    app.log.flush()

if __name__ == '__main__':
  run_ci()

