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
import app.color
import app.controller
import app.cu_editor
import app.editor
import app.history
import app.text_buffer
import sys
import curses


# The terminal area that the curses can draw to.
mainCursesWindow = None


class StaticWindow:
  """A static window does not get focus.
  parent is responsible for the order in which this window is updated, relative
  to its siblings."""
  def __init__(self, parent):
    self.parent = parent
    self.zOrder = []
    self.isFocusable = False
    self.top = 0
    self.left = 0
    self.rows = 1
    self.cols = 1
    self.scrollRow = 0
    self.scrollCol = 0
    self.writeLineRow = 0

  def addStr(self, row, col, text, colorPair):
    """Overwrite text a row, column with text."""
    if 0:
      if 0:
        if row < 0 or col >= self.cols:
          return
        if col < 0:
          text = text[col * -1:]
          col = 0
        if len(text) > self.cols:
          text = text[:self.cols]
      else:
        assert row >= 0, row
        assert row < self.rows, "%d, %d" %(row, self.rows)
        assert col <= self.cols, "%d, %d" %(col, self.cols)
        assert col >= 0, col
        assert len(text) <= self.cols, "%d, %d" %(len(text), self.cols)
    try:
      mainCursesWindow.addstr(self.top + row, self.left + col, text, colorPair)
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
    mainCursesWindow.chgat(self.top + row, self.left + col, count, colorPair)

  def presentModal(self, changeTo, paneRow, paneCol):
    self.parent.presentModal(changeTo, paneRow, paneCol)

  def blank(self, colorPair):
    """Clear the window."""
    for i in range(self.rows):
      self.addStr(i, 0, ' '*self.cols, colorPair)

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
    except ValueError: app.log.detail(repr(self) + 'not found in zOrder')

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
    self.top = top
    self.left = left

  def moveBy(self, top, left):
    self.top += top
    self.left += left

  def refresh(self):
    """Redraw window."""
    for child in self.zOrder:
      child.refresh()

  def reshape(self, rows, cols, top, left):
    self.moveTo(top, left)
    self.resizeTo(rows, cols)

  def resizeTo(self, rows, cols):
    app.log.detail(rows, cols, self)
    assert rows >=0, rows
    assert cols >=0, cols
    self.rows = rows
    self.cols = cols

  def resizeBottomBy(self, rows):
    self.rows += rows

  def resizeBy(self, rows, cols):
    self.rows += rows
    self.cols += cols

  def resizeTopBy(self, rows):
    self.top += rows
    self.rows -= rows

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

  def writeLine(self, text, color):
    """Simple line writer for static windows."""
    text = str(text)[:self.cols]
    text = text + ' ' * max(0, self.cols - len(text))
    try:
      mainCursesWindow.addstr(self.top + self.writeLineRow, self.left, text,
          color)
    except curses.error: pass
    self.writeLineRow += 1


class ActiveWindow(StaticWindow):
  """An ActiveWindow may have focus and a controller."""
  def __init__(self, parent, controller=None):
    StaticWindow.__init__(self, parent)
    self.controller = controller
    self.isFocusable = True
    self.shouldShowCursor = False

  def focus(self):
    app.log.info(self)
    self.hasFocus = True
    try: self.parent.zOrder.remove(self)
    except ValueError: app.log.detail(repr(self)+'not found in zOrder')
    self.parent.zOrder.append(self)
    self.controller.focus()

  def setController(self, controllerClass):
    self.controller = controllerClass(self.host)
    self.controller.setTextBuffer(self.textBuffer)

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
    self.hasCaptiveCursor = app.prefs.editor['captiveCursor']
    self.hasFocus = False
    self.shouldShowCursor = True
    self.textBuffer = None

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
    self.textBuffer.draw(self)
    StaticWindow.refresh(self)
    if self.hasFocus:
      self.parent.debugDraw(self)
      self.shouldShowCursor = (self.cursorRow >= self.scrollRow and
          self.cursorRow < self.scrollRow+self.rows)

  def setTextBuffer(self, textBuffer):
    textBuffer.setView(self)
    self.textBuffer = textBuffer

  def unfocus(self):
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

  def refresh(self):
    self.leftColumn.addStr(0, 0, self.label,
        app.prefs.color['default'])
    Window.refresh(self)

  def reshape(self, rows, cols, top, left):
    labelWidth = len(self.label)
    Window.reshape(self, rows, max(0, cols - labelWidth), top,
        left + labelWidth)
    self.leftColumn.reshape(rows, labelWidth, top, left)

  def setController(self, controllerClass):
    self.controller = controllerClass(self.host)
    self.controller.setTextBuffer(self.textBuffer)

  def setLabel(self, label):
    self.label = label
    self.reshape(self.rows, self.cols, self.top, self.left)

  def unfocus(self):
    self.blank(app.color.get('message_line'))
    self.hide()
    self.leftColumn.blank(app.color.get('message_line'))
    self.leftColumn.hide()
    Window.unfocus(self)


