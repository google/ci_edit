# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.controller
import app.cu_editor
import app.editor
import app.text_buffer
import sys
import curses


class StaticWindow:
  """A static window does not get focus.
  parent is responsible for the order in which this window is updated, relative
  to its siblings."""
  def __init__(self, parent):
    self.parent = parent
    self.zOrder = []
    self.color = 0
    self.colorSelected = 1
    self.top = 0
    self.left = 0
    self.rows = 1
    self.cols = 1
    self.writeLineRow = 0
    self.cursorWindow = curses.newwin(1, 1)
    self.cursorWindow.leaveok(1)  # Don't update cursor position.

  def addStr(self, row, col, text, colorPair):
    """Overwrite text a row, column with text."""
    try: self.cursorWindow.addstr(row, col, text, colorPair)
    except curses.error: pass

  def blank(self):
    """Clear the window."""
    for i in range(self.rows):
      self.addStr(0, i, ' '*self.cols, self.color)
    self.cursorWindow.refresh()

  def contains(self, row, col):
    """Determine whether the position at row, col lay within this window."""
    for i in self.zOrder:
      if i.contains(row, col):
        return i
    return (self.top <= row < self.top+self.rows and
        self.left <= col < self.left + self.cols and self)

  def debugDraw(self, win):
    self.parent.debugDraw(win)

  def hide(self):
    """Remove window from the render list."""
    try: self.parent.zOrder.remove(self)
    except ValueError: app.log.detail(repr(self)+'not found in zOrder')

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

  def moveTo(self, top, left):
    app.log.detail('move', top, left)
    if top == self.top and left == self.left:
      return
    self.top = top
    self.left = left
    try:
      self.cursorWindow.mvwin(self.top, self.left)
    except:
      app.log.info('error mvwin', top, left, repr(self))
      app.log.detail('error mvwin', top, left, repr(self))

  def moveBy(self, top, left):
    app.log.detail('moveBy', top, left, repr(self))
    if top == 0 and left == 0:
      return
    self.top += top
    self.left += left
    self.cursorWindow.mvwin(self.top, self.left)

  def refresh(self):
    """Redraw window."""
    self.cursorWindow.refresh()
    for child in reversed(self.zOrder):
      child.refresh()

  def reshape(self, rows, cols, top, left):
    self.moveTo(top, left)
    self.resizeTo(rows, cols)

  def resizeTo(self, rows, cols):
    app.log.detail('resizeTo', rows, cols)
    self.rows = rows
    self.cols = cols
    try:
      self.cursorWindow.resize(self.rows, self.cols)
    except:
      app.log.detail('resize failed', self.rows, self.cols)

  def resizeBy(self, rows, cols):
    app.log.detail('resizeBy', rows, cols, repr(self))
    self.rows += rows
    self.cols += cols
    if self.rows <= 0 or self.cols <= 0:
      return
    self.cursorWindow.resize(self.rows, self.cols)

  def setParent(self, parent, layerIndex):
    if self.parent:
      try: self.parent.zOrder.remove(self)
      except: pass
    self.parent = parent
    if parent:
      self.parent.zOrder.insert(layerIndex, self)

  def show(self):
    """Show window and bring it to the top layer."""
    try: self.parent.zOrder.remove(self)
    except: pass
    self.parent.zOrder.append(self)

  def writeLine(self, text, colorPair=1):
    """Simple line writer for static windows."""
    text = str(text)[:self.cols]
    text = text + ' '*max(0, self.cols-len(text))
    try: self.cursorWindow.addstr(self.writeLineRow, 0, text,
        curses.color_pair(colorPair))
    except curses.error: pass
    self.writeLineRow += 1


class Window(StaticWindow):
  """A Window may have focus. A Window holds a TextBuffer and a
    controller that operates on the TextBuffer."""
  def __init__(self, parent, controller=None):
    StaticWindow.__init__(self, parent)
    self.controller = controller
    self.cursorWindow.keypad(1)
    self.hasFocus = False
    self.textBuffer = None

  def focus(self):
    app.log.info('focus', self)
    self.hasFocus = True
    try: self.parent.zOrder.remove(self)
    except ValueError: app.log.detail(repr(self)+'not found in zOrder')
    self.parent.zOrder.append(self)
    self.cursorWindow.leaveok(0)  # Do update cursor position.
    self.controller.focus()

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
    StaticWindow.refresh(self)
    self.textBuffer.draw(self)
    if self.hasFocus:
      self.parent.debugDraw(self)
      try:
        self.cursorWindow.move(
            self.textBuffer.cursorRow - self.textBuffer.scrollRow,
            self.textBuffer.cursorCol - self.textBuffer.scrollCol)
      except curses.error:
        pass

  def setTextBuffer(self, textBuffer):
    textBuffer.setView(self)
    self.textBuffer = textBuffer

  def unfocus(self):
    app.log.info('unfocus', self)
    self.hasFocus = False
    self.cursorWindow.leaveok(1)  # Don't update cursor position.
    self.controller.unfocus()
    #assert(self.prg.exiting or self.prg.changeTo)


