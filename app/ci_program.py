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

import cProfile
import pstats
import cPickle as pickle
import curses
import locale
import io
import os
import StringIO
import sys
import time
import traceback

import app.background
import app.curses_util
import app.help
import app.history
import app.log
import app.prefs
import app.program_window
import app.window


userConsoleMessage = None
def userMessage(*args):
  global userConsoleMessage
  if not userConsoleMessage:
    userConsoleMessage = ''
  args = [str(i) for i in args]
  userConsoleMessage += unicode(' '.join(args) + '\n')


class CiProgram:
  """This is the main editor program. It holds top level information and runs
  the main loop. The CiProgram is intended as a singleton.
  The program interacts with a single top-level ProgramWindow."""
  def __init__(self, cursesScreen):
    self.clicks = 0
    self.debugMouseEvent = (0, 0, 0, 0, 0)
    self.exiting = False
    self.cursesScreen = cursesScreen
    self.ch = 0
    curses.mousemask(-1)
    curses.mouseinterval(0)
    # Enable mouse tracking in xterm.
    sys.stdout.write('\033[?1002;h\n')
    #sys.stdout.write('\033[?1005;h\n')
    curses.meta(1)
    # Access ^c before shell does.
    curses.raw()
    # Enable Bracketed Paste Mode.
    sys.stdout.write('\033[?2004;h\n')
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
    if 1:
      #rows, cols = self.cursesScreen.getmaxyx()
      cursesWindow = self.cursesScreen
      cursesWindow.leaveok(1)  # Don't update cursor position.
      cursesWindow.scrollok(0)
      cursesWindow.timeout(10)
      cursesWindow.keypad(1)
      app.window.mainCursesWindow = cursesWindow
    self.zOrder = []

  def commandLoop(self):
    # Cache the thread setting.
    useBgThread = app.prefs.editor['useBgThread']
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
    # The first render, to get something on the screen.
    if useBgThread:
      self.bg.put((self.programWindow, []))
    else:
      self.render()
    # This is the 'main loop'. Execution doesn't leave this loop until the
    # application is closing down.
    while not self.exiting:
      if useBgThread:
        while self.bg.hasMessage():
          frame = self.bg.get()
          if frame[0] == 'exception':
            for line in frame[1]:
              userMessage(line[:-1])
            self.exiting = True
            return
          self.refresh(frame[0], frame[1])
      elif 1:
        frame = app.render.frame.grabFrame()
        self.refresh(frame[0], frame[1])
      else:
        profile = cProfile.Profile()
        profile.enable()
        self.refresh(frame[0], frame[1])
        profile.disable()
        output = StringIO.StringIO()
        stats = pstats.Stats(profile, stream=output).sort_stats('cumulative')
        stats.print_stats()
        app.log.info(output.getvalue())
      self.mainLoopTime = time.time() - start
      if self.mainLoopTime > self.mainLoopTimePeak:
        self.mainLoopTimePeak = self.mainLoopTime
      # Gather several commands into a batch before doing a redraw.
      # (A performance optimization).
      cmdList = []
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
              paste_end = (
                  curses.ascii.ESC,) + app.curses_util.BRACKETED_PASTE_END
              while tuple(keySequence[-len(paste_end):]) != paste_end:
                #app.log.info('waiting in paste mode')
                n = cursesWindow.getch()
                if n != curses.ERR:
                  keySequence.append(n)
              keySequence = keySequence[:-(len(paste_end))]
              #print 'keySequence', keySequence
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
          if ch == 0 and useBgThread:
            # bg response.
            frame = None
            while self.bg.hasMessage():
              frame = self.bg.get()
              if frame[0] == 'exception':
                for line in frame[1]:
                  userMessage(line[:-1])
                self.exiting = True
                return
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
        if useBgThread:
          self.bg.put((self.programWindow, cmdList))
        else:
          self.programWindow.executeCommandList(cmdList)
          self.render()

  def startup(self):
    """A second init-like function. Called after command line arguments are
    parsed."""
    self.programWindow = app.program_window.ProgramWindow(self)
    top, left = app.window.mainCursesWindow.getyx()
    rows, cols = app.window.mainCursesWindow.getmaxyx()
    self.programWindow.reshape(top, left, rows, cols)
    self.programWindow.inputWindow.startup()
    self.programWindow.focus()

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
    numColors = min(curses.COLORS, 256)
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
        elif i == '--singleThread':
          app.prefs.editor['useBgThread'] = False
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
        elif i == '--keys':
          userMessage(app.help.docs['key bindings'])
          self.quitNow()
        elif i == '--clearHistory':
          app.history.clearUserHistory()
          self.quitNow()
        elif i == '--eightColors':
          numColors = 8
        elif i == '--version':
          userMessage(app.help.docs['version'])
          self.quitNow()
        elif i.startswith('--'):
          userMessage("unknown command line argument", i)
          self.quitNow()
        continue
      if i == '-':
        readStdin = True
      else:
        cliFiles.append({'path': unicode(i)})
    app.prefs.init()
    app.prefs.startup = {
      'debugRedo': debugRedo,
      'showLogWindow': showLogWindow,
      'cliFiles': cliFiles,
      'openToLine': openToLine,
      'profile': profile,
      'readStdin': readStdin,
      'timeStartup': timeStartup,
      'numColors': numColors,
    }
    self.showLogWindow = showLogWindow

  def quitNow(self):
    """Set the intent to exit the program. The actual exit will occur a bit
    later."""
    app.log.info()
    self.exiting = True

  def refresh(self, drawList, cursor):
    """Paint the drawList to the screen in the main thread."""
    # Ask curses to hold the back buffer until curses refresh().
    cursesWindow = app.window.mainCursesWindow
    cursesWindow.noutrefresh()
    curses.curs_set(0)  # Hide cursor.
    for i in drawList:
      try:
        cursesWindow.addstr(*i)
      except:
        #app.log.error('failed to draw', repr(i))
        pass
    if cursor is not None:
      curses.curs_set(1)  # Show cursor.
      try:
        cursesWindow.leaveok(0)  # Do update cursor position.
        cursesWindow.move(cursor[0], cursor[1])  # Move cursor.
        # Calling refresh will draw the cursor.
        cursesWindow.refresh()
        cursesWindow.leaveok(1)  # Don't update cursor position.
      except:
        pass

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
    except Exception as e:
      app.log.exception(e)

  def run(self):
    self.parseArgs()
    self.setUpPalette()
    homePath = app.prefs.prefs['userData'].get('homePath')
    self.makeHomeDirs(homePath)
    app.curses_util.hackCursesFixes()
    if app.prefs.editor['useBgThread']:
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
    if app.prefs.editor['useBgThread']:
      self.bg.put((self.programWindow, 'quit'))
      self.bg.join()

  def setUpPalette(self):
    def applyPalette(name):
      palette = app.prefs.palette[name]
      foreground = palette['foregroundIndexes']
      background = palette['backgroundIndexes']
      for i in range(1, app.prefs.startup['numColors']):
        curses.init_pair(i, foreground[i], background[i])
    def twoTries(primary, fallback):
      try:
        applyPalette(primary)
      except:
        try:
          applyPalette(fallback)
        except:
          pass
    app.color.colors = app.prefs.startup['numColors']
    if app.prefs.startup['numColors'] == 8:
      app.prefs.prefs['color'] = app.prefs.color = app.prefs.color8
      twoTries(app.prefs.editor['palette8'], 'default8')
    elif app.prefs.startup['numColors'] == 256:
      app.prefs.prefs['color'] = app.prefs.color = app.prefs.color256
      twoTries(app.prefs.editor['palette'], 'default')
    else:
      raise Exception('unknown palette color count ' +
                      repr(app.prefs.startup['numColors']))

  if 1:  # For unit tests/debugging.
    def debugWindowOrder(self):
      app.log.info('debugWindowOrder')
      def recurse(list, indent):
        for i in list:
          app.log.info(indent, i)
          recurse(i.zOrder, indent + '  ')
      recurse(self.zOrder, '  ')
      app.log.info('top window', self.topWindow())

    def getSelection(self):
      """This is primarily for testing."""
      tb = self.programWindow.focusedWindow.textBuffer
      return (tb.penRow, tb.penCol, tb.markerRow, tb.markerCol, tb.selectionMode)

    def topWindow(self):
      top = self
      while len(top.zOrder):
        top = top.zOrder[-1]
      return top

def wrapped_ci(cursesScreen):
  try:
    prg = CiProgram(cursesScreen)
    prg.run()
  except Exception:
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
    sys.stdout.write('\033[?2004l\n')
  global userConsoleMessage
  if userConsoleMessage:
    fullPath = os.path.expanduser(os.path.expandvars(
        '~/.ci_edit/userConsoleMessage'))
    with io.open(fullPath, 'w+') as f:
      f.write(userConsoleMessage)
    sys.stdout.write(userConsoleMessage + '\n')

if __name__ == '__main__':
  run_ci()