class Menu(StaticWindow):
  """"""
  def __init__(self, host):
    StaticWindow.__init__(self, host)
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
    self.reshape(len(self.lines), longest + 2, left, top)

  def refresh(self):
    color = app.color.get('context_menu')
    maxRow, maxCol = self.rows, self.cols
    self.writeLineRow = 0
    for i in self.lines[:maxRow]:
      self.writeLine(" "+i, color);
    StaticWindow.refresh(self)

  def setController(self, controllerClass):
    self.controller = controllerClass(self.host)
    self.controller.setTextBuffer(self.textBuffer)


class LineNumbers(StaticWindow):
  def __init__(self, host):
    StaticWindow.__init__(self, host)
    self.host = host

  def drawLineNumbers(self):
    maxRow, maxCol = self.rows, self.cols
    textBuffer = self.host.textBuffer
    limit = min(maxRow, len(textBuffer.lines)-self.host.scrollRow)
    color = app.color.get('line_number')
    for i in range(limit):
      self.addStr(i, 0, ' %5d '%(self.host.scrollRow + i + 1), color)
    color = app.color.get('outside_document')
    for i in range(limit, maxRow):
      self.addStr(i, 0, '       ', color)
    cursorAt = self.host.cursorRow - self.host.scrollRow
    if 0 <= cursorAt < limit:
      color = app.color.get('line_number_current')
      self.addStr(cursorAt, 1, '%5d'%(self.host.cursorRow + 1), color)

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
    app.log.meta(" " * 10, self.refreshCounter, "- screen refresh -")
    maxRow, maxCol = self.rows, self.cols
    self.writeLineRow = 0
    colorA = app.color.get(0)
    colorB = app.color.get(96)
    for i in self.lines[-maxRow:]:
      color = colorA
      if len(i) and i[-1] == '-':
        color = colorB
      self.writeLine(i, color);
    StaticWindow.refresh(self)


class InteractiveFind(Window):
  def __init__(self, host):
    Window.__init__(self, host)
    self.findLine = LabeledLine(self, 'find: ')
    self.findLine.setController(app.cu_editor.InteractiveFind)
    self.zOrder.append(self.findLine)
    self.replaceLine = LabeledLine(self, 'replace: ')
    self.replaceLine.setController(app.cu_editor.InteractiveFind)
    self.zOrder.append(self.replaceLine)
    self.setTextBuffer(app.text_buffer.TextBuffer())
    self.controller = app.cu_editor.InteractiveFind(host, self.findLine.textBuffer)

  def reshape(self, rows, cols, top, left):
    self.findLine.reshape(1, cols, top, left)
    top += 1
    self.replaceLine.reshape(1, cols, top, left)


class MessageLine(StaticWindow):
  """The message line appears at the bottom of the screen."""
  def __init__(self, host):
    StaticWindow.__init__(self, host)
    self.host = host
    self.message = None
    self.renderedMessage = None

  def refresh(self):
    if self.message:
      if self.message != self.renderedMessage:
        self.writeLineRow = 0
        self.writeLine(self.message[0], app.color.get('message_line'))
    else:
      self.blank(app.color.get('message_line'))


