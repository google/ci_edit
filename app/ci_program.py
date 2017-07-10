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


import os
import sys
if os.getenv('CI_EDIT_USE_FAKE_CURSES'):
  # Replace curses with a fake version for testing.
  sys.path = ['test_fake'] + sys.path


import app.bookmarks
import app.curses_util
import app.help
import app.history
import app.log
import app.prefs
import app.text_buffer
import app.window
import cProfile
import pstats
import cPickle as pickle
import curses
import StringIO
import time
import traceback


userConsoleMessage = None
def userMessage(*args):
  global userConsoleMessage
  if not userConsoleMessage:
    userConsoleMessage = ''
  userConsoleMessage += ' '.join(args) + '\n'


class CiProgram:
  """This is the main editor program. It holds top level information and runs
  the main loop. The CiProgram is intended as a singleton.
  In some aspects, the program acts as a top level window, even though it's not
  exactly a window."""
  def __init__(self, cursesScreen):
    self.debugMouseEvent = (0, 0, 0, 0, 0)
    self.exiting = False
    self.modalUi = None
    self.modeStack = []
    self.priorClick = 0
    self.savedMouseWindow = None
    self.savedMouseX = -1
    self.savedMouseY = -1
    self.cursesScreen = cursesScreen
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
        curses.init_color(i, 500, 500, i * 787 % 1000)
      app.log.detail("color_content, after:")
      for i in range(0, curses.COLORS):
        app.log.detail("color", i, ": ", curses.color_content(i))
    self.setUpPalette()
    self.zOrder = []

  def commandLoop(self):
    # At startup, focus the main window (just to start somewhere).
    window = self.zOrder[-1]
    window.focus()
    self.focusedWindow = window
    # Track the time needed to handle commands and render the UI.
    # (A performance measurement).
    self.mainLoopTime = 0
    self.mainLoopTimePeak = 0
    start = time.time()
    # This is the 'main loop'. Execution doesn't leave this loop until the
    # application is closing down.
    while not self.exiting:
      self.refresh()
      self.mainLoopTime = time.time() - start
      if self.mainLoopTime > self.mainLoopTimePeak:
        self.mainLoopTimePeak = self.mainLoopTime
      # Gather several commands into a batch before doing a redraw.
      # (A performance optimization).
      cmdList = []
      mouseEvents = []
      while not len(cmdList):
        for i in range(5):
          ch = window.cursorWindow.getch()
          if ch == curses.ascii.ESC:
            # Some keys are sent from the terminal as a sequence of bytes
            # beginning with an Escape character. To help reason about these
            # events (and apply event handler callback functions) the sequence
            # is converted into tuple.
            keySequence = []
            n = window.cursorWindow.getch()
            while n != curses.ERR:
              keySequence.append(n)
              n = window.cursorWindow.getch()
            #app.log.info('sequence\n', keySequence)
            ch = tuple(keySequence)
            if not ch:
              # The sequence was empty, so it looks like this Escape wasn't
              # really the start of a sequence and is instead a stand-alone
              # Escape. Just forward the esc.
              ch = curses.ascii.ESC
          if ch != curses.ERR:
            self.ch = ch
            if ch == curses.KEY_MOUSE:
              # On Ubuntu, Gnome terminal, curses.getmouse() may only be called
              # once for each KEY_MOUSE. Subsequent calls will throw an
              # exception. So getmouse is (only) called here and other parts of
              # the code use the mouseEvents list instead of calling getmouse.
              self.debugMouseEvent = curses.getmouse()
              mouseEvents.append((self.debugMouseEvent, time.time()))
            cmdList.append(ch)
      start = time.time()
      if len(cmdList):
        for cmd in cmdList:
          if cmd == curses.KEY_RESIZE:
            if sys.platform == 'darwin':
              # Some terminals seem to resize the terminal and others leave it
              # to the application to resize the curses terminal.
              rows, cols = app.curses_util.terminalSize()
              curses.resizeterm(rows, cols)
            self.layout()
            window.controller.onChange()
            self.refresh()
            app.log.debug(self.cursesScreen.getmaxyx(), time.time())
            continue
          window.controller.doCommand(cmd)
          if cmd == curses.KEY_MOUSE:
            self.handleMouse(mouseEvents[0])
            mouseEvents = mouseEvents[1:]
          window = self.focusedWindow
          window.controller.onChange()

  def changeFocusTo(self, changeTo):
    self.focusedWindow.controller.onChange()
    self.focusedWindow.unfocus()
    self.focusedWindow = changeTo
    self.focusedWindow.focus()

  def normalize(self):
    self.presentModal(None)

  def presentModal(self, changeTo, top=0, left=0):
    if self.modalUi is not None:
      #self.modalUi.controller.onChange()
      self.modalUi.hide()
    app.log.info('\n', changeTo)
    self.modalUi = changeTo
    if self.modalUi is not None:
      self.modalUi.moveSizeToFit(top, left)
      self.modalUi.show()

  def startup(self):
    """A second init-like function. Called after command line arguments are
    parsed."""
    if self.showLogWindow:
      self.debugWindow = app.window.StaticWindow(self)
      #self.zOrder += [self.debugWindow]
      self.logWindow = app.window.LogWindow(self)
      #self.zOrder += [self.logWindow]
    else:
      self.debugWindow = None
      self.logWindow = None
      self.paletteWindow = None
    self.paletteWindow = app.window.PaletteWindow(self)
    self.inputWindow = app.window.InputWindow(self)
    self.zOrder.append(self.inputWindow)
    self.layout()
    self.inputWindow.startup()

  def layout(self):
    """Arrange the debug, log, and input windows."""
    rows, cols = self.cursesScreen.getmaxyx()
    #app.log.detail('layout', rows, cols)
    if self.showLogWindow:
      inputWidth = min(80, cols)
      debugWidth = max(cols - inputWidth - 1, 0)
      debugRows = 20
      self.debugWindow.reshape(debugRows, debugWidth, 0,
          inputWidth + 1)
      self.logWindow.reshape(rows - debugRows, debugWidth, debugRows,
          inputWidth + 1)
    else:
      inputWidth = cols
    count = len(self.zOrder)
    eachRows = rows / count
    for i, window in enumerate(self.zOrder[:-1]):
      window.reshape(eachRows, inputWidth, eachRows * i, 0)
    self.zOrder[-1].reshape(rows - eachRows * (count - 1), inputWidth,
        eachRows * (count - 1), 0)

  def debugDraw(self, win):
    """Draw real-time debug information to the screen."""
    if not self.debugWindow:
      return
    textBuffer = win.textBuffer
    y, x = win.cursorWindow.getyx()
    maxRow, maxCol = win.cursorWindow.getmaxyx()
    self.debugWindow.writeLineRow = 0
    intent = "noIntent"
    try: intent = win.userIntent
    except: pass
    color = app.color.get('debug_window')
    color = app.prefs.prefs['color']['debug_window']
    self.debugWindow.writeLine(
        "   cRow %3d    cCol %2d goalCol %2d  %s"
        %(win.cursorRow, win.cursorCol, win.goalCol, intent), color)
    self.debugWindow.writeLine(
        "   pRow %3d    pCol %2d"
        %(textBuffer.penRow, textBuffer.penCol), color)
    self.debugWindow.writeLine(
        " mkrRow %3d  mkrCol %2d sm %d"
        %(textBuffer.markerRow, textBuffer.markerCol,
            textBuffer.selectionMode),
        color)
    self.debugWindow.writeLine(
        "scrlRow %3d scrlCol %2d lines %3d"
        %(win.scrollRow, win.scrollCol, len(textBuffer.lines)),
        color)
    self.debugWindow.writeLine(
        "y %2d x %2d maxRow %d maxCol %d baud %d color %d"
        %(y, x, maxRow, maxCol, curses.baudrate(), curses.can_change_color()),
            color)
    screenRows, screenCols = self.cursesScreen.getmaxyx()
    self.debugWindow.writeLine(
        "scr rows %d cols %d mlt %f/%f pt %f"
        %(screenRows, screenCols, self.mainLoopTime, self.mainLoopTimePeak,
            textBuffer.parserTime))
    self.debugWindow.writeLine(
        "ch %3s %s"
        %(self.ch, app.curses_util.cursesKeyName(self.ch) or 'UNKNOWN'),
        color)
    self.debugWindow.writeLine("win %r"%(win,),
        color)
    self.debugWindow.writeLine("win %r"%(self.focusedWindow,),
        color)
    self.debugWindow.writeLine("tb %r"%(textBuffer,),
        color)
    (id, mouseCol, mouseRow, mouseZ, bState) = self.debugMouseEvent
    self.debugWindow.writeLine(
        "mouse id %d, mouseCol %d, mouseRow %d, mouseZ %d"
        %(id, mouseCol, mouseRow, mouseZ), color)
    self.debugWindow.writeLine(
        "bState %s %d"
        %(app.curses_util.mouseButtonName(bState), bState),
            color)
    # Display some of the redo chain.
    self.debugWindow.writeLine(
        "redoIndex %3d savedAt %3d depth %3d"
        %(textBuffer.redoIndex, textBuffer.savedAtRedoIndex,
          len(textBuffer.redoChain)),
        color + 100)
    lenChain = textBuffer.redoIndex
    for i in range(textBuffer.redoIndex - 5, textBuffer.redoIndex):
      text = i >= 0 and textBuffer.redoChain[i] or ''
      self.debugWindow.writeLine(text, 101)
    for i in range(textBuffer.redoIndex, textBuffer.redoIndex + 4):
      text = (i < len(textBuffer.redoChain) and
          textBuffer.redoChain[i] or '')
      self.debugWindow.writeLine(text, 1)
    # Refresh the display.
    self.debugWindow.cursorWindow.refresh()

  def debugWindowOrder(self):
    app.log.info('debugWindowOrder')
    def recurse(list, indent):
      for i in list:
        app.log.info(indent, i)
        recurse(i.zOrder, indent + '  ')
    recurse(self.zOrder, '  ')
    app.log.info('top window', self.topWindow())

  def topWindow(self):
    top = self
    while len(top.zOrder):
      top = top.zOrder[-1]
    return top

  def clickedNearby(self, row, col):
    y, x = self.priorClickRowCol
    return y - 1 <= row <= y + 1 and x - 1 <= col <= x + 1

  def handleMouse(self, info):
    """Mouse handling is a special case. The getch() curses function will
    signal the existence of a mouse event, but the event must be fetched and
    parsed separately."""
    (id, mouseCol, mouseRow, mouseZ, bState) = info[0]
    app.log.mouse()
    eventTime = info[1]
    rapidClickTimeout = .5
    def findWindow(parent, mouseRow, mouseCol):
      for window in reversed(parent.zOrder):
        if window.contains(mouseRow, mouseCol):
          return findWindow(window, mouseRow, mouseCol)
      return parent
    window = findWindow(self, mouseRow, mouseCol)
    if window == self:
      app.log.mouse('click landed on screen')
      return
    if self.focusedWindow != window and window.isFocusable:
      window.changeFocusTo(window)
    mouseRow -= window.top
    mouseCol -= window.left
    app.log.mouse(mouseRow, mouseCol)
    app.log.mouse("\n",window)
    #app.log.info('bState', app.curses_util.mouseButtonName(bState))
    if bState & curses.BUTTON1_RELEASED:
      app.log.mouse(bState, curses.BUTTON1_RELEASED)
      if self.priorClick + rapidClickTimeout <= eventTime:
        window.mouseRelease(mouseRow, mouseCol, bState&curses.BUTTON_SHIFT,
            bState&curses.BUTTON_CTRL, bState&curses.BUTTON_ALT)
    elif bState & curses.BUTTON1_PRESSED:
      if (self.priorClick + rapidClickTimeout > eventTime and
          self.clickedNearby(mouseRow, mouseCol)):
        self.clicks += 1
        self.priorClick = eventTime
        if self.clicks == 2:
          window.mouseDoubleClick(mouseRow, mouseCol,
              bState&curses.BUTTON_SHIFT, bState&curses.BUTTON_CTRL,
              bState&curses.BUTTON_ALT)
        else:
          window.mouseTripleClick(mouseRow, mouseCol,
              bState&curses.BUTTON_SHIFT, bState&curses.BUTTON_CTRL,
              bState&curses.BUTTON_ALT)
          self.clicks = 1
      else:
        self.clicks = 1
        self.priorClick = eventTime
        self.priorClickRowCol = (mouseRow, mouseCol)
        window.mouseClick(mouseRow, mouseCol, bState&curses.BUTTON_SHIFT,
            bState&curses.BUTTON_CTRL, bState&curses.BUTTON_ALT)
    elif bState & curses.BUTTON2_PRESSED:
      window.mouseWheelUp(bState&curses.BUTTON_SHIFT,
          bState&curses.BUTTON_CTRL, bState&curses.BUTTON_ALT)
    elif bState & curses.BUTTON4_PRESSED:
      if self.savedMouseX == mouseCol and self.savedMouseY == mouseRow:
        window.mouseWheelDown(bState&curses.BUTTON_SHIFT,
            bState&curses.BUTTON_CTRL, bState&curses.BUTTON_ALT)
      else:
        if self.savedMouseWindow and self.savedMouseWindow is not window:
          mouseRow += window.top - self.savedMouseWindow.top
          mouseCol += window.left - self.savedMouseWindow.left
          window = self.savedMouseWindow
        window.mouseMoved(mouseRow, mouseCol, bState&curses.BUTTON_SHIFT,
            bState&curses.BUTTON_CTRL, bState&curses.BUTTON_ALT)
    elif bState & curses.REPORT_MOUSE_POSITION:
      #app.log.mouse('REPORT_MOUSE_POSITION')
      if self.savedMouseX == mouseCol and self.savedMouseY == mouseRow:
        # This is a hack for dtterm on Mac OS X.
        window.mouseWheelUp(bState&curses.BUTTON_SHIFT,
            bState&curses.BUTTON_CTRL, bState&curses.BUTTON_ALT)
      else:
        if self.savedMouseWindow and self.savedMouseWindow is not window:
          mouseRow += window.top - self.savedMouseWindow.top
          mouseCol += window.left - self.savedMouseWindow.left
          window = self.savedMouseWindow
        window.mouseMoved(mouseRow, mouseCol, bState&curses.BUTTON_SHIFT,
            bState&curses.BUTTON_CTRL, bState&curses.BUTTON_ALT)
    else:
      app.log.mouse('got bState', app.curses_util.mouseButtonName(bState),
          bState)
    self.savedMouseWindow = window
    self.savedMouseX = mouseCol
    self.savedMouseY = mouseRow

  def handleScreenResize(self):
    app.log.debug('handleScreenResize -----------------------')
    self.layout()

  def parseArgs(self):
    """Interpret the command line arguments."""
    self.debugRedo = False
    self.showLogWindow = False
    self.cliFiles = []
    self.openToLine = None
    self.profile = False
    self.readStdin = False
    takeAll = False  # Take all args as file paths.
    for i in sys.argv[1:]:
      if not takeAll and i[:1] == '+':
        self.openToLine = int(i[1:])
        continue
      if not takeAll and i[:2] == '--':
        if i == '--debugRedo':
          self.debugRedo = True
        elif i == '--profile':
          self.profile = True
        elif i == '--log':
          self.showLogWindow = True
        elif i == '--d':
          app.log.channelEnable('debug', True)
        elif i == '--m':
          app.log.channelEnable('mouse', True)
        elif i == '--p':
          app.log.channelEnable('info', True)
          app.log.channelEnable('debug', True)
          app.log.channelEnable('detail', True)
          app.log.channelEnable('error', True)
        elif i == '--parser':
          app.log.channelEnable('parser', True)
        elif i == '--startup':
          app.log.channelEnable('startup', logStartup)
        elif i == '--':
          # All remaining args are file paths.
          takeAll = True
        elif i == '--help':
          userMessage(app.help.docs['command line'])
          self.quitNow()
          return
        elif i == '--version':
          userMessage(app.help.docs['version'])
          self.quitNow()
          return
        elif i.startswith('--'):
          userMessage("unknown command line argument", i)
          self.quitNow()
          return
        continue
      if i == '-':
        self.readStdin = True
      else:
        self.cliFiles.append({'path': i})
    app.prefs.init()

  def quit(self):
    """Determine whether it's ok to quit. quitNow() will be called if it
        looks ok to quit."""
    app.log.info('self.exiting = True')
    self.exiting = True

  def quitNow(self):
    """Set the intent to exit the program. The actual exit will occur a bit
    later."""
    app.log.info('self.exiting = True')
    self.exiting = True

  def refresh(self):
    """Repaint stacked windows, furthest to nearest."""
    curses.curs_set(0)
    if self.showLogWindow:
      self.logWindow.refresh()
    for i,k in enumerate(self.zOrder):
      #app.log.info("[[%d]] %r"%(i, k))
      k.refresh()
    if k.shouldShowCursor:
      curses.curs_set(1)

  def makeHomeDirs(self, homePath):
    try:
      if not os.path.isdir(homePath):
        os.makedirs(homePath)
      self.dirBackups = os.path.join(homePath, 'backups')
      if not os.path.isdir(self.dirBackups):
        os.makedirs(self.dirBackups)
      self.dirPrefs = os.path.join(homePath, 'prefs')
      if not os.path.isdir(self.dirPrefs):
        os.makedirs(self.dirPrefs)
      app.history.path = os.path.join(homePath, app.history.path)
    except Exception, e:
      app.log.error('exception in makeHomeDirs')

  def run(self):
    self.parseArgs()
    homePath = os.path.expanduser('~/.ci_edit')
    self.makeHomeDirs(homePath)
    app.bookmarks.loadUserBookmarks(os.path.join(homePath, 'bookmarks.dat'))
    app.history.loadUserHistory(os.path.join(homePath, 'history.dat'))
    app.curses_util.hackCursesFixes()
    self.startup()
    if self.profile:
      profile = cProfile.Profile()
      profile.enable()
      self.commandLoop()
      profile.disable()
      output = StringIO.StringIO()
      stats = pstats.Stats(profile, stream=output).sort_stats('cumulative')
      stats.print_stats()
      app.log.info(output.getvalue())
    else:
      self.commandLoop()
    app.history.saveUserHistory()
    app.bookmarks.saveUserBookmarks()

  def setUpPalette(self):
    def applyPalette(name):
      palette = app.prefs.prefs['palette'][name]
      foreground = palette['foregroundIndexes']
      background = palette['backgroundIndexes']
      cycle = len(foreground)
      for i in range(1, curses.COLORS):
        curses.init_pair(i, foreground[i % cycle], background[i / cycle])
    try:
      applyPalette(app.prefs.prefs['editor']['palette'])
    except:
      applyPalette('default')

def wrapped_ci(cursesScreen):
  try:
    prg = CiProgram(cursesScreen)
    prg.run()
  except Exception, e:
    errorType, value, tracebackInfo = sys.exc_info()
    out = traceback.format_exception(errorType, value, tracebackInfo)
    for i in out:
      app.log.error(i[:-1])

def run_ci():
  try:
    # Reduce the delay waiting for escape sequences.
    os.environ.setdefault('ESCDELAY', '1')
    curses.wrapper(wrapped_ci)
  finally:
    app.log.flush()
    app.log.writeToFile('~/.ci_edit/recentLog')
  global userConsoleMessage
  if userConsoleMessage:
    print userConsoleMessage

if __name__ == '__main__':
  run_ci()

