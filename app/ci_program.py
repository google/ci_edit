# -*- coding: utf-8 -*-
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
try:
    unicode

    def bytes_to_unicode(chars):
        chars = "".join([chr(i) for i in chars])
        return chars.decode("utf-8")
except NameError:
    unicode = str
    unichr = chr

    def bytes_to_unicode(values):
        return bytes(values).decode("utf-8")


assert bytes_to_unicode((226, 143, 176)) == u'⏰'

import cProfile
import pstats
try:
    import cPickle as pickle
except ImportError:
    import pickle
import curses
import locale
import io
import os
import struct
import sys
import time
import traceback

import app.background
import app.buffer_file
import app.buffer_manager
import app.clipboard
import app.color
import app.curses_util
import app.help
import app.history
import app.log
import app.prefs
import app.program_window
import app.render
import app.spelling
import app.window

userConsoleMessage = None


def userMessage(*args):
    global userConsoleMessage
    if not userConsoleMessage:
        userConsoleMessage = ''
    args = [str(i) for i in args]
    userConsoleMessage += u' '.join(args) + u'\n'


class CiProgram:
    """This is the main editor program. It holds top level information and runs
    the main loop. The CiProgram is intended as a singleton.
    The program interacts with a single top-level ProgramWindow."""

    def __init__(self):
        app.log.startup(u"Python version ", sys.version)
        self.prefs = app.prefs.Prefs()
        self.color = app.color.Colors(self.prefs.color)
        self.dictionary = app.spelling.Dictionary(
            self.prefs.dictionaries[u"base"],
            self.prefs.dictionaries[u"path_match"])
        self.clipboard = app.clipboard.Clipboard()
        # There is a background frame that is being build up/created. Once it's
        # completed it becomes the new front frame that will be drawn on the
        # screen. This frees up the background frame to begin drawing the next
        # frame (similar to, but not exactly like double buffering video).
        self.backgroundFrame = app.render.Frame()
        self.frontFrame = None
        self.history = app.history.History(
            self.prefs.userData.get('historyPath'))
        self.bufferManager = app.buffer_manager.BufferManager(self, self.prefs)
        self.cursesScreen = None
        self.debugMouseEvent = (0, 0, 0, 0, 0)
        self.exiting = False
        self.ch = 0
        self.bg = None

    def setUpCurses(self, cursesScreen):
        self.cursesScreen = cursesScreen
        curses.mousemask(-1)
        curses.mouseinterval(0)
        # Enable mouse tracking in xterm.
        sys.stdout.write('\033[?1002;h')
        #sys.stdout.write('\033[?1005;h')
        curses.meta(1)
        # Access ^c before shell does.
        curses.raw()
        # Enable Bracketed Paste Mode.
        sys.stdout.write('\033[?2004;h')
        # Push the escape codes out to the terminal. (Whether this is needed
        # seems to vary by platform).
        sys.stdout.flush()
        try:
            curses.start_color()
            if not curses.has_colors():
                userMessage("This terminal does not support color.")
                self.quitNow()
            else:
                curses.use_default_colors()
        except curses.error as e:
            app.log.error(e)
        app.log.startup(u"curses.COLORS", curses.COLORS)
        if 0:
            assert curses.COLORS == 256
            assert curses.can_change_color() == 1
            assert curses.has_colors() == 1
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

    def commandLoop(self):
        # Cache the thread setting.
        useBgThread = self.prefs.editor['useBgThread']
        cmdCount = 0
        # Track the time needed to handle commands and render the UI.
        # (A performance measurement).
        self.mainLoopTime = 0
        self.mainLoopTimePeak = 0
        self.cursesWindowGetCh = app.window.mainCursesWindow.getch
        if self.prefs.startup['timeStartup']:
            # When running a timing of the application startup, push a CTRL_Q
            # onto the curses event messages to simulate a full startup with a
            # GUI render.
            curses.ungetch(17)
        start = time.time()
        # The first render, to get something on the screen.
        if useBgThread:
            self.bg.put((self.programWindow, []))
        else:
            self.programWindow.shortTimeSlice()
            self.programWindow.render()
            self.backgroundFrame.setCmdCount(0)
        # This is the 'main loop'. Execution doesn't leave this loop until the
        # application is closing down.
        while not self.exiting:
            if 0:
                profile = cProfile.Profile()
                profile.enable()
                self.refresh(drawList, cursor, cmdCount)
                profile.disable()
                output = io.StringIO.StringIO()
                stats = pstats.Stats(
                    profile, stream=output).sort_stats('cumulative')
                stats.print_stats()
                app.log.info(output.getvalue())
            self.mainLoopTime = time.time() - start
            if self.mainLoopTime > self.mainLoopTimePeak:
                self.mainLoopTimePeak = self.mainLoopTime
            # Gather several commands into a batch before doing a redraw.
            # (A performance optimization).
            cmdList = []
            while not len(cmdList):
                if not useBgThread:
                    (drawList, cursor,
                     frameCmdCount) = self.backgroundFrame.grabFrame()
                    if frameCmdCount is not None:
                        self.frontFrame = (drawList, cursor, frameCmdCount)
                if self.frontFrame is not None:
                    drawList, cursor, frameCmdCount = self.frontFrame
                    self.refresh(drawList, cursor, frameCmdCount)
                    self.frontFrame = None
                for _ in range(5):
                    eventInfo = None
                    if self.exiting:
                        return
                    ch = self.getCh()
                    # assert isinstance(ch, int), type(ch)
                    if ch == curses.ascii.ESC:
                        # Some keys are sent from the terminal as a sequence of
                        # bytes beginning with an Escape character. To help
                        # reason about these events (and apply event handler
                        # callback functions) the sequence is converted into
                        # tuple.
                        keySequence = []
                        n = self.getCh()
                        while n != curses.ERR:
                            keySequence.append(n)
                            n = self.getCh()
                        #app.log.info('sequence\n', keySequence)
                        # Check for Bracketed Paste Mode begin.
                        paste_begin = app.curses_util.BRACKETED_PASTE_BEGIN
                        if tuple(keySequence[:len(paste_begin)]) == paste_begin:
                            ch = app.curses_util.BRACKETED_PASTE
                            keySequence = keySequence[len(paste_begin):]
                            paste_end = (curses.ascii.ESC,
                                        ) + app.curses_util.BRACKETED_PASTE_END
                            while tuple(
                                    keySequence[-len(paste_end):]) != paste_end:
                                #app.log.info('waiting in paste mode')
                                n = self.getCh()
                                if n != curses.ERR:
                                    keySequence.append(n)
                            keySequence = keySequence[:-(len(paste_end))]
                            eventInfo = struct.pack(
                                'B' * len(keySequence),
                                *keySequence).decode(u"utf-8")
                        else:
                            ch = tuple(keySequence)
                        if not ch:
                            # The sequence was empty, so it looks like this
                            # Escape wasn't really the start of a sequence and
                            # is instead a stand-alone Escape. Just forward the
                            # esc.
                            ch = curses.ascii.ESC
                    elif type(ch) is int and 160 <= ch < 257:
                        # Start of utf-8 character.
                        u = None
                        if (ch & 0xe0) == 0xc0:
                            # Two byte utf-8.
                            b = self.getCh()
                            u = bytes_to_unicode((ch, b))
                        elif (ch & 0xf0) == 0xe0:
                            # Three byte utf-8.
                            b = self.getCh()
                            c = self.getCh()
                            u = bytes_to_unicode((ch, b, c))
                        elif (ch & 0xf8) == 0xf0:
                            # Four byte utf-8.
                            b = self.getCh()
                            c = self.getCh()
                            d = self.getCh()
                            u = bytes_to_unicode((ch, b, c, d))
                        assert u is not None
                        eventInfo = u
                        ch = app.curses_util.UNICODE_INPUT
                    if ch != curses.ERR:
                        self.ch = ch
                        if ch == curses.KEY_MOUSE:
                            # On Ubuntu, Gnome terminal, curses.getmouse() may
                            # only be called once for each KEY_MOUSE. Subsequent
                            # calls will throw an exception. So getmouse is
                            # (only) called here and other parts of the code use
                            # the eventInfo list instead of calling getmouse.
                            self.debugMouseEvent = curses.getmouse()
                            eventInfo = (self.debugMouseEvent, time.time())
                        cmdList.append((ch, eventInfo))
            start = time.time()
            if len(cmdList):
                if useBgThread:
                    self.bg.put((self.programWindow, cmdList))
                else:
                    self.programWindow.executeCommandList(cmdList)
                    self.programWindow.shortTimeSlice()
                    self.programWindow.render()
                    cmdCount += len(cmdList)
                    self.backgroundFrame.setCmdCount(cmdCount)

    def processBackgroundMessages(self):
        while self.bg.hasMessage():
            frame = self.bg.get()
            if frame[0] == 'exception':
                for line in frame[1]:
                    userMessage(line[:-1])
                self.quitNow()
                return
            # It's unlikely that more than one frame would be present in the
            # queue. If/when it happens, only the las/most recent frame matters.
            self.frontFrame = frame

    def getCh(self):
        """Get an input character (or event) from curses."""
        if self.exiting:
            return -1
        ch = self.cursesWindowGetCh()
        # The background thread can send a notice at any getch call.
        while ch == 0:
            if self.bg is not None:
                # Hmm, will ch ever equal 0 when self.bg is None?
                self.processBackgroundMessages()
            if self.exiting:
                return -1
            ch = self.cursesWindowGetCh()
        return ch

    def startup(self):
        """A second init-like function. Called after command line arguments are
        parsed."""
        if app.config.strict_debug:
            assert issubclass(self.__class__, app.ci_program.CiProgram), self
        self.programWindow = app.program_window.ProgramWindow(self)
        top, left = app.window.mainCursesWindow.getyx()
        rows, cols = app.window.mainCursesWindow.getmaxyx()
        self.programWindow.reshape(top, left, rows, cols)
        self.programWindow.inputWindow.startup()
        self.programWindow.focus()

    def parseArgs(self):
        """Interpret the command line arguments."""
        app.log.startup('isatty', sys.stdin.isatty())
        debugRedo = False
        showLogWindow = False
        cliFiles = []
        openToLine = None
        profile = False
        readStdin = not sys.stdin.isatty()
        takeAll = False  # Take all args as file paths.
        timeStartup = False
        numColors = min(curses.COLORS, 256)
        if os.getenv(u"CI_EDIT_SINGLE_THREAD"):
            self.prefs.editor['useBgThread'] = False
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
                    self.prefs.editor['useBgThread'] = False
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
                    self.history.clearUserHistory()
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
        # If there's no line specified, try to reinterpret the paths.
        if openToLine is None:
            decodedPaths = []
            for file in cliFiles:
                path, openToRow, openToColumn = app.buffer_file.pathRowColumn(
                    file[u"path"], self.prefs.editor[u"baseDirEnv"])
                decodedPaths.append({'path': path, 'row': openToRow, 'col': openToColumn})
            cliFiles = decodedPaths
        self.prefs.startup = {
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

    def refresh(self, drawList, cursor, cmdCount):
        """Paint the drawList to the screen in the main thread."""
        cursesWindow = app.window.mainCursesWindow
        # Ask curses to hold the back buffer until curses refresh().
        cursesWindow.noutrefresh()
        curses.curs_set(0)  # Hide cursor.
        for i in drawList:
            try:
                cursesWindow.addstr(*i)
            except curses.error:
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
            except curses.error:
                pass
        # This is a workaround to allow background processing (and parser screen
        # redraw) to interact well with the test harness. The intent is to tell
        # the test that the screen includes all commands executed up to N.
        if hasattr(cursesWindow, 'test_rendered_command_count'):
            cursesWindow.test_rendered_command_count(cmdCount)

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
        homePath = self.prefs.userData.get('homePath')
        self.makeHomeDirs(homePath)
        self.history.loadUserHistory()
        app.curses_util.hackCursesFixes()
        if self.prefs.editor['useBgThread']:
            self.bg = app.background.startupBackground()
        self.startup()
        if self.prefs.startup.get('profile'):
            profile = cProfile.Profile()
            profile.enable()
            self.commandLoop()
            profile.disable()
            output = io.StringIO.StringIO()
            stats = pstats.Stats(
                profile, stream=output).sort_stats('cumulative')
            stats.print_stats()
            app.log.info(output.getvalue())
        else:
            self.commandLoop()
        if self.prefs.editor['useBgThread']:
            self.bg.put((self.programWindow, 'quit'))
            self.bg.join()

    def setUpPalette(self):

        def applyPalette(name):
            palette = self.prefs.palette[name]
            foreground = palette['foregroundIndexes']
            background = palette['backgroundIndexes']
            for i in range(1, self.prefs.startup['numColors']):
                curses.init_pair(i, foreground[i], background[i])

        def twoTries(primary, fallback):
            try:
                applyPalette(primary)
                app.log.startup(u"Primary color scheme applied")
            except curses.error:
                try:
                    applyPalette(fallback)
                    app.log.startup(u"Fallback color scheme applied")
                except curses.error:
                    app.log.startup(u"No color scheme applied")

        self.color.colors = self.prefs.startup['numColors']
        if self.prefs.startup['numColors'] == 0:
            app.log.startup('using no colors')
        elif self.prefs.startup['numColors'] == 8:
            self.prefs.color = self.prefs.color8
            app.log.startup('using 8 colors')
            twoTries(self.prefs.editor['palette8'], 'default8')
        elif self.prefs.startup['numColors'] == 16:
            self.prefs.color = self.prefs.color16
            app.log.startup('using 16 colors')
            twoTries(self.prefs.editor['palette16'], 'default16')
        elif self.prefs.startup['numColors'] == 256:
            self.prefs.color = self.prefs.color256
            app.log.startup('using 256 colors')
            twoTries(self.prefs.editor['palette'], 'default')
        else:
            raise Exception('unknown palette color count ' +
                            repr(self.prefs.startup['numColors']))

    if 1:  # For unit tests/debugging.

        def getDocumentSelection(self):
            """This is primarily for testing."""
            tb = self.programWindow.inputWindow.textBuffer
            return (tb.penRow, tb.penCol, tb.markerRow, tb.markerCol,
                    tb.selectionMode)

        def getSelection(self):
            """This is primarily for testing."""
            tb = self.programWindow.focusedWindow.textBuffer
            return (tb.penRow, tb.penCol, tb.markerRow, tb.markerCol,
                    tb.selectionMode)


def wrapped_ci(cursesScreen):
    try:
        prg = CiProgram()
        prg.setUpCurses(cursesScreen)
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
        sys.stdout.write('\033[?2004l')
        sys.stdout.flush()
    if userConsoleMessage:
        fullPath = app.buffer_file.expandFullPath(
            '~/.ci_edit/userConsoleMessage')
        with io.open(fullPath, 'w+') as f:
            f.write(userConsoleMessage)
        sys.stdout.write(userConsoleMessage + '\n')
        sys.stdout.flush()


if __name__ == '__main__':
    run_ci()