class StatusLine(StaticWindow):
  """The status line appears at the bottom of the screen. It shows the current
  line and column the cursor is on."""
  def __init__(self, host):
    StaticWindow.__init__(self, host)
    self.host = host

  def refresh(self):
    maxRow, maxCol = self.rows, self.cols
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
        colPercentage = self.host.cursorCol * 100 / charCount
      else:
        colPercentage = 100
    # Format.
    rightSide = ''
    if len(statusLine):
      rightSide += ' |'
    if app.prefs.startup.get('showLogWindow'):
      rightSide += ' %s | %s |'%(tb.cursorGrammarName(), tb.selectionModeName())
    rightSide += ' %4d,%2d | %3d%%,%3d%%'%(
        self.host.cursorRow+1, self.host.cursorCol + 1,
        rowPercentage,
        colPercentage)
    statusLine += ' ' * (maxCol - len(statusLine) - len(rightSide)) + rightSide
    color = app.color.get('status_line')
    self.addStr(0, 0, statusLine[:self.cols], color)


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
    # TODO: Make dynamic topinfo work properly
    if len(tb.lines):
      lineCursor = self.host.scrollRow
      line = ""
      if len(tb.lines) > lineCursor:
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
      if tb.isReadOnly:
        pathLine += ' [RO]'
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
      self.host.topRows = infoRows
      self.host.layout()
      self.borrowedRows = infoRows

  def refresh(self):
    """Render the context information at the top of the window."""
    lines = self.lines[-self.mode:]
    lines.reverse()
    color = app.color.get('top_info')
    for i,line in enumerate(lines):
      self.addStr(i, 0, (line + ' ' * (self.cols - len(line)))[:self.cols],
          color)
    for i in range(len(lines), self.rows):
      self.addStr(i, 0, ' ' * self.cols, color)

  def reshape(self, rows, cols, top, left):
    self.borrowedRows = 0
    StaticWindow.reshape(self, rows, cols, top, left)