class HeaderLine(StaticWindow):
  def __init__(self, parent, host):
    StaticWindow.__init__(self, parent)
    self.host = host
    self.textLine = None

  def refresh(self):
    textLine = self.host.textBuffer.fullPath
    if self.textLine == textLine:
      return
    self.textLine = textLine
    self.blank()
    self.addStr(0, 0, textLine, self.color)
    self.cursorWindow.refresh()


class FileListPanel(Window):
  def __init__(self, parent):
    Window.__init__(self, parent)
    self.color = curses.color_pair(18)
    self.colorSelected = curses.color_pair(3)


class LabeledLine(Window):
  def __init__(self, parent, label):
    Window.__init__(self, parent)
    self.label = label
    self.leftColumn = StaticWindow(parent)

  def refresh(self):
    self.leftColumn.addStr(0, 0, self.label, self.color)
    self.leftColumn.cursorWindow.refresh()
    Window.refresh(self)

  def reshape(self, rows, cols, top, left):
    labelWidth = len(self.label)
    Window.reshape(self, rows, cols-labelWidth, top, left+labelWidth)
    self.leftColumn.reshape(rows, labelWidth, top, left)

  def unfocus(self):
    self.blank()
    self.hide()
    self.leftColumn.blank()
    self.leftColumn.hide()
    Window.unfocus(self)


class InteractiveFind(LabeledLine):
  def __init__(self, host):
    LabeledLine.__init__(self, host, "find: ")
    self.host = host
    self.setTextBuffer(app.text_buffer.TextBuffer())
    self.controller = app.cu_editor.InteractiveFind(host,
        self.textBuffer)


class InteractiveGoto(LabeledLine):
  def __init__(self, parent, host):
    LabeledLine.__init__(self, parent, "goto: ")
    self.host = host
    self.setTextBuffer(app.text_buffer.TextBuffer())
    self.controller = app.cu_editor.InteractiveGoto(host,
        self.textBuffer)
    self.leftColumn = StaticWindow(parent)


class InteractiveOpener(LabeledLine):
  def __init__(self, prg, host):
    """|host| is used as parent and host."""
    LabeledLine.__init__(self, host, "file: ")
    self.host = host
    self.setTextBuffer(app.text_buffer.TextBuffer())
    self.fileListing = app.text_buffer.TextBuffer()
    #self.fileListing.fullPath = self.host.textBuffer.fullPath
    #self.host.setTextBuffer(self.fileListing)
    self.controller = app.cu_editor.InteractiveOpener(prg, host,
        self.textBuffer)


class InteractiveQuit(LabeledLine):
  def __init__(self, parent, host):
    LabeledLine.__init__(self, parent,
        "Save changes? (yes, no, or cancel): ")
    self.host = host
    self.setTextBuffer(app.text_buffer.TextBuffer())
    self.controller = app.cu_editor.InteractiveQuit(host,
        self.textBuffer)


class InteractiveSaveAs(LabeledLine):
  def __init__(self, prg, host):
    LabeledLine.__init__(self, host, "save as: ")
    #self.controller = app.cu_editor.InteractiveSaveAs(prg, host,
    #    self.textBuffer)


class LineNumbers(StaticWindow):
  def __init__(self, parent, host):
    StaticWindow.__init__(self, parent)
    self.host = host

  def drawLineNumbers(self):
    maxy, maxx = self.cursorWindow.getmaxyx()
    textBuffer = self.host.textBuffer
    limit = min(maxy, len(textBuffer.lines)-textBuffer.scrollRow)
    for i in range(limit):
      self.addStr(i, 0,
          ' %5d  '%(textBuffer.scrollRow+i+1), self.color)
    for i in range(limit, maxy):
      self.addStr(i, 0, '       ', 0)
    if 1:
      cursorAt = textBuffer.cursorRow-textBuffer.scrollRow
      self.addStr(cursorAt, 1,
          '%5d'%(textBuffer.cursorRow+1), self.colorSelected)
    self.cursorWindow.refresh()

  def refresh(self):
    self.drawLineNumbers()


