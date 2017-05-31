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

import app.buffer_manager
import app.controller
import app.cu_editor
import app.editor
import app.history
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
    self.isFocusable = False
    self.top = 0
    self.left = 0
    self.rows = 1
    self.cols = 1
    self.scrollRow = 0
    self.scrollCol = 0
    self.writeLineRow = 0
    self.cursorWindow = curses.newwin(1, 1)
    self.cursorWindow.leaveok(1)  # Don't update cursor position.
    self.cursorWindow.timeout(10)

  def addStr(self, row, col, text, colorPair):
    """Overwrite text a row, column with text."""
    try: self.cursorWindow.addstr(row, col, text, colorPair)
    except curses.error: pass

  def changeFocusTo(self, changeTo):
    self.parent.changeFocusTo(changeTo)

  def normalize(self):
    self.parent.normalize()

  def paint(self, row, col, count, colorPair):
    """Paint text a row, column with colorPair.
      fyi, I thought this may be faster than using addStr to paint over the text
      with a different colorPair. It looks like there isn't a significant
      performance difference between chgat and addstr."""
    self.cursorWindow.chgat(row, col, count, colorPair)

  def presentModal(self, changeTo, paneRow, paneCol):
    self.parent.presentModal(changeTo, paneRow, paneCol)

  def blank(self):
    """Clear the window."""
    for i in range(self.rows):
      self.addStr(i, 0, ' '*self.cols, self.color)
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

  def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
    pass

  def mouseDoubleClick(self, paneRow, paneCol, shift, ctrl, alt):
    pass

  def mouseMoved(self, paneRow, paneCol, shift, ctrl, alt):
    pass

  def mouseRelease(self, paneRow, paneCol, shift, ctrl, alt):
    pass

  def mouseTripleClick(self, paneRow, paneCol, shift, ctrl, alt):
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
    for child in self.zOrder:
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

  def resizeBottomBy(self, rows):
    app.log.detail('resizeTopBy', rows, repr(self))
    self.rows += rows
    if self.rows <= 0:
      return
    self.cursorWindow.resize(self.rows, self.cols)

  def resizeBy(self, rows, cols):
    app.log.detail('resizeBy', rows, cols, repr(self))
    self.rows += rows
    self.cols += cols
    if self.rows <= 0 or self.cols <= 0:
      return
    self.cursorWindow.resize(self.rows, self.cols)

  def resizeTopBy(self, rows):
    self.top += rows
    self.rows -= rows
    if self.rows <= 0:
      return
    try:
      self.cursorWindow.resize(self.rows, self.cols)
      self.cursorWindow.mvwin(self.top, self.left)
    except:
      app.log.error('window resize failed')

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


class ActiveWindow(StaticWindow):
  """An ActiveWindow may have focus and a controller."""
  def __init__(self, parent, controller=None):
    StaticWindow.__init__(self, parent)
    self.controller = controller
    self.cursorWindow.keypad(1)
    self.isFocusable = True
    self.shouldShowCursor = False

  def focus(self):
    app.log.info(self)
    self.hasFocus = True
    try: self.parent.zOrder.remove(self)
    except ValueError: app.log.detail(repr(self)+'not found in zOrder')
    self.parent.zOrder.append(self)
    self.controller.focus()

  def unfocus(self):
    app.log.info(self)
    self.hasFocus = False
    self.controller.unfocus()


