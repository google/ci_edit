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
import app.em_editor
import app.history
import app.render
import app.text_buffer
import app.vi_editor
import sys
import curses


# The terminal area that the curses can draw to.
mainCursesWindow = None


class ViewWindow:
  """A view window is a base window that does not get focus or have TextBuffer.
  See class ActiveWindow for a window that can get focus.
  See class Window for a window that can get focus and have a TextBuffer.
  """
  def __init__(self, parent):
    """
    Args:
      parent is responsible for the order in which this window is updated,
      relative to its siblings.
    """
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
    """Overwrite text at row, column with text. The caller is responsible for
    avoiding overdraw.
    """
    #app.log.check_le(row, self.rows)
    #app.log.check_le(col, self.cols)
    app.render.frame.addStr(self.top + row, self.left + col,
        text.encode('utf-8'), colorPair)

  def changeFocusTo(self, changeTo):
    self.parent.changeFocusTo(changeTo)

  def normalize(self):
    self.parent.normalize()

  def paint(self, row, col, count, colorPair):
    """Paint text a row, column with colorPair.
      fyi, I thought this may be faster than using addStr to paint over the text
      with a different colorPair. It looks like there isn't a significant
      performance difference between chgat and addstr.
    """
    mainCursesWindow.chgat(self.top + row, self.left + col, count, colorPair)

  def presentModal(self, changeTo, paneRow, paneCol):
    self.parent.presentModal(changeTo, paneRow, paneCol)

  def blank(self, colorPair):
    """Clear the window."""
    for i in range(self.rows):
      self.addStr(i, 0, ' ' * self.cols, colorPair)

  def contains(self, row, col):
    """Determine whether the position at row, col lay within this window."""
    for i in self.zOrder:
      if i.contains(row, col):
        return i
    return (self.top <= row < self.top + self.rows and
        self.left <= col < self.left + self.cols and self)

  def debugDraw(self, win):
    self.parent.debugDraw(win)

  def debugUndoDraw(self, win):
    self.parent.debugUndoDraw(win)

  def hide(self):
    """Remove window from the render list."""
    try:
      self.parent.zOrder.remove(self)
    except ValueError:
      app.log.detail(repr(self) + 'not found in zOrder')

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

  def render(self):
    """Redraw window."""
    for child in self.zOrder:
      child.render()

  def reshape(self, rows, cols, top, left):
    self.moveTo(top, left)
    self.resizeTo(rows, cols)

  def resizeTo(self, rows, cols):
    #app.log.detail(rows, cols, self)
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
    """Setting the parent will cause the the window to refresh (i.e. if self
    was hidden with hide() it will no longer be hidden).
    """
    if self.parent:
      try:
        self.parent.zOrder.remove(self)
      except Exception:
        pass
    self.parent = parent
    if parent:
      self.parent.zOrder.insert(layerIndex, self)

  def show(self):
    """Show window and bring it to the top layer."""
    try:
      self.parent.zOrder.remove(self)
    except Exception:
      pass
    self.parent.zOrder.append(self)

  def writeLine(self, text, color):
    """Simple line writer for static windows."""
    text = unicode(text)[:self.cols]
    text = text + ' ' * max(0, self.cols - len(text))
    app.render.frame.addStr(self.top + self.writeLineRow, self.left,
        text.encode('utf-8'), color)
    self.writeLineRow += 1


class ActiveWindow(ViewWindow):
  """An ActiveWindow may have focus and a controller."""
  def __init__(self, parent):
    ViewWindow.__init__(self, parent)
    self.controller = None
    self.isFocusable = True

  def focus(self):
    app.log.info(self)
    self.hasFocus = True
    try:
      self.parent.zOrder.remove(self)
    except ValueError:
      app.log.detail(repr(self) + 'not found in zOrder')
    self.parent.zOrder.append(self)
    self.controller.focus()

  def unfocus(self):
    app.log.info(self)
    self.hasFocus = False
    self.controller.unfocus()


class Window(ActiveWindow):
  """A Window holds a TextBuffer and a controller that operates on the
  TextBuffer."""
  def __init__(self, parent):
    ActiveWindow.__init__(self, parent)
    self.cursorRow = 0
    self.cursorCol = 0
    self.hasCaptiveCursor = app.prefs.editor['captiveCursor']
    self.hasFocus = False
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

  def render(self):
    self.cursorRow = self.textBuffer.penRow
    self.cursorCol = self.textBuffer.penCol
    self.textBuffer.draw(self)
    ViewWindow.render(self)
    if self.hasFocus:
      self.parent.debugDraw(self)
      self.parent.debugUndoDraw(self)
      if (self.cursorRow >= self.scrollRow and
          self.cursorRow < self.scrollRow + self.rows):
        app.render.frame.setCursor((
            self.top + self.cursorRow - self.scrollRow,
            self.left + self.cursorCol - self.scrollCol))
      else:
        app.render.frame.setCursor(None)

  def setTextBuffer(self, textBuffer):
    textBuffer.setView(self)
    self.textBuffer = textBuffer

  def unfocus(self):
    ActiveWindow.unfocus(self)


