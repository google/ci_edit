#!/usr/bin/python
# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.curses_util
import app.text_buffer
import app.window
import sys
import curses
import time


globalPrintLog = "--- begin log ---\n"
shouldWritePrintLog = False


def logPrint(*args):
  global globalPrintLog
  msg = str(args[0])
  for i in args[1:]:
    msg += ' '+str(i)
  globalPrintLog += msg + "\n"


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
    # Access ^c before shell does.
    curses.raw()
    #curses.start_color()
    curses.use_default_colors()
    if 0:
      assert(curses.COLORS == 256)
      assert(curses.can_change_color() == 1)
      assert(curses.has_colors() == 1)
      logPrint("color_content:")
      for i in range(0, curses.COLORS):
        logPrint("color", i, ": ", curses.color_content(i))
      for i in range(16, curses.COLORS):
        curses.init_color(i, 500, 500, i*787%1000)
      logPrint("color_content, after:")
      for i in range(0, curses.COLORS):
        logPrint("color", i, ": ", curses.color_content(i))
    self.showPalette = 0
    self.shiftPalette()

    self.zOrder = []

  def startup(self):
    """A second init-like function. Called after command line arguments are
    parsed."""
    if self.showLogWindow:
      self.debugWindow = app.window.StaticWindow(self, 0, 1, 0, 0)
      self.zOrder += [self.debugWindow]
      self.logWindow = app.window.Window(self, 1, 1, 0, 0)
      self.logWindow.setTextBuffer(app.text_buffer.TextBuffer(self))
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
    #logPrint('layout', rows, cols)
    if self.showLogWindow:
      inputWidth = min(78, cols)
      debugWidth = max(cols-inputWidth-1, 0)
      debugRows = 10
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
        %(self.ch, app.curses_util.cursesKeyName(self.ch)),
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
          %(app.curses_util.mouseButtonName(bstate), bstate),
          self.debugWindow.color)
    except curses.error:
      self.debugWindow.addStr(6, 0, "mouse is not available.  ",
          self.debugWindow.color)
    self.debugWindow.cursorWindow.refresh()

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

  def logPrint(self, *args):
    logPrint(*args)

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
        global shouldWritePrintLog
        shouldWritePrintLog = shouldWritePrintLog or i == '--logPrint'
        shouldWritePrintLog = shouldWritePrintLog or i == '--p'
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
        win.focus()
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
      light = [-1, 230, 228, 221,   255, 254, 253, 14]
      for i in range(1, curses.COLORS):
        curses.init_pair(i, dark[i%len(dark)], light[i/32])
    elif self.showPalette == 2:
      for i in range(1, curses.COLORS):
        curses.init_pair(i, i, 231)
    else:
      for i in range(1, curses.COLORS):
        curses.init_pair(i, 16, i)

def wrapped_ci(stdscr):
  prg = CiProgram(stdscr)
  prg.run()

def run_ci():
  global globalPrintLog
  curses.wrapper(wrapped_ci)
  if shouldWritePrintLog:
    print globalPrintLog

if __name__ == '__main__':
  run_ci()