class Window(ActiveWindow):
  """A Window holds a TextBuffer and a controller that operates on the
  TextBuffer."""
  def __init__(self, parent, controller=None):
    ActiveWindow.__init__(self, parent)
    self.cursorRow = 0
    self.cursorCol = 0
    self.goalCol = 0
    self.hasCaptiveCursor = app.prefs.prefs['editor']['captiveCursor']
    self.hasFocus = False
    self.shouldShowCursor = True
    self.textBuffer = None

  def focus(self):
    self.cursorWindow.leaveok(0)  # Do update cursor position.
    ActiveWindow.focus(self)

  def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
    self.textBuffer.mouseClick(paneRow, paneCol, shift, ctrl, alt)

  def mouseDoubleClick(self, paneRow, paneCol, shift, ctrl, alt):
    self.textBuffer.mouseDoubleClick(paneRow, paneCol, shift, ctrl, alt)

  def mouseMoved(self, paneRow, paneCol, shift, ctrl, alt):
    self.textBuffer.mouseMoved(paneRow, paneCol, shift, ctrl, alt)

  def mouseRelease(self, paneRow, paneCol, shift, ctrl, alt):
    self.textBuffer.mouseRelease(paneRow, paneCol, shift, ctrl, alt)

  def mouseTripleClick(self, paneRow, paneCol, shift, ctrl, alt):
    self.textBuffer.mouseTripleClick(paneRow, paneCol, shift, ctrl, alt)

  def mouseWheelDown(self, shift, ctrl, alt):
    self.textBuffer.mouseWheelDown(shift, ctrl, alt)

  def mouseWheelUp(self, shift, ctrl, alt):
    self.textBuffer.mouseWheelUp(shift, ctrl, alt)

  def refresh(self):
    self.cursorRow = self.textBuffer.penRow
    self.cursorCol = self.textBuffer.penCol
    self.textBuffer.cursorRow = self.textBuffer.penRow
    self.textBuffer.cursorCol = self.textBuffer.penCol
    self.textBuffer.draw(self)
    StaticWindow.refresh(self)
    if self.hasFocus:
      self.parent.debugDraw(self)
      self.shouldShowCursor = (self.cursorRow >= self.scrollRow and
          self.cursorRow < self.scrollRow+self.rows)
      if self.shouldShowCursor:
        try:
          self.cursorWindow.move(
              self.cursorRow - self.scrollRow,
              self.cursorCol - self.scrollCol)
        except curses.error:
          pass

  def setTextBuffer(self, textBuffer):
    textBuffer.setView(self)
    self.textBuffer = textBuffer

  def unfocus(self):
    self.cursorWindow.leaveok(1)  # Don't update cursor position.
    ActiveWindow.unfocus(self)


class LabeledLine(Window):
  """A single line with a label. This is akin to a line prompt or gui modal
      dialog. It's used for things like 'find' and 'goto line'."""
  def __init__(self, parent, label, controller=None):
    Window.__init__(self, parent, controller)
    self.host = parent
    self.setTextBuffer(app.text_buffer.TextBuffer())
    self.label = label
    self.leftColumn = StaticWindow(self)
    self.color = curses.color_pair(0)
    self.colorSelected = curses.color_pair(87)

  def refresh(self):
    self.leftColumn.addStr(0, 0, self.label, self.color)
    self.leftColumn.cursorWindow.refresh()
    Window.refresh(self)

  def reshape(self, rows, cols, top, left):
    labelWidth = len(self.label)
    Window.reshape(self, rows, cols-labelWidth, top, left+labelWidth)
    self.leftColumn.reshape(rows, labelWidth, top, left)

  def setController(self, controllerClass):
    self.controller = controllerClass(self.host, self.textBuffer)

  def setLabel(self, label):
    self.label = label
    self.reshape(self.rows, self.cols, self.top, self.left)

  def unfocus(self):
    self.blank()
    self.hide()
    self.leftColumn.blank()
    self.leftColumn.hide()
    Window.unfocus(self)


class Menu(StaticWindow):
  """"""
  def __init__(self, prg, host):
    StaticWindow.__init__(self, prg)
    self.host = host
    self.controller = None
    self.lines = []
    self.commands = []
    self.shouldShowCursor = False

  def addItem(self, label, command):
    self.lines.append(label)
    self.commands.append(command)

  def clear(self):
    self.lines = []
    self.commands = []

  def moveSizeToFit(self, left, top):
    self.clear()
    self.addItem('some menu', None)
    #self.addItem('sort', self.host.textBuffer.sortSelection)
    self.addItem('cut', self.host.textBuffer.editCut)
    self.addItem('paste', self.host.textBuffer.editPaste)
    longest = 0
    for i in self.lines:
      if len(i) > longest:
        longest = len(i)
    self.reshape(len(self.lines), longest+2, left, top)

  def refresh(self):
    maxRow, maxCol = self.cursorWindow.getmaxyx()
    self.writeLineRow = 0
    for i in self.lines[:maxRow]:
      self.writeLine(" "+i, 192);
    StaticWindow.refresh(self)

  def setController(self, controllerClass):
    self.controller = controllerClass(self.host, self.textBuffer)