class LabeledLine(Window):
  """A single line with a label. This is akin to a line prompt or gui modal
      dialog. It's used for things like 'find' and 'goto line'."""
  def __init__(self, parent, label):
    Window.__init__(self, parent)
    self.host = parent
    tb = app.text_buffer.TextBuffer()
    tb.rootGrammar = app.prefs.grammars['none']
    self.setTextBuffer(tb)
    self.label = label
    self.leftColumn = ViewWindow(self)

  def render(self):
    self.leftColumn.addStr(0, 0, self.label,
        app.color.get('keyword'))
    Window.render(self)

  def reshape(self, rows, cols, top, left):
    labelWidth = len(self.label)
    Window.reshape(self, rows, max(0, cols - labelWidth), top,
        left + labelWidth)
    self.leftColumn.reshape(rows, labelWidth, top, left)

  def setController(self, controllerClass):
    app.log.caller('                        ',self.textBuffer)
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


class Menu(ViewWindow):
  """Work in progress on a context menu.
  """
  def __init__(self, host):
    ViewWindow.__init__(self, host)
    self.host = host
    self.controller = None
    self.lines = []
    self.commands = []

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

  def render(self):
    color = app.color.get('context_menu')
    self.writeLineRow = 0
    for i in self.lines[:self.rows]:
      self.writeLine(" "+i, color);
    ViewWindow.render(self)

  def setController(self, controllerClass):
    app.log.info('                        ',self.textBuffer)
    self.controller = controllerClass(self.host)
    self.controller.setTextBuffer(self.textBuffer)


class LineNumbers(ViewWindow):
  def __init__(self, host):
    ViewWindow.__init__(self, host)
    self.host = host

  def drawLineNumbers(self):
    limit = min(self.rows,
        len(self.host.textBuffer.lines) - self.host.scrollRow)
    color = app.color.get('line_number')
    for i in range(limit):
      self.addStr(i, 0, ' %5d ' % (self.host.scrollRow + i + 1), color)
    color = app.color.get('outside_document')
    for i in range(limit, self.rows):
      self.addStr(i, 0, '       ', color)
    cursorAt = self.host.cursorRow - self.host.scrollRow
    if 0 <= cursorAt < limit:
      color = app.color.get('line_number_current')
      self.addStr(cursorAt, 1, '%5d' % (self.host.cursorRow + 1), color)

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
    self.host.textBuffer.mouseClick(paneRow, paneCol - self.cols, True, ctrl, alt)

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

  def render(self):
    self.drawLineNumbers()


class LogWindow(ViewWindow):
  def __init__(self, parent):
    ViewWindow.__init__(self, parent)
    self.lines = app.log.getLines()
    self.renderCounter = 0

  def render(self):
    self.renderCounter += 1
    app.log.meta(" " * 10, self.renderCounter, "- screen refresh -")
    self.writeLineRow = 0
    colorA = app.color.get('default')
    colorB = app.color.get('highlight')
    for i in self.lines[-self.rows:]:
      color = colorA
      if len(i) and i[-1] == '-':
        color = colorB
      self.writeLine(i, color);
    ViewWindow.render(self)


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
    self.controller = app.cu_editor.InteractiveFind(host,
        self.findLine.textBuffer)

  def reshape(self, rows, cols, top, left):
    self.findLine.reshape(1, cols, top, left)
    top += 1
    self.replaceLine.reshape(1, cols, top, left)


class MessageLine(ViewWindow):
  """The message line appears at the bottom of the screen."""
  def __init__(self, host):
    ViewWindow.__init__(self, host)
    self.host = host
    self.message = None
    self.renderedMessage = None

  def render(self):
    if self.message:
      if self.message != self.renderedMessage:
        self.writeLineRow = 0
        self.writeLine(self.message, app.color.get('message_line'))
    else:
      self.blank(app.color.get('message_line'))