class LogWindow(StaticWindow):
  def __init__(self, parent):
    StaticWindow.__init__(self, parent)
    self.lines = app.log.getLines()
    self.refreshCounter = 0

  def refresh(self):
    self.refreshCounter += 1
    app.log.info(" "*40, self.refreshCounter, "- screen refresh -")
    maxy, maxx = self.cursorWindow.getmaxyx()
    self.writeLineRow = 0
    for i in self.lines[-maxy:]:
      self.writeLine(i);
    StaticWindow.refresh(self)


class MessageLine(StaticWindow):
  """The message line appears at the bottom of the screen. It shows
       messages to the user, such as error messages."""
  def __init__(self, parent, host):
    StaticWindow.__init__(self, parent)
    self.host = host
    self.renderedMessage = None

  def refresh(self):
    tb = self.host.textBuffer
    #maxy, maxx = self.cursorWindow.getmaxyx()
    if not tb or self.renderedMessage is tb.message:
      #self.writeLine('<no text buffer>', 0)
      return
    app.log.debug('update message line\n',self.renderedMessage, '\n',
      tb.message)
    self.renderedMessage = tb.message
    self.writeLineRow = 0
    if tb.message:
      self.writeLine(tb.message[0], tb.message[1])
    else:
      self.blank()
    self.cursorWindow.refresh()


class StatusLine(StaticWindow):
  """The status line appears at the bottom of the screen. It shows the current
  line and column the cursor is on."""
  def __init__(self, parent, host):
    StaticWindow.__init__(self, parent)
    self.host = host

  def refresh(self):
    maxy, maxx = self.cursorWindow.getmaxyx()
    if False and self.parent.zOrder[-1] is self:
      Window.refresh(self)
    else:
      tb = self.host.textBuffer
      statusLine = self.host.textBuffer.relativePath
      if tb.isDirty():
        statusLine += ' * '
      else:
        statusLine += ' . '
      # Percentages.
      rowPercentage = 0
      colPercentage = 0
      lineCount = len(tb.lines)
      if lineCount:
        rowPercentage = tb.cursorRow*100/lineCount
        if tb.cursorRow >= lineCount - 1:
           rowPercentage = 100
        charCount = len(tb.lines[tb.cursorRow])
        if (tb.cursorCol < charCount):
          colPercentage = tb.cursorCol*100/charCount
        else:
          colPercentage = 100
      # Format.
      rightSide = '%s | %s | %4d,%2d | %3d%%,%3d%%'%(
          tb.cursorGrammarName(),
          tb.selectionModeName(),
          tb.cursorRow+1, tb.cursorCol+1,
          rowPercentage,
          colPercentage)
      statusLine += ' '*(maxx-len(statusLine)-len(rightSide)) + rightSide
      self.addStr(0, 0, statusLine, self.color)
      self.cursorWindow.refresh()