class LineNumbers(StaticWindow):
  def __init__(self, host):
    StaticWindow.__init__(self, host)
    self.host = host

  def drawLineNumbers(self):
    maxRow, maxCol = self.cursorWindow.getmaxyx()
    textBuffer = self.host.textBuffer
    limit = min(maxRow, len(textBuffer.lines)-self.host.scrollRow)
    for i in range(limit):
      self.addStr(i, 0,
          ' %5d  '%(self.host.scrollRow+i+1), self.color)
    color = curses.color_pair(app.prefs.outsideOfBufferColorIndex)
    for i in range(limit, maxRow):
      self.addStr(i, 0, '       ', color)
    if 1:
      cursorAt = self.host.cursorRow-self.host.scrollRow
      self.addStr(cursorAt, 1,
          '%5d'%(self.host.cursorRow+1), self.colorSelected)
    self.cursorWindow.refresh()

  def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
    app.log.info(paneRow, paneCol, shift)
    if ctrl:
      app.log.info('click at', paneRow, paneCol)
      return
    self.host.changeFocusTo(self.host)
    tb = self.host.textBuffer
    if shift:
      if tb.selectionMode == app.selectable.kSelectionNone:
        tb.selectionLine()
      self.mouseRelease(paneRow, paneCol, shift, ctrl, alt)
    else:
      tb.selectionNone()
      self.mouseRelease(paneRow, paneCol, shift, ctrl, alt)

  def mouseDoubleClick(self, paneRow, paneCol, shift, ctrl, alt):
    self.host.textBuffer.selectionAll()

  def mouseMoved(self, paneRow, paneCol, shift, ctrl, alt):
    app.log.info(paneRow, paneCol, shift)
    self.host.textBuffer.mouseClick(paneRow, paneCol, True, ctrl, alt)

  def mouseRelease(self, paneRow, paneCol, shift, ctrl, alt):
    app.log.info(paneRow, paneCol, shift)
    tb = self.host.textBuffer
    tb.selectLineAt(self.host.scrollRow + paneRow)

  def mouseTripleClick(self, paneRow, paneCol, shift, ctrl, alt):
    pass

  def mouseWheelDown(self, shift, ctrl, alt):
    self.host.mouseWheelDown(shift, ctrl, alt)

  def mouseWheelUp(self, shift, ctrl, alt):
    self.host.mouseWheelUp(shift, ctrl, alt)

  def refresh(self):
    self.drawLineNumbers()


class LogWindow(StaticWindow):
  def __init__(self, parent):
    StaticWindow.__init__(self, parent)
    self.lines = app.log.getLines()
    self.refreshCounter = 0

  def refresh(self):
    self.refreshCounter += 1
    app.log.info(" "*10, self.refreshCounter, "- screen refresh -")
    maxRow, maxCol = self.cursorWindow.getmaxyx()
    self.writeLineRow = 0
    for i in self.lines[-maxRow:]:
      color = 0
      if len(i) and i[-1] == '-':
        color = 96
      self.writeLine(i, color);
    StaticWindow.refresh(self)


class MessageLine(StaticWindow):
  """The message line appears at the bottom of the screen. It shows
       messages to the user, such as error messages."""
  def __init__(self, host):
    StaticWindow.__init__(self, host)
    self.host = host
    self.renderedMessage = None

  def refresh(self):
    self.blank()
    return
    # TODO(dschuyler): clean this up
    tb = self.host.textBuffer
    if not tb or self.renderedMessage is tb.message:
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
  def __init__(self, host):
    StaticWindow.__init__(self, host)
    self.host = host

  def refresh(self):
    maxRow, maxCol = self.cursorWindow.getmaxyx()
    tb = self.host.textBuffer
    statusLine = ''
    if tb.message:
      statusLine = tb.message[0]
      tb.setMessage()
    if 0:
      if tb.isDirty():
        statusLine += ' * '
      else:
        statusLine += ' . '
    # Percentages.
    rowPercentage = 0
    colPercentage = 0
    lineCount = len(tb.lines)
    if lineCount:
      rowPercentage = self.host.cursorRow*100/lineCount
      if self.host.cursorRow >= lineCount - 1:
         rowPercentage = 100
      charCount = len(tb.lines[self.host.cursorRow])
      if (self.host.cursorCol < charCount):
        colPercentage = self.host.cursorCol*100/charCount
      else:
        colPercentage = 100
    # Format.
    rightSide = ''
    if len(statusLine):
      rightSide += ' |'
    if 0:
      rightSide += ' %s | %s |'%(
          tb.cursorGrammarName(),
          tb.selectionModeName())
    rightSide += ' %4d,%2d | %3d%%,%3d%%'%(
        self.host.cursorRow+1, self.host.cursorCol+1,
        rowPercentage,
        colPercentage)
    statusLine += ' '*(maxCol-len(statusLine)-len(rightSide)) + rightSide
    self.addStr(0, 0, statusLine, self.color)
    self.cursorWindow.refresh()