class StatusLine(ViewWindow):
  """The status line appears at the bottom of the screen. It shows the current
  line and column the cursor is on."""
  def __init__(self, host):
    ViewWindow.__init__(self, host)
    self.host = host

  def render(self):
    tb = self.host.textBuffer
    color = app.color.get('status_line')
    if self.host.showTips:
      tipRows = app.help.docs['tips']
      if len(tipRows) + 1 < self.rows:
        for i in range(self.rows):
          self.addStr(i, 0, ' ' * self.cols, color)
        for i,k in enumerate(tipRows):
          self.addStr(i + 1, 4, k, color)
        self.addStr(1, 40, "(Press F1 to show/hide tips)",
            color | curses.A_REVERSE)

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
      rowPercentage = self.host.cursorRow * 100 / lineCount
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
      rightSide += ' %s | %s |' % (tb.cursorGrammarName(),
          tb.selectionModeName())
    rightSide += ' %4d,%2d | %3d%%,%3d%%' % (
        self.host.cursorRow+1, self.host.cursorCol + 1,
        rowPercentage,
        colPercentage)
    statusLine += \
        ' ' * (self.cols - len(statusLine) - len(rightSide)) + rightSide
    self.addStr(self.rows - 1, 0, statusLine[:self.cols], color)


class TopInfo(ViewWindow):
  def __init__(self, host):
    ViewWindow.__init__(self, host)
    self.host = host
    self.borrowedRows = 0
    self.lines = []
    self.mode = 2

  def onChange(self):
    if self.mode == 0:
      return
    tb = self.host.textBuffer
    lines = []
    # TODO: Make dynamic topInfo work properly
    if len(tb.lines):
      lineCursor = self.host.scrollRow
      line = ""
      # Check for extremely small window.
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

  def render(self):
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
    ViewWindow.reshape(self, rows, cols, top, left)


class InputWindow(Window):
  """This is the main content window. Often the largest pane displayed."""
  def __init__(self, host):
    assert(host)
    Window.__init__(self, host)
    self.bottomRows = 1  # Not including status line.
    self.host = host
    self.showFooter = True
    self.useInteractiveFind = True
    self.savedScrollPositions = {}
    self.showLineNumbers = app.prefs.editor.get(
        'showLineNumbers', True)
    self.showMessageLine = True
    self.showRightColumn = True
    self.showTopInfo = True
    self.statusLineCount = 0 if app.prefs.status.get('seenTips') else 8

    self.topRows = 2  # Number of lines in default TopInfo status.
    self.controller = app.controller.MainController(self)
    self.controller.add(app.em_editor.EmacsEdit(self))
    self.controller.add(app.vi_editor.ViEdit(self))
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
      self.logoCorner = ViewWindow(self)
      self.logoCorner.name = 'Logo'
      self.logoCorner.setParent(self, 0)
    if 1:
      self.rightColumn = ViewWindow(self)
      self.rightColumn.name = 'Right'
      self.rightColumn.setParent(self, 0)
      if not self.showRightColumn:
        self.rightColumn.hide()
    if self.showMessageLine:
      self.messageLine = MessageLine(self)
      self.messageLine.setParent(self, 0)
    self.showTips = app.prefs.status.get('showTips')
    self.statusLineCount = 8 if self.showTips else 1

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
      app.buffer_manager.buffers.loadTextBuffer(f['path'], self)
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
      self.statusLine.reshape(self.statusLineCount, cols,
          bottomFirstRow - self.statusLineCount, left)
      rows -= self.statusLineCount
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
    logo.render()

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

  def render(self):
    self.topInfo.onChange()
    self.drawLogoCorner()
    self.drawRightEdge()
    Window.render(self)

  def setTextBuffer(self, textBuffer):
    app.log.info('setTextBuffer')
    if self.textBuffer is not None:
      self.savedScrollPositions[self.textBuffer.fullPath] = (
          self.scrollRow, self.scrollCol)
    #self.normalize()
    textBuffer.lineLimitIndicator = app.prefs.editor['lineLimitIndicator']
    textBuffer.debugRedo = app.prefs.startup.get('debugRedo')
    Window.setTextBuffer(self, textBuffer)
    self.controller.setTextBuffer(textBuffer)
    savedScroll = self.savedScrollPositions.get(self.textBuffer.fullPath)
    if savedScroll is not None:
      self.scrollRow, self.scrollCol = savedScroll
    else:
      self.textBuffer.scrollToOptimalScrollPosition()

  def toggleShowTips(self):
    self.showTips = not self.showTips
    self.statusLineCount = 8 if self.showTips else 1
    self.layout()
    app.prefs.save('status', 'showTips', self.showTips)

  def unfocus(self):
    if self.showMessageLine:
      self.messageLine.hide()
    Window.unfocus(self)


class PaletteWindow(ActiveWindow):
  """A window with example foreground and background text colors."""
  def __init__(self, prg):
    ActiveWindow.__init__(self, prg)
    self.resizeTo(16, 16 * 5)
    self.moveTo(8, 8)
    self.controller = app.controller.MainController(self)
    self.controller.add(app.cu_editor.PaletteDialogController(self))

  def render(self):
    width = 16
    rows = 16
    for i in range(width):
      for k in range(rows):
        self.addStr(k, i * 5, ' %3d ' % (i + k * width,),
            app.color.get(i + k * width))

