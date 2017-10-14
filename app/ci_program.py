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


import app.background
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
import locale
import StringIO
import time
import traceback


userConsoleMessage = None
def userMessage(*args):
  global userConsoleMessage
  if not userConsoleMessage:
    userConsoleMessage = ''
  args = [str(i) for i in args]
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
    # Enable Bracketed Paste Mode.
    print '\033[?2004;h'
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
    if 1:
      rows, cols = self.cursesScreen.getmaxyx()
      cursesWindow = self.cursesScreen
      cursesWindow.leaveok(1)  # Don't update cursor position.
      cursesWindow.scrollok(0)
      cursesWindow.timeout(10)
      cursesWindow.keypad(1)
      self.top, self.left = cursesWindow.getyx()
      self.rows, self.cols = cursesWindow.getmaxyx()
      app.window.mainCursesWindow = cursesWindow
    self.zOrder = []

  def commandLoop(self):
    # At startup, focus the main window (just to start somewhere).
    self.focusedWindow = self.zOrder[-1]
    self.focusedWindow.focus()
    # Track the time needed to handle commands and render the UI.
    # (A performance measurement).
    self.mainLoopTime = 0
    self.mainLoopTimePeak = 0
    cursesWindow = app.window.mainCursesWindow
    if app.prefs.startup['timeStartup']:
      # When running a timing of the application startup, push a CTRL_Q onto the
      # curses event messages to simulate a full startup with a GUI render.
      curses.ungetch(17)
    start = time.time()
    self.bg.put((self, []))
    #frame = self.bg.get()
    # This is the 'main loop'. Execution doesn't leave this loop until the
    # application is closing down.
    while not self.exiting:
      if 0:
        profile = cProfile.Profile()
        profile.enable()
        self.refresh(frame[0], frame[1])
        profile.disable()
        output = StringIO.StringIO()
        stats = pstats.Stats(profile, stream=output).sort_stats('cumulative')
        stats.print_stats()
        app.log.info(output.getvalue())
      else:
        while self.bg.hasMessage():
          frame = self.bg.get()
          if type(frame) == type("") and frame == 'quit':
            self.exiting = True
            return
          self.refresh(frame[0], frame[1])
      self.mainLoopTime = time.time() - start
      if self.mainLoopTime > self.mainLoopTimePeak:
        self.mainLoopTimePeak = self.mainLoopTime
      # Gather several commands into a batch before doing a redraw.
      # (A performance optimization).
      cmdList = []
      mouseEvents = []
      while not len(cmdList):
        for i in range(5):
          eventInfo = None
          if self.exiting:
            return
          ch = cursesWindow.getch()
          if ch == curses.ascii.ESC:
            # Some keys are sent from the terminal as a sequence of bytes
            # beginning with an Escape character. To help reason about these
            # events (and apply event handler callback functions) the sequence
            # is converted into tuple.
            keySequence = []
            n = cursesWindow.getch()
            while n != curses.ERR:
              keySequence.append(n)
              n = cursesWindow.getch()
            #app.log.info('sequence\n', keySequence)
            # Check for Bracketed Paste Mode begin.
            paste_begin = app.curses_util.BRACKETED_PASTE_BEGIN
            if tuple(keySequence[:len(paste_begin)]) == paste_begin:
              ch = app.curses_util.BRACKETED_PASTE
              keySequence = keySequence[len(paste_begin):]
              paste_end = app.curses_util.BRACKETED_PASTE_END
              while tuple(keySequence[-len(paste_end):]) != paste_end:
                #app.log.info('waiting in paste mode')
                n = cursesWindow.getch()
                while n != curses.ERR:
                  keySequence.append(n)
                  n = cursesWindow.getch()
              keySequence = keySequence[:-(1 + len(paste_end))]
              eventInfo = ''.join([chr(i) for i in keySequence])
            else:
              ch = tuple(keySequence)
            if not ch:
              # The sequence was empty, so it looks like this Escape wasn't
              # really the start of a sequence and is instead a stand-alone
              # Escape. Just forward the esc.
              ch = curses.ascii.ESC
          elif 160 <= ch < 257:
            # Start of utf-8 character.
            u = None
            if (ch & 0xe0) == 0xc0:
              # Two byte utf-8.
              b = cursesWindow.getch()
              u = (chr(ch) + chr(b)).decode("utf-8")
            elif (ch & 0xf0) == 0xe0:
              # Three byte utf-8.
              b = cursesWindow.getch()
              c = cursesWindow.getch()
              u = (chr(ch) + chr(b) + chr(c)).decode("utf-8")
            elif (ch & 0xf8) == 0xf0:
              # Four byte utf-8.
              b = cursesWindow.getch()
              c = cursesWindow.getch()
              d = cursesWindow.getch()
              u = (chr(ch) + chr(b) + chr(c) + chr(d)).decode("utf-8")
            assert u is not None
            eventInfo = u
            ch = app.curses_util.UNICODE_INPUT
          if ch == 0:
            # bg response.
            frame = None
            while self.bg.hasMessage():
              frame = self.bg.get()
            if frame is not None:
              self.refresh(frame[0], frame[1])
          elif ch != curses.ERR:
            self.ch = ch
            if ch == curses.KEY_MOUSE:
              # On Ubuntu, Gnome terminal, curses.getmouse() may only be called
              # once for each KEY_MOUSE. Subsequent calls will throw an
              # exception. So getmouse is (only) called here and other parts of
              # the code use the eventInfo list instead of calling getmouse.
              self.debugMouseEvent = curses.getmouse()
              eventInfo = (self.debugMouseEvent, time.time())
            cmdList.append((ch, eventInfo))
      start = time.time()
      if len(cmdList):
        if 10:
          #app.log.info(len(cmdList))
          self.bg.put((self, cmdList))
        else:
          self.executeCommandList(cmdList)
          self.render()

  def executeCommandList(self, cmdList):
    for cmd, eventInfo in cmdList:
      if cmd == curses.KEY_RESIZE:
        self.handleScreenResize(self.focusedWindow)
        continue
      self.focusedWindow.controller.doCommand(cmd, eventInfo)
      if cmd == curses.KEY_MOUSE:
        self.handleMouse(eventInfo)
      self.focusedWindow.controller.onChange()

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
      self.debugWindow = app.window.ViewWindow(self)
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
    rows, cols = self.rows, self.cols
    #app.log.detail('layout', rows, cols)
    if self.showLogWindow:
      inputWidth = min(88, cols)
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
    y, x = win.top, win.left
    maxRow, maxCol = win.rows, win.cols
    self.debugWindow.writeLineRow = 0
    intent = "noIntent"
    try: intent = win.userIntent
    except: pass
    color = app.color.get('debug_window')
    self.debugWindow.writeLine(
        "   cRow %3d    cCol %2d goalCol %2d  %s"
        %(win.textBuffer.penRow, win.textBuffer.penCol, win.textBuffer.goalCol,
            intent),
        color)
    self.debugWindow.writeLine(
        "   pRow %3d    pCol %2d chRow %4d"
        %(textBuffer.penRow, textBuffer.penCol, textBuffer.sentUpperChangedRow),
        color)
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
            textBuffer.parserTime), color)
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
    redoColorA = app.color.get(100)
    self.debugWindow.writeLine(
        "redoIndex %3d savedAt %3d depth %3d"
        %(textBuffer.redoIndex, textBuffer.savedAtRedoIndex,
          len(textBuffer.redoChain)),
        redoColorA)
    lenChain = textBuffer.redoIndex
    redoColorB = app.color.get(101)
    for i in range(textBuffer.redoIndex - 5, textBuffer.redoIndex):
      text = i >= 0 and textBuffer.redoChain[i] or ''
      self.debugWindow.writeLine(text, redoColorB)
    redoColorC = app.color.get(1)
    for i in range(textBuffer.redoIndex, textBuffer.redoIndex + 4):
      text = (i < len(textBuffer.redoChain) and
          textBuffer.redoChain[i] or '')
      self.debugWindow.writeLine(text, redoColorC)

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
      app.log.debug('before change focus')
      window.changeFocusTo(window)
      app.log.debug('after change focus')
    mouseRow -= window.top
    mouseCol -= window.left
    app.log.mouse(mouseRow, mouseCol)
    app.log.mouse("\n", window)
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

  def handleScreenResize(self, window):
    #app.log.debug('handleScreenResize -----------------------')
    if sys.platform == 'darwin':
      # Some terminals seem to resize the terminal and others leave it
      # to the application to resize the curses terminal.
      rows, cols = app.curses_util.terminalSize()
      curses.resizeterm(rows, cols)
    self.layout()
    window.controller.onChange()
    self.render()
    self.top, self.left = app.window.mainCursesWindow.getyx()
    self.rows, self.cols = app.window.mainCursesWindow.getmaxyx()
    self.layout()

  def parseArgs(self):
    """Interpret the command line arguments."""
    debugRedo = False
    showLogWindow = False
    cliFiles = []
    openToLine = None
    profile = False
    readStdin = False
    takeAll = False  # Take all args as file paths.
    timeStartup = False
    for i in sys.argv[1:]:
      if not takeAll and i[:1] == '+':
        openToLine = int(i[1:])
        continue
      if not takeAll and i[:2] == '--':
        if i == '--debugRedo':
          debugRedo = True
        elif i == '--profile':
          profile = True
        elif i == '--log':
          showLogWindow = True
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
          app.log.channelEnable('startup', True)
        elif i == '--timeStartup':
          timeStartup = True
        elif i == '--':
          # All remaining args are file paths.
          takeAll = True
        elif i == '--help':
          userMessage(app.help.docs['command line'])
          self.quitNow()
        elif i == '--version':
          userMessage(app.help.docs['version'])
          self.quitNow()
        elif i == '--clearHistory':
          app.history.clearUserHistory()
          self.quitNow()
        elif i.startswith('--'):
          userMessage("unknown command line argument", i)
          self.quitNow()
        continue
      if i == '-':
        readStdin = True
      else:
        cliFiles.append({'path': i})
    app.prefs.init()
    app.prefs.startup = {
      'debugRedo': debugRedo,
      'showLogWindow': showLogWindow,
      'cliFiles': cliFiles,
      'openToLine': openToLine,
      'profile': profile,
      'readStdin': readStdin,
      'timeStartup': timeStartup,
    }
    self.showLogWindow = showLogWindow

  def quit(self):
    """Determine whether it's ok to quit. quitNow() will be called if it
        looks ok to quit."""
    app.log.info()
    assert False
    self.exiting = True

  def quitNow(self):
    """Set the intent to exit the program. The actual exit will occur a bit
    later."""
    app.log.info()
    self.exiting = True

  def refresh(self, drawList, cursor):
    """Repaint stacked windows, furthest to nearest in the main thread."""
    # Ask curses to hold the back buffer until curses refresh().
    cursesWindow = app.window.mainCursesWindow
    cursesWindow.noutrefresh()
    curses.curs_set(0)
    #drawList, cursor = app.render.frame.grabFrame()
    for i in drawList:
      try:
        cursesWindow.addstr(*i)
      except:
        #app.log.error('failed to draw', repr(i))
        pass
    if cursor is not None:
      curses.curs_set(1)
      try:
        cursesWindow.leaveok(0)  # Do update cursor position.
        cursesWindow.move(cursor[0], cursor[1])
        # Calling refresh will draw the cursor.
        cursesWindow.refresh()
        cursesWindow.leaveok(1)  # Don't update cursor position.
      except:
        pass

  def render(self):
    """Repaint stacked windows, furthest to nearest in the background thread."""
    if self.showLogWindow:
      self.logWindow.render()
    for i,k in enumerate(self.zOrder):
      #app.log.info("[[%d]] %r"%(i, k))
      k.render()

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
    except Exception, e:
      app.log.error('exception in makeHomeDirs')

  def run(self):
    self.parseArgs()
    homePath = app.prefs.prefs['userData'].get('homePath')
    self.makeHomeDirs(homePath)
    app.curses_util.hackCursesFixes()
    self.bg = app.background.startupBackground()
    self.startup()
    if app.prefs.startup.get('profile'):
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
    self.bg.put((self, 'quit'))
    self.bg.join()

  def setUpPalette(self):
    def applyPalette(name):
      palette = app.prefs.palette[name]
      foreground = palette['foregroundIndexes']
      background = palette['backgroundIndexes']
      for i in range(1, curses.COLORS):
        curses.init_pair(i, foreground[i], background[i])
    def twoTries(primary, fallback):
      try:
        applyPalette(primary)
      except:
        try:
          applyPalette(fallback)
        except:
          pass
    if curses.COLORS == 8:
      app.prefs.prefs['color'] = app.prefs.color8
      app.prefs.color = app.prefs.color8
      app.color.colors = 8
      twoTries(app.prefs.editor['palette8'], 'default8')
    elif curses.COLORS == 256:
      app.prefs.prefs['color'] = app.prefs.color256
      app.prefs.color = app.prefs.color256
      app.color.colors = 256
      twoTries(app.prefs.editor['palette'], 'default')

def wrapped_ci(cursesScreen):
  try:
    prg = CiProgram(cursesScreen)
    prg.run()
  except Exception, e:
    userMessage('---------------------------------------')
    userMessage('Super sorry, something went very wrong.')
    userMessage('Please create a New Issue and paste this info there.\n')
    errorType, value, tracebackInfo = sys.exc_info()
    out = traceback.format_exception(errorType, value, tracebackInfo)
    for i in out:
      userMessage(i[:-1])
      #app.log.error(i[:-1])

def run_ci():
  locale.setlocale(locale.LC_ALL, '')
  try:
    # Reduce the delay waiting for escape sequences.
    os.environ.setdefault('ESCDELAY', '1')
    curses.wrapper(wrapped_ci)
  finally:
    app.log.flush()
    app.log.writeToFile('~/.ci_edit/recentLog')
    # Disable Bracketed Paste Mode.
    print '\033[?2004l'
  global userConsoleMessage
  if userConsoleMessage:
    print userConsoleMessage

if __name__ == '__main__':
  run_ci()