class TopInfo(StaticWindow):
  def __init__(self, host):
    StaticWindow.__init__(self, host)
    self.host = host
    self.borrowedRows = 0
    self.lines = []
    self.mode = 2

  def onChange(self):
    if self.mode == 0:
      return
    tb = self.host.textBuffer
    lines = []
    if len(tb.lines):
      lineCursor = self.host.scrollRow
      line = ""
      while len(line) == 0 and lineCursor > 0:
        line = tb.lines[lineCursor]
        lineCursor -= 1
      if len(line):
        indent = len(line) - len(line.lstrip(' '))
        lineCursor += 1
        while lineCursor < len(tb.lines):
          line = tb.lines[lineCursor]
          if not len(line):
            continue
          z = len(line) - len(line.lstrip(' '))
          if z > indent:
            indent = z
            lineCursor += 1
          else:
            break
        while indent and lineCursor > 0:
          line = tb.lines[lineCursor]
          if len(line):
            z = len(line) - len(line.lstrip(' '))
            if z < indent:
              indent = z
              lines.append(line)
          lineCursor -= 1
    pathLine = self.host.textBuffer.fullPath
    if 1:
      if tb.isDirty():
        pathLine += ' * '
      else:
        pathLine += ' . '
    lines.append(pathLine[-self.cols:])
    self.lines = lines
    infoRows = len(self.lines)
    if self.mode > 0:
      infoRows = self.mode
    if self.borrowedRows != infoRows:
      self.host.resizeTopBy(infoRows-self.borrowedRows)
      self.resizeTo(infoRows, self.cols)
      self.borrowedRows = infoRows

  def refresh(self):
    """Render the context information at the top of the window."""
    lines = self.lines
    lines.reverse()
    for i,line in enumerate(lines):
      self.addStr(i, 0, line+' '*(self.cols-len(line)), self.color)
    for i in range(len(lines), self.rows):
      self.addStr(i, 0, ' '*self.cols, self.color)
    self.cursorWindow.refresh()

  def reshape(self, rows, cols, top, left):
    self.borrowedRows = 0
    StaticWindow.reshape(self, rows, cols, top, left)