class InputWindow(Window):
  """This is the main content window. Often the largest pane displayed."""
  def __init__(self, host):
    assert(host)
    Window.__init__(self, host)
    self.bookmarkIndex = 0
    self.bottomRows = 1  # Not including status line.
    self.host = host
    self.showFooter = True
    self.useInteractiveFind = True
    self.showLineNumbers = app.prefs.editor.get(
        'showLineNumbers', True)
    self.showMessageLine = True
    self.showRightColumn = True
    self.showTopInfo = True
    self.topRows = 0
    self.controller = app.controller.MainController(self)
    self.controller.add(app.cu_editor.CuaPlusEdit(self))
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
    self.contextMenu = Menu(self)
    if 0:  # wip on multi-line interactive find.
      self.interactiveFind = InteractiveFind(self)
    else:
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
      self.topInfo.setParent(self, 0)
      if not self.showTopInfo:
        self.topInfo.hide()
    if 1:
      self.statusLine = StatusLine(self)
      self.statusLine.setParent(self, 0)
      if not self.showFooter:
        self.statusLine.hide()
    if 1:
      self.lineNumberColumn = LineNumbers(self)
      self.lineNumberColumn.setParent(self, 0)
      if not self.showLineNumbers:
        self.lineNumberColumn.hide()
    if 1:
      self.logoCorner = StaticWindow(self)
      self.logoCorner.name = 'Logo'
      self.logoCorner.setParent(self, 0)
    if 1:
      self.rightColumn = StaticWindow(self)
      self.rightColumn.name = 'Right'
      self.rightColumn.setParent(self, 0)
      if not self.showRightColumn:
        self.rightColumn.hide()
    if self.showMessageLine:
      self.messageLine = MessageLine(self)
      self.messageLine.setParent(self, 0)

  if 0:
    def splitWindow(self):
      """
      Experimental.
      """
      app.log.info()
      other = InputWindow(self.prg)
      other.setTextBuffer(self.textBuffer)
      app.log.info()
      self.prg.zOrder.append(other)
      self.prg.layout()
      app.log.info()

  def startup(self):
    for f in app.prefs.startup.get('cliFiles', []):
      app.buffer_manager.buffers.loadTextBuffer(f['path'])
    if app.prefs.startup.get('readStdin'):
      app.buffer_manager.buffers.readStdin()
    tb = app.buffer_manager.buffers.topBuffer()
    if not tb:
      tb = app.buffer_manager.buffers.newTextBuffer()
    self.setTextBuffer(tb)
    openToLine = app.prefs.startup.get('openToLine')
    if openToLine is not None:
      self.textBuffer.selectText(openToLine - 1, 0, 0,
          app.selectable.kSelectionNone)

  def reshape(self, rows, cols, top, left):
    """Change self and sub-windows to fit within the given rectangle."""
    app.log.detail('reshape', rows, cols, top, left)
    self.outerShape = (rows, cols, top, left)
    self.layout()

  def layout(self):
    """Change self and sub-windows to fit within the given rectangle."""
    app.log.info()
    rows, cols, top, left = self.outerShape
    lineNumbersCols = 7
    topRows = self.topRows
    bottomRows = self.bottomRows

    if self.showTopInfo and rows > topRows and cols > lineNumbersCols:
      self.topInfo.reshape(topRows, cols - lineNumbersCols, top,
          left + lineNumbersCols)
      top += topRows
      rows -= topRows
    rows -= bottomRows
    bottomFirstRow = top + rows
    self.confirmClose.reshape(bottomRows, cols, bottomFirstRow, left)
    self.confirmOverwrite.reshape(bottomRows, cols, bottomFirstRow, left)
    self.interactiveOpen.reshape(bottomRows, cols, bottomFirstRow, left)
    self.interactivePrediction.reshape(bottomRows, cols, bottomFirstRow, left)
    self.interactivePrompt.reshape(bottomRows, cols, bottomFirstRow, left)
    self.interactiveQuit.reshape(bottomRows, cols, bottomFirstRow, left)
    self.interactiveSaveAs.reshape(bottomRows, cols, bottomFirstRow, left)
    if self.showMessageLine:
      self.messageLine.reshape(bottomRows, cols, bottomFirstRow, left)
    if self.useInteractiveFind:
      self.interactiveFind.reshape(bottomRows, cols, bottomFirstRow, left)
    if 1:
      self.interactiveGoto.reshape(bottomRows, cols, bottomFirstRow,
          left)
    if self.showFooter and rows > 0:
      self.statusLine.reshape(1, cols, bottomFirstRow - 1, left)
      rows -= 1
    if self.showLineNumbers and cols > lineNumbersCols:
      self.lineNumberColumn.reshape(rows, lineNumbersCols, top, left)
      cols -= lineNumbersCols
      left += lineNumbersCols
    if self.showRightColumn and cols > 0:
      self.rightColumn.reshape(rows, 1, top, left + cols - 1)
      cols -= 1
    # The top, left of the main window is the rows, cols of the logo corner.
    self.logoCorner.reshape(top, left, 0, 0)
    Window.reshape(self, rows, cols, top, left)

  def drawLogoCorner(self):
    """."""
    logo = self.logoCorner
    if logo.rows <= 0 or logo.cols <= 0:
      return
    color = app.color.get('logo')
    for i in range(logo.rows):
      logo.addStr(i, 0, ' ' * logo.cols, color)
    logo.addStr(0, 1, 'ci'[:self.cols], color)
    logo.refresh()

  def drawRightEdge(self):
    """Draw makers to indicate text extending past the right edge of the
    window."""
    maxRow, maxCol = self.rows, self.cols
    limit = min(maxRow, len(self.textBuffer.lines)-self.scrollRow)
    for i in range(limit):
      color = app.color.get('right_column')
      if len(self.textBuffer.lines[
          i + self.scrollRow]) - self.scrollCol > maxCol:
        color = app.color.get('line_overflow')
      self.rightColumn.addStr(i, 0, ' ', color)
    color = app.color.get('outside_document')
    for i in range(limit, maxRow):
      self.rightColumn.addStr(i, 0, ' ', color)

  def focus(self):
    app.log.debug()
    self.layout()
    if self.showMessageLine:
      self.messageLine.show()
    Window.focus(self)

  def quitNow(self):
    self.host.quitNow()

  def refresh(self):
    self.textBuffer.updateScrollPosition()
    self.topInfo.onChange()
    self.drawLogoCorner()
    self.drawRightEdge()
    Window.refresh(self)

  def setTextBuffer(self, textBuffer):
    app.log.info('setTextBuffer')
    #self.normalize()
    if self.textBuffer is not None:
      app.history.set(['files', self.textBuffer.fullPath, 'cursor'],
          (self.textBuffer.penRow, self.textBuffer.penCol))
    # TODO(dschuyler): Do we need to restore positions and selections here?
    self.controller.setTextBuffer(textBuffer)
    Window.setTextBuffer(self, textBuffer)
    self.textBuffer.debugRedo = app.prefs.startup.get('debugRedo')
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
    self.controller.add(app.cu_editor.PaletteDialogController(self))

  def refresh(self):
    width = 16
    rows = 16
    for i in range(width):
      for k in range(rows):
        self.addStr(k, i*5, ' %3d '%(i+k*width,), app.color.get(i+k*width))