class InputWindow(Window):
  """This is the main content window. Often the largest pane displayed."""
  def __init__(self, prg, rows, cols, top, left, header, footer, lineNumbers):
    assert(prg)
    Window.__init__(self, prg)
    self.prg = prg
    self.showHeader = header
    self.showFooter = footer
    self.showLineNumbers = lineNumbers
    self.color = curses.color_pair(0)
    self.colorSelected = curses.color_pair(app.prefs.selectedColor)
    self.controller = app.controller.MainController(self)
    self.controller.add(app.cu_editor.CuaPlusEdit(prg, self))
    if 1:
      self.interactiveOpen = InteractiveOpener(prg, self)
      self.interactiveOpen.color = curses.color_pair(0)
      self.interactiveOpen.colorSelected = curses.color_pair(87)
      self.interactiveOpen.setParent(self, 0)
      self.interactiveOpen.hide()
    if 1:
      self.interactiveSaveAs = InteractiveSaveAs(prg, self)
      self.interactiveSaveAs.color = curses.color_pair(0)
      self.interactiveSaveAs.colorSelected = curses.color_pair(87)
      self.interactiveSaveAs.setParent(self, 0)
      self.interactiveSaveAs.hide()
    if 1:
      self.interactiveQuit = InteractiveQuit(prg, self)
      self.interactiveQuit.color = curses.color_pair(0)
      self.interactiveQuit.colorSelected = curses.color_pair(87)
      self.interactiveQuit.setParent(self, 0)
      self.interactiveQuit.hide()
    if 1:
      self.interactiveFind = InteractiveFind(self)
      self.interactiveFind.color = curses.color_pair(0)
      self.interactiveFind.colorSelected = curses.color_pair(87)
      self.interactiveFind.setParent(self, 0)
      self.interactiveFind.hide()
    if 1:
      self.interactiveGoto = InteractiveGoto(prg, self)
      self.interactiveGoto.color = curses.color_pair(0)
      self.interactiveGoto.colorSelected = curses.color_pair(87)
      self.interactiveGoto.setParent(self, 0)
      self.interactiveGoto.hide()
    if header:
      self.headerLine = HeaderLine(self, self)
      self.headerLine.color = curses.color_pair(168)
      self.headerLine.colorSelected = curses.color_pair(47)
      self.headerLine.setParent(self, 0)
    if footer:
      self.statusLine = StatusLine(self, self)
      self.statusLine.color = curses.color_pair(168)
      self.statusLine.colorSelected = curses.color_pair(47)
      self.statusLine.setParent(self, 0)
    if lineNumbers:
      self.leftColumn = LineNumbers(self, self)
      self.leftColumn.color = curses.color_pair(211)
      self.leftColumn.colorSelected = curses.color_pair(146)
      self.leftColumn.setParent(self, 0)
    if 1:
      self.rightColumn = StaticWindow(self)
      self.rightColumn.color = curses.color_pair(18)
      self.rightColumn.colorSelected = curses.color_pair(105)
      self.rightColumn.setParent(self, 0)
    if True:
      self.messageLine = MessageLine(self, self)
      self.messageLine.color = curses.color_pair(3)
      self.messageLine.colorSelected = curses.color_pair(87)
      self.messageLine.setParent(self, 0)

    if header:
      if self.prg.cliFiles:
        path = self.prg.cliFiles[0]['path']
        #self.headerLine.setFileName(path)
        self.setTextBuffer(
            self.prg.bufferManager.loadTextBuffer(path))
      elif self.prg.readStdin:
        #self.headerLine.setFileName("stdin")
        self.setTextBuffer(self.prg.bufferManager.readStdin())
      else:
        scratchPath = "~/ci_scratch"
        #self.headerLine.setFileName(scratchPath)
        self.setTextBuffer(self.prg.bufferManager.loadTextBuffer(scratchPath))
    self.reshape(rows, cols, top, left)

  def reshape(self, rows, cols, top, left):
    app.log.detail('reshape', rows, cols, top, left)
    if self.showHeader:
      self.headerLine.reshape(1, cols, top, left)
      rows -= 1
      top += 1
    self.interactiveOpen.reshape(1, cols, top+rows-1, left)
    self.interactiveQuit.reshape(1, cols, top+rows-1, left)
    self.interactiveSaveAs.reshape(1, cols, top+rows-1, left)
    self.messageLine.reshape(1, cols, top+rows-1, left)
    if 1:
      findReplaceHeight = 1
      topOfFind = top+rows-findReplaceHeight
      self.interactiveFind.reshape(findReplaceHeight, cols,
          topOfFind, left)
    if 1:
      topOfGoto = top+rows-findReplaceHeight
      self.interactiveGoto.reshape(1, cols, topOfGoto, left)
    if self.showFooter:
      self.statusLine.reshape(1, cols, top+rows-2, left)
      rows -= 2
    if self.showLineNumbers:
      self.leftColumn.reshape(rows, 7, top, left)
      cols -= 7
      left += 7
    if 1:
      self.rightColumn.reshape(rows, 1, top, left+cols-1)
      cols -= 1
    Window.reshape(self, rows, cols, top, left)

  def changeFocusTo(self, changeTo):
    self.prg.changeTo = changeTo

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

  def focus(self):
    self.messageLine.show()
    Window.focus(self)

  def quitNow(self):
    self.prg.quitNow()

  def refresh(self):
    Window.refresh(self)
    self.drawRightEdge()
    self.cursorWindow.refresh()

  def setTextBuffer(self, textBuffer):
    app.log.info('setTextBuffer')
    #self.headerLine.controller.setFileName(textBuffer.fullPath)
    textBuffer.lineLimitIndicator = 80
    self.controller.setTextBuffer(textBuffer)
    Window.setTextBuffer(self, textBuffer)
    self.textBuffer.debugRedo = self.prg.debugRedo

  def unfocus(self):
    self.statusLine.cursorWindow.addstr(0, 0, ".")
    self.statusLine.refresh()
    app.log.debug('message line unfocus')
    self.messageLine.blank()
    self.messageLine.hide()
    Window.unfocus(self)


class PaletteWindow(Window):
  """A window with example foreground and background text colors."""
  def __init__(self, prg):
    Window.__init__(self, prg)
    self.resizeTo(16, 16*5)
    self.moveTo(8, 8)
    self.controller = app.controller.MainController(self)
    self.controller.add(app.cu_editor.PaletteDialogController(
        prg, self))
    textBuffer = app.text_buffer.TextBuffer()
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