class InputWindow(Window):
  """This is the main content window. Often the largest pane displayed."""
  def __init__(self, prg):
    assert(prg)
    Window.__init__(self, prg)
    self.bookmarkIndex = 0
    self.prg = prg
    self.showFooter = True
    self.useInteractiveFind = True
    self.showLineNumbers = True
    self.showMessageLine = False
    self.showRightColumn = True
    self.showTopInfo = True
    self.color = curses.color_pair(0)
    self.colorSelected = curses.color_pair(app.prefs.selectedColor)
    self.controller = app.controller.MainController(self)
    self.controller.add(app.cu_editor.CuaPlusEdit(prg, self))
    # What does the user appear to want: edit, quit, or something else?
    self.userIntent = 'edit'
    if 1:
      self.confirmClose = LabeledLine(self,
          "Save changes? (yes, no, or cancel): ")
      self.confirmClose.setController(app.cu_editor.ConfirmClose)
    if 1:
      self.confirmOverwrite = LabeledLine(self,
          "Overwrite exiting file? (yes or no): ")
      self.confirmOverwrite.setController(app.cu_editor.ConfirmOverwrite)
    self.contextMenu = Menu(prg, self)
    if 1:
      self.interactiveFind = LabeledLine(self, 'find: ')
      self.interactiveFind.setController(app.cu_editor.InteractiveFind)
    if 1:
      self.interactiveGoto = LabeledLine(self, 'goto: ')
      self.interactiveGoto.setController(app.cu_editor.InteractiveGoto)
    if 1:
      self.interactiveOpen = LabeledLine(self, 'open: ')
      self.interactiveOpen.setController(app.cu_editor.InteractiveOpener)
    if 1:
      self.interactivePrediction = LabeledLine(self, 'p: ')
      self.interactivePrediction.setController(
          app.cu_editor.InteractivePrediction)
    if 1:
      self.interactivePrompt = LabeledLine(self, "e: ")
      self.interactivePrompt.setController(app.cu_editor.InteractivePrompt)
    if 1:
      self.interactiveQuit = LabeledLine(self,
          "Save changes? (yes, no, or cancel): ")
      self.interactiveQuit.setController(app.cu_editor.InteractiveQuit)
    if 1:
      self.interactiveSaveAs = LabeledLine(self, "save as: ")
      self.interactiveSaveAs.setController(app.cu_editor.InteractiveSaveAs)
    if 1:
      self.topInfo = TopInfo(self)
      self.topInfo.color = curses.color_pair(168)
      self.topInfo.colorSelected = curses.color_pair(47)
      self.topInfo.setParent(self, 0)
      if not self.showTopInfo:
        self.topInfo.hide()
    if 1:
      self.statusLine = StatusLine(self)
      self.statusLine.color = curses.color_pair(168)
      self.statusLine.colorSelected = curses.color_pair(47)
      self.statusLine.setParent(self, 0)
      if not self.showFooter:
        self.statusLine.hide()
    if 1:
      self.leftColumn = LineNumbers(self)
      self.leftColumn.color = curses.color_pair(211)
      self.leftColumn.colorSelected = curses.color_pair(146)
      self.leftColumn.setParent(self, 0)
      if not self.showLineNumbers:
        self.leftColumn.hide()
    if 1:
      self.logoCorner = StaticWindow(self)
      self.logoCorner.name = 'Logo'
      self.logoCorner.color = curses.color_pair(168)
      self.logoCorner.colorSelected = curses.color_pair(146)
      self.logoCorner.setParent(self, 0)
    if 1:
      self.rightColumn = StaticWindow(self)
      self.rightColumn.name = 'Right'
      self.rightColumn.color = curses.color_pair(18)
      self.rightColumn.colorSelected = curses.color_pair(105)
      self.rightColumn.setParent(self, 0)
      if not self.showRightColumn:
        self.rightColumn.hide()
    if self.showMessageLine:
      self.messageLine = MessageLine(self)
      self.messageLine.color = curses.color_pair(3)
      self.messageLine.colorSelected = curses.color_pair(87)
      self.messageLine.setParent(self, 0)
      if not self.showMessageLine:
        self.messageLine.hide()

  def startup(self):
    for f in self.prg.cliFiles:
      app.buffer_manager.buffers.loadTextBuffer(f['path'])
    if self.prg.readStdin:
      app.buffer_manager.buffers.readStdin()
    tb = app.buffer_manager.buffers.topBuffer()
    if not tb:
      tb = app.buffer_manager.buffers.newTextBuffer()
    self.setTextBuffer(tb)
    if self.prg.openToLine is not None:
      self.textBuffer.selectText(self.prg.openToLine - 1, 0, 0,
          app.selectable.kSelectionNone)

  def reshape(self, rows, cols, top, left):
    """Change self and sub-windows to fit within the given rectangle."""
    app.log.detail('reshape', rows, cols, top, left)
    lineNumbersCols = 7
    bottomRows = 1  # Not including status line.

    if self.showTopInfo:
      self.topInfo.reshape(0, cols-lineNumbersCols, top,
          left+lineNumbersCols)
    self.confirmClose.reshape(1, cols, top+rows-1, left)
    self.confirmOverwrite.reshape(1, cols, top+rows-1, left)
    self.interactiveOpen.reshape(1, cols, top+rows-1, left)
    self.interactivePrediction.reshape(1, cols, top+rows-1, left)
    self.interactivePrompt.reshape(1, cols, top+rows-1, left)
    self.interactiveQuit.reshape(1, cols, top+rows-1, left)
    self.interactiveSaveAs.reshape(1, cols, top+rows-1, left)
    if self.showMessageLine:
      self.messageLine.reshape(bottomRows, cols, top+rows-bottomRows, left)
    if self.useInteractiveFind:
      self.interactiveFind.reshape(bottomRows, cols,
          top+rows-bottomRows, left)
    if 1:
      self.interactiveGoto.reshape(bottomRows, cols, top+rows-bottomRows, left)
    if self.showFooter:
      self.statusLine.reshape(1, cols, top+rows-bottomRows-1, left)
      rows -= bottomRows+1
    if self.showLineNumbers:
      self.leftColumn.reshape(rows, lineNumbersCols, top, left)
      cols -= lineNumbersCols
      left += lineNumbersCols
    if self.showRightColumn:
      self.rightColumn.reshape(rows, 1, top, left+cols-1)
      cols -= 1
    # The top, left of the main window is the rows, cols of the logo corner.
    self.logoCorner.reshape(top, left, 0, 0)
    Window.reshape(self, rows, cols, top, left)

  def resizeTopBy(self, rowDelta):
    Window.resizeTopBy(self, rowDelta)
    self.leftColumn.resizeTopBy(rowDelta)
    self.logoCorner.resizeBottomBy(rowDelta)
    self.rightColumn.resizeTopBy(rowDelta)
    self.textBuffer.updateScrollPosition()

  def drawLogoCorner(self):
    """."""
    maxRow, maxCol = self.logoCorner.cursorWindow.getmaxyx()
    color = self.logoCorner.color
    for i in range(maxRow):
      self.logoCorner.addStr(i, 0, ' '*maxCol, color)
    self.logoCorner.addStr(0, 1, 'ci', color)
    self.logoCorner.refresh()

  def drawRightEdge(self):
    """Draw makers to indicate text extending past the right edge of the
    window."""
    maxRow, maxCol = self.cursorWindow.getmaxyx()
    limit = min(maxRow, len(self.textBuffer.lines)-self.scrollRow)
    for i in range(limit):
      color = self.rightColumn.color
      if len(self.textBuffer.lines[
          i+self.scrollRow])-self.scrollCol > maxCol:
        color = self.rightColumn.colorSelected
      self.rightColumn.addStr(i, 0, ' ', color)
    color = curses.color_pair(app.prefs.outsideOfBufferColorIndex)
    for i in range(limit, maxRow):
      self.rightColumn.addStr(i, 0, ' ', color)
    self.rightColumn.cursorWindow.refresh()

  def focus(self):
    if self.showMessageLine:
      self.messageLine.show()
    Window.focus(self)

  def quitNow(self):
    self.prg.quitNow()

  def refresh(self):
    self.textBuffer.updateScrollPosition()
    self.topInfo.onChange()
    self.drawLogoCorner()
    self.drawRightEdge()
    Window.refresh(self)

  def setTextBuffer(self, textBuffer):
    app.log.info('setTextBuffer')
    #self.normalize()
    #restore positions and selections  +
    textBuffer.lineLimitIndicator = 80
    self.controller.setTextBuffer(textBuffer)
    Window.setTextBuffer(self, textBuffer)
    self.textBuffer.debugRedo = self.prg.debugRedo
    # Restore cursor position.
    cursor = app.history.get(['files', textBuffer.fullPath, 'cursor'], (0, 0))
    if not len(textBuffer.lines):
      row = col = 0
    else:
      row = max(0, min(cursor[0], len(textBuffer.lines)-1))
      col = max(0, min(cursor[1], len(textBuffer.lines[row])))
    textBuffer.selectText(row, col, 0, app.selectable.kSelectionNone)

  def unfocus(self):
    if self.showMessageLine:
      self.messageLine.hide()
    Window.unfocus(self)


class PaletteWindow(ActiveWindow):
  """A window with example foreground and background text colors."""
  def __init__(self, prg):
    ActiveWindow.__init__(self, prg)
    self.resizeTo(16, 16*5)
    self.moveTo(8, 8)
    self.controller = app.controller.MainController(self)
    self.controller.add(app.cu_editor.PaletteDialogController(
        prg, self))

  def refresh(self):
    width = 16
    rows = 16
    for i in range(width):
      for k in range(rows):
        self.addStr(k, i*5, ' %3d '%(i+k*width,), curses.color_pair(i+k*width))
    self.cursorWindow.refresh()

