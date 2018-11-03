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
  type(u"") is unicode
except:
  unicode = str
  unichr = chr

import bisect
import os
import sys
import types
import curses

import app.buffer_manager
import app.color
import app.config
import app.controller
import app.cu_editor
import app.em_editor
import app.render
import app.text_buffer
import app.vi_editor


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
    if app.config.strict_debug:
      assert issubclass(self.__class__, ViewWindow), self
      if parent is not None:
        assert issubclass(parent.__class__, ViewWindow), parent
    self.parent = parent
    self.isFocusable = False
    self.top = 0
    self.left = 0
    self.rows = 1
    self.cols = 1
    self.scrollRow = 0
    self.scrollCol = 0
    self.writeLineRow = 0
    self.zOrder = []

  def addStr(self, row, col, text, colorPair):
    """Overwrite text at row, column with text. The caller is responsible for
    avoiding overdraw.
    """
    if app.config.strict_debug:
      app.log.check_le(row, self.rows)
      app.log.check_le(col, self.cols)
    app.render.frame.addStr(self.top + row, self.left + col,
        text.encode('utf-8'), colorPair)

  def reattach(self):
    self.setParent(self.parent)

  def blank(self, colorPair):
    """Clear the window."""
    for i in range(self.rows):
      self.addStr(i, 0, ' ' * self.cols, colorPair)

  def bringChildToFront(self, child):
    """Bring it to the top layer."""
    try:
      self.zOrder.remove(child)
    except ValueError:
      pass
    self.zOrder.append(child)

  def bringToFront(self):
    """Bring it to the top layer."""
    self.parent.bringChildToFront(self)

  def changeFocusTo(self, changeTo):
    if app.config.strict_debug:
      assert issubclass(self.__class__, ViewWindow), self
      assert issubclass(changeTo.__class__, ViewWindow), changeTo
    topWindow = self
    while topWindow.parent:
      topWindow = topWindow.parent
    topWindow.changeFocusTo(changeTo)

  def contains(self, row, col):
    """Determine whether the position at row, col lay within this window."""
    for i in self.zOrder:
      if i.contains(row, col):
        return i
    return (self.top <= row < self.top + self.rows and
        self.left <= col < self.left + self.cols and self)

  def debugDraw(self):
    programWindow = self
    while programWindow.parent is not None:
      programWindow = programWindow.parent
    programWindow.debugDraw(self)

  def deselect(self):
    pass

  def detach(self):
    """Hide the window by removing self from parents' children, but keep same
    parent to be reattached later."""
    try:
      self.parent.zOrder.remove(self)
    except ValueError:
      pass

  def layoutHorizontally(self, children, separation=0):
    left = self.left
    cols = self.cols
    for view in children:
      preferredCols = view.preferredSize(self.rows, max(0, cols))[1]
      view.reshape(self.top, left, self.rows, max(0, min(cols, preferredCols)))
      delta = view.cols + separation
      left += delta
      cols -= delta

  def layoutVertically(self, children, separation=0):
    top = self.top
    rows = self.rows
    for view in children:
      preferredRows = view.preferredSize(max(0, rows), self.cols)[0]
      view.reshape(top, self.left, max(0, min(rows, preferredRows)), self.cols)
      delta = view.rows + separation
      top += delta
      rows -= delta

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

  def __childFocusableWindow(self, reverse=False):
    windows = self.zOrder[:]
    if reverse:
      windows.reverse()
    for i in windows:
      if i.isFocusable:
        return i
      else:
        r = i.__childFocusableWindow(reverse)
        if r is not None:
          return r

  def nextFocusableWindow(self, start, reverse=False):
    """Ignore |start| when searching."""
    windows = self.zOrder[:]
    if reverse:
      windows.reverse()
    try:
      found = windows.index(start)
    except ValueError:
      found = -1
    windows = windows[found + 1:]
    for i in windows:
      if i.isFocusable:
        return i
      else:
        r = i.__childFocusableWindow(reverse)
        if r is not None:
          return r
    r = self.parent.nextFocusableWindow(self, reverse)
    if r is not None:
      return r
    return self.__childFocusableWindow(reverse)

  def normalize(self):
    self.parent.normalize()

  def onPrefChanged(self, category, name):
    self.parent.onPrefChanged(category, name)

  def paint(self, row, col, count, colorPair):
    """Paint text a row, column with colorPair.
      fyi, I thought this may be faster than using addStr to paint over the text
      with a different colorPair. It looks like there isn't a significant
      performance difference between chgat and addstr.
    """
    mainCursesWindow.chgat(self.top + row, self.left + col, count, colorPair)

  def preferredSize(self, rowLimit, colLimit):
    # Derived classes should override this.
    return rowLimit, colLimit

  def presentModal(self, changeTo, paneRow, paneCol):
    self.parent.presentModal(changeTo, paneRow, paneCol)

  def priorFocusableWindow(self, start):
    return self.nextFocusableWindow(start, True)

  def quitNow(self):
    programWindow = self
    while programWindow.parent is not None:
      programWindow = programWindow.parent
    programWindow.quitNow()

  def render(self):
    """Redraw window."""
    for child in self.zOrder:
      child.render()

  def showWindowHierarchy(self, indent='  '):
    """For debugging."""
    focus = '[f]' if self.isFocusable else '[ ]'
    extra = ''
    if hasattr(self, 'label'):
      extra += ' "' + self.label + '"'
    app.log.info("%s%s%s%s" % (indent, focus, self, extra))
    for child in self.zOrder:
      child.showWindowHierarchy(indent + '  ')

  def showFullWindowHierarchy(self, indent='  '):
    """For debugging."""
    f = self
    while f.parent is not None:
      f = f.parent
    assert f
    f.showWindowHierarchy()

  def doPreCommand(self):
    pass

  def longTimeSlice(self):
    """returns whether work is finished (no need to call again)."""
    return True

  def shortTimeSlice(self):
    pass

  def reshape(self, top, left, rows, cols):
    self.moveTo(top, left)
    self.resizeTo(rows, cols)
    #app.log.debug(self, top, left, rows, cols)

  def resizeBottomBy(self, rows):
    self.rows += rows

  def resizeBy(self, rows, cols):
    self.rows += rows
    self.cols += cols

  def resizeTo(self, rows, cols):
    #app.log.detail(rows, cols, self)
    if app.config.strict_debug:
      assert rows >=0, rows
      assert cols >=0, cols
    self.rows = rows
    self.cols = cols

  def resizeTopBy(self, rows):
    self.top += rows
    self.rows -= rows

  def setParent(self, parent, layerIndex=sys.maxsize):
    """Setting the parent will cause the the window to refresh (i.e. if self
    was hidden with detach() it will no longer be hidden).
    """
    if app.config.strict_debug:
      assert issubclass(self.__class__, ViewWindow), self
      assert issubclass(parent.__class__, ViewWindow), parent
    if self.parent:
      try:
        self.parent.zOrder.remove(self)
      except ValueError:
        pass
    self.parent = parent
    if parent:
      self.parent.zOrder.insert(layerIndex, self)

  def writeLine(self, text, color):
    """Simple line writer for static windows."""
    if app.config.strict_debug:
      type(text) is unicode
    text = text[:self.cols]
    text = text + u' ' * max(0, self.cols - len(text))
    app.render.frame.addStr(self.top + self.writeLineRow, self.left,
        text.encode(u'utf-8'), color)
    self.writeLineRow += 1


class ActiveWindow(ViewWindow):
  """An ActiveWindow may have focus and a controller."""
  def __init__(self, parent):
    if app.config.strict_debug:
      assert issubclass(self.__class__, ActiveWindow), self
      if parent is not None:
        assert issubclass(parent.__class__, ViewWindow), parent
    ViewWindow.__init__(self, parent)
    self.controller = None
    self.hasFocus = False
    self.isFocusable = True

  def focus(self):
    """
    Note: to focus a view it must have a controller. Focusing a view without a
        controller would make the program appear to freeze since nothing would
        be responding to user input.
    """
    self.hasFocus = True
    self.controller.focus()

  def setController(self, controller):
    if app.config.strict_debug:
      assert issubclass(self.__class__, Window), self
    self.controller = controller(self)

  def unfocus(self):
    self.hasFocus = False
    self.controller.unfocus()


class Window(ActiveWindow):
  """A Window holds a TextBuffer and a controller that operates on the
  TextBuffer."""
  def __init__(self, parent):
    if app.config.strict_debug:
      assert issubclass(self.__class__, Window), self
      assert issubclass(parent.__class__, ViewWindow), parent
    ActiveWindow.__init__(self, parent)
    self.hasCaptiveCursor = app.prefs.editor['captiveCursor']
    self.textBuffer = None

  def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
    if self.textBuffer:
      self.textBuffer.mouseClick(paneRow, paneCol, shift, ctrl, alt)

  def mouseDoubleClick(self, paneRow, paneCol, shift, ctrl, alt):
    if self.textBuffer:
      self.textBuffer.mouseDoubleClick(paneRow, paneCol, shift, ctrl, alt)

  def mouseMoved(self, paneRow, paneCol, shift, ctrl, alt):
    if self.textBuffer:
      self.textBuffer.mouseMoved(paneRow, paneCol, shift, ctrl, alt)

  def mouseRelease(self, paneRow, paneCol, shift, ctrl, alt):
    if self.textBuffer:
      self.textBuffer.mouseRelease(paneRow, paneCol, shift, ctrl, alt)

  def mouseTripleClick(self, paneRow, paneCol, shift, ctrl, alt):
    if self.textBuffer:
      self.textBuffer.mouseTripleClick(paneRow, paneCol, shift, ctrl, alt)

  def mouseWheelDown(self, shift, ctrl, alt):
    if self.textBuffer:
      self.textBuffer.mouseWheelDown(shift, ctrl, alt)

  def mouseWheelUp(self, shift, ctrl, alt):
    if self.textBuffer:
      self.textBuffer.mouseWheelUp(shift, ctrl, alt)

  def preferredSize(self, rowLimit, colLimit):
    return min(rowLimit, len(self.textBuffer.lines)), colLimit

  def render(self):
    if self.textBuffer:
      self.textBuffer.draw(self)
    ViewWindow.render(self)

  def setController(self, controller):
    ActiveWindow.setController(self, controller)
    self.controller.setTextBuffer(self.textBuffer)

  def setTextBuffer(self, textBuffer):
    textBuffer.setView(self)
    self.textBuffer = textBuffer

  def doPreCommand(self):
    if self.textBuffer is not None:
      self.textBuffer.setMessage()

  def longTimeSlice(self):
    """returns whether work is finished (no need to call again)."""
    finished = True
    tb = self.textBuffer
    if tb is not None and tb.parser.fullyParsedToLine < len(tb.lines):
      tb.parseDocument()
      # If a user event came in while parsing, the parsing will be paused (to be
      # resumed after handling the event).
      finished = tb.parser.fullyParsedToLine >= len(tb.lines)
    for child in self.zOrder:
      finished = finished and child.longTimeSlice()
    return finished

  def shortTimeSlice(self):
    if self.textBuffer is not None:
      self.textBuffer.parseScreenMaybe()


class LabelWindow(ViewWindow):
  """A text label. The label is inert, it will pass events to its parent."""
  def __init__(self, parent, label, preferredWidth=None, align='left'):
    if app.config.strict_debug:
      assert issubclass(parent.__class__, ViewWindow), parent
      assert type(label) == str
      assert preferredWidth is None or type(preferredWidth) == int
      assert type(align) == str
    ViewWindow.__init__(self, parent)
    self.label = label
    self.preferredWidth = preferredWidth
    self.align = -1 if align == 'left' else 1
    self.color = app.color.get('keyword')

  def preferredSize(self, rowLimit, colLimit):
    if app.config.strict_debug:
      assert self.parent
      assert rowLimit >= 0
      assert colLimit >= 0
    preferredWidth = self.preferredWidth if self.preferredWidth is not None \
        else len(self.label)
    return (min(rowLimit, 1), min(colLimit, preferredWidth))

  def render(self):
    if self.rows <= 0:
      return
    line = self.label[:self.cols]
    line = u"%*s" % (self.cols * self.align, line)
    self.addStr(0, 0, line, self.color)
    ViewWindow.render(self)


class LabeledLine(Window):
  """A single line with a label. This is akin to a line prompt or gui modal
      dialog. It's used for things like 'find' and 'goto line'."""
  def __init__(self, parent, label):
    if app.config.strict_debug:
      assert issubclass(self.__class__, LabeledLine), self
      assert issubclass(parent.__class__, ViewWindow), parent
    Window.__init__(self, parent)
    self.host = parent
    tb = app.text_buffer.TextBuffer()
    tb.rootGrammar = app.prefs.grammars['none']
    self.setTextBuffer(tb)
    self.label = label
    self.leftColumn = ViewWindow(self)
    # TODO(dschuyler) Add self.rightColumn.

  def focus(self):
    self.bringToFront()
    if not self.controller:
      app.log.info(self, repr(self.label))
    Window.focus(self)

  def preferredSize(self, rowLimit, colLimit):
    return min(rowLimit, 1), colLimit

  def render(self):
    #app.log.info('LabeledLine', self.label, self.rows, self.cols)
    if self.rows <= 0:
      return
    self.leftColumn.addStr(0, 0, self.label, app.color.get('keyword'))
    Window.render(self)

  def reshape(self, top, left, rows, cols):
    labelWidth = len(self.label)
    Window.reshape(self, top,
        left + labelWidth, rows, max(0, cols - labelWidth))
    self.leftColumn.reshape(top, left, rows, labelWidth)

  def setLabel(self, label):
    self.label = label
    self.reshape(self.top, self.left, self.rows, self.cols)


class Menu(ViewWindow):
  """Work in progress on a context menu.
  """
  def __init__(self, host):
    if app.config.strict_debug:
      assert issubclass(self.__class__, Menu), self
      assert issubclass(host.__class__, ActiveWindow), parent
    ViewWindow.__init__(self, host)
    self.host = host
    self.label = ''
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
    self.reshape(left, top, len(self.lines), longest + 2)

  def render(self):
    color = app.color.get('context_menu')
    self.writeLineRow = 0
    for i in self.lines[:self.rows]:
      self.writeLine(" "+i, color);
    ViewWindow.render(self)


class LineNumbers(ViewWindow):
  def __init__(self, host):
    ViewWindow.__init__(self, host)
    self.host = host

  def drawLineNumbers(self):
    limit = min(self.rows,
        len(self.host.textBuffer.lines) - self.host.scrollRow)
    cursorBookmarkColorIndex = None
    visibleBookmarks = self.getVisibleBookmarks(self.host.scrollRow,
                                                self.host.scrollRow + limit)
    currentBookmarkIndex = 0
    for i in range(limit):
      color = app.color.get('line_number')
      currentRow = self.host.scrollRow + i
      if currentBookmarkIndex < len(visibleBookmarks):
        currentBookmark = visibleBookmarks[currentBookmarkIndex]
      else:
        currentBookmark = None
      # Use a different color if the row is associated with a bookmark.
      if currentBookmark:
        if (currentRow >= currentBookmark.begin and
            currentRow <= currentBookmark.end):
          color = app.color.get(currentBookmark.data.get('colorIndex'))
          if self.host.textBuffer.penRow == currentRow:
            cursorBookmarkColorIndex = currentBookmark.data.get('colorIndex')
        if currentRow + 1 > currentBookmark.end:
          currentBookmarkIndex += 1
      self.addStr(i, 0, ' %5d ' % (currentRow + 1), color)
    # Draw indicators for text off of the left edge.
    if self.host.scrollCol > 0:
      color = app.color.get('line_overflow')
      for i in range(limit):
        if len(self.host.textBuffer.lines[self.host.scrollRow + i]) > 0:
          self.addStr(i, 6, ' ', color)
    # Draw blank line number rows past the end of the document.
    color = app.color.get('outside_document')
    for i in range(limit, self.rows):
      self.addStr(i, 0, '       ', color)
    # Highlight the line numbers for the current cursor line.
    cursorAt = self.host.textBuffer.penRow - self.host.scrollRow
    if 0 <= cursorAt < limit:
      if cursorBookmarkColorIndex:
        if app.prefs.startup['numColors'] == 8:
          color = app.color.get(cursorBookmarkColorIndex)
        else:
          color = app.color.get(cursorBookmarkColorIndex % 32 + 128)
      else:
        color = app.color.get('line_number_current')
      self.addStr(cursorAt, 1, '%5d' % (self.host.textBuffer.penRow + 1), color)

  def getVisibleBookmarks(self, beginRow, endRow):
    """
    Args:
      beginRow (int): the index of the line number that you want the list of
                      bookmarks to start from.
      endRow (int): the index of the line number that you want the list of
                    bookmarks to end at (exclusive).

    Returns:
      A list containing the bookmarks that are displayed on the screen. If there
      are no bookmarks, returns an empty list.
    """
    bookmarkList = self.host.textBuffer.bookmarks
    beginIndex = endIndex = 0
    if len(bookmarkList):
      needle = app.bookmark.Bookmark(beginRow, beginRow)
      beginIndex = bisect.bisect_left(bookmarkList, needle)
      if beginIndex > 0 and bookmarkList[beginIndex - 1].end >= beginRow:
        beginIndex -= 1
      needle.range = (endRow, endRow)
      endIndex = bisect.bisect_left(bookmarkList, needle)
    return bookmarkList[beginIndex:endIndex]

  def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
    if ctrl:
      app.log.info('click at', paneRow, paneCol)
      return
    self.host.changeFocusTo(self.host)
    tb = self.host.textBuffer
    if self.host.scrollRow + paneRow >= len(tb.lines):
      tb.selectionNone()
      return
    if shift:
      if tb.selectionMode == app.selectable.kSelectionNone:
        tb.selectionLine()
      self.mouseRelease(paneRow, paneCol, shift, ctrl, alt)
    else:
      tb.cursorMoveAndMark(self.host.scrollRow + paneRow - tb.penRow, 0,
                           self.host.scrollRow + paneRow - tb.markerRow, 0,
                           app.selectable.kSelectionNone - tb.selectionMode)
      self.mouseRelease(paneRow, paneCol, shift, ctrl, alt)

  def mouseDoubleClick(self, paneRow, paneCol, shift, ctrl, alt):
    self.host.textBuffer.selectionAll()

  def mouseMoved(self, paneRow, paneCol, shift, ctrl, alt):
    app.log.info(paneRow, paneCol, shift)
    self.host.textBuffer.mouseClick(paneRow, paneCol - self.cols, True, ctrl,
        alt)

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
    self.host = host
    self.expanded = False
    self.setController(app.cu_editor.InteractiveFind)
    indent = '  '

    self.findLine = LabeledLine(self, 'Find: ')
    self.findLine.setController(app.cu_editor.InteractiveFindInput)
    self.findLine.setParent(self)

    self.replaceLine = LabeledLine(self, 'Replace: ')
    self.replaceLine.setController(app.cu_editor.InteractiveReplaceInput)
    self.replaceLine.setParent(self)

    self.matchOptionsRow = RowWindow(self, 2)
    self.matchOptionsRow.setParent(self)

    # If findUseRegex is false, re.escape the search.
    toggle = OptionsToggle(self.matchOptionsRow, 'regex', 'editor',
        'findUseRegex')
    # If findWholeWord, wrap with \b.
    toggle = OptionsToggle(self.matchOptionsRow, 'wholeWord', 'editor',
        'findWholeWord')
    # If findIgnoreCase, pass ignore case flag to regex.
    toggle = OptionsToggle(self.matchOptionsRow, 'ignoreCase', 'editor',
        'findIgnoreCase')
    if 0:
      # Use locale.
      toggle = OptionsToggle(self.matchOptionsRow, 'locale', 'editor',
          'findLocale')
      # Span lines.
      toggle = OptionsToggle(self.matchOptionsRow, 'multiline', 'editor',
          'findMultiline')
      # Dot matches anything (even \n).
      toggle = OptionsToggle(self.matchOptionsRow, 'dotAll', 'editor',
          'findDotAll')
      # Unicode match.
      toggle = OptionsToggle(self.matchOptionsRow, 'unicode', 'editor',
          'findUnicode')
      # Replace uppercase with upper and lowercase with lower.
      toggle = OptionsToggle(self.matchOptionsRow, 'smartCaps', 'editor',
          'findReplaceSmartCaps')

    if 0:
      self.scopeOptions, self.scopeRow = self.addSelectOptionsRow(
          indent + 'scope     ', ['file', 'directory', 'openFiles', 'project'])
      self.changeCaseOptions, self.changeCaseRow = self.addSelectOptionsRow(
          indent + 'changeCase', ['none', 'smart', 'upper', 'lower'])
      self.withinOptions, self.withinOptionsRow = self.addSelectOptionsRow(
          indent + 'within    ', [
            'any',
            'code',
            'comment',
            'error',
            'markup',
            'misspelled',  # Find in misspelled words.
            'quoted',  # Find in strings.
          ])
      self.searchSelectionOption, self.searchSelectionRow = self.addSelectOptionsRow(
          indent + 'selection ', ['any', 'yes', 'no'])
      self.searchChangedOption, self.searchChangedRow = self.addSelectOptionsRow(
          indent + 'changed   ', ['any', 'yes', 'no'])
      self.pathsLine = LabeledLine(self, 'Paths: ')
      self.pathsLine.setController(app.cu_editor.InteractiveFindInput)
      self.pathsLine.setParent(self)

  def reattach(self):
    Window.reattach(self)
    # TODO(dschuyler): consider removing expanded control.
    # See https://github.com/google/ci_edit/issues/170
    self.expanded = True
    self.parent.layout()

  def detach(self):
    Window.detach(self)
    self.parent.layout()

  def addSelectOptionsRow(self, label, optionsList):
    """
    Such as a radio group.
    """
    optionsRow = OptionsRow(self)
    optionsRow.color = app.color.get('keyword')
    optionsRow.addLabel(label)
    optionsDict = {}
    optionsRow.beginGroup()
    for key in optionsList:
      optionsDict[key] = False
      optionsRow.addSelection(key, optionsDict)
    optionsRow.endGroup()
    optionsDict[optionsList[0]] = True
    optionsRow.setParent(self)
    return optionsDict, optionsRow

  def bringChildToFront(self, child):
    # The find window doesn't reorder children.
    pass

  def focus(self):
    self.reattach()
    if app.config.strict_debug:
      assert self.parent
      assert self.findLine.parent
      assert self.rows > 0, self.rows
      assert self.findLine.rows > 0, self.findLine.rows
    self.controller.focus()
    self.changeFocusTo(self.findLine)

  def preferredSize(self, rowLimit, colLimit):
    if app.config.strict_debug:
      assert self.parent
      assert rowLimit >= 0
      assert colLimit >= 0
    if self.parent and self in self.parent.zOrder and self.expanded:
      return (min(rowLimit, len(self.zOrder)), colLimit)
    return (1, -1)

  def expandFindWindow(self, expanded):
    self.expanded = expanded
    self.parent.layout()

  def reshape(self, top, left, rows, cols):
    Window.reshape(self, top, left, rows, cols)
    self.layoutVertically(self.zOrder)

  def unfocus(self):
    self.detach()
    Window.unfocus(self)


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
      color = (tb.message[1]
          if tb.message[1] is not None
          else app.color.get('status_line'))
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
      rowPercentage = self.host.textBuffer.penRow * 100 // lineCount
      charCount = len(tb.lines[self.host.textBuffer.penRow])
      if self.host.textBuffer.penCol != 0:
        colPercentage = self.host.textBuffer.penCol * 100 // charCount
    # Format.
    rightSide = ''
    if len(statusLine):
      rightSide += ' |'
    if app.prefs.startup.get('showLogWindow'):
      rightSide += ' %s | %s |' % (tb.cursorGrammarName(),
          tb.selectionModeName())
    rightSide += ' %4d,%2d | %3d%%,%3d%%' % (
        self.host.textBuffer.penRow + 1, self.host.textBuffer.penCol + 1,
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

  def reshape(self, top, left, rows, cols):
    self.borrowedRows = 0
    ViewWindow.reshape(self, top, left, rows, cols)


class InputWindow(Window):
  """This is the main content window. Often the largest pane displayed."""
  def __init__(self, host):
    if app.config.strict_debug:
      assert(host)
    Window.__init__(self, host)
    self.host = host
    self.showFooter = True
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
    if 1:  # wip on multi-line interactive find.
      self.interactiveFind = InteractiveFind(self)
      self.interactiveFind.setParent(self, 0)
    else:
      self.interactiveFind = LabeledLine(self, 'find: ')
      self.interactiveFind.setController(app.cu_editor.InteractiveFind)
    if 1:
      self.interactiveGoto = LabeledLine(self, 'goto: ')
      self.interactiveGoto.setController(app.cu_editor.InteractiveGoto)
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
      self.topInfo = TopInfo(self)
      self.topInfo.setParent(self, 0)
      if not self.showTopInfo:
        self.topInfo.detach()
    if 1:
      self.statusLine = StatusLine(self)
      self.statusLine.setParent(self, 0)
      if not self.showFooter:
        self.statusLine.detach()
    if 1:
      self.lineNumberColumn = LineNumbers(self)
      self.lineNumberColumn.setParent(self, 0)
      if not self.showLineNumbers:
        self.lineNumberColumn.detach()
    if 1:
      self.logoCorner = ViewWindow(self)
      self.logoCorner.name = 'Logo'
      self.logoCorner.setParent(self, 0)
    if 1:
      self.rightColumn = ViewWindow(self)
      self.rightColumn.name = 'Right'
      self.rightColumn.setParent(self, 0)
      if not self.showRightColumn:
        self.rightColumn.detach()
    if 1:
      self.popupWindow = PopupWindow(self)
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

  def layout(self):
    """Change self and sub-windows to fit within the given rectangle."""
    top, left, rows, cols = self.outerShape
    lineNumbersCols = 7
    topRows = self.topRows
    bottomRows = max(1, self.interactiveFind.preferredSize(rows, cols)[0])

    # The top, left of the main window is the rows, cols of the logo corner.
    self.logoCorner.reshape(top, left, 2, lineNumbersCols)

    if self.showTopInfo and rows > topRows and cols > lineNumbersCols:
      self.topInfo.reshape(top,
          left + lineNumbersCols, topRows, cols - lineNumbersCols)
      top += topRows
      rows -= topRows
    rows -= bottomRows
    bottomFirstRow = top + rows

    self.confirmClose.reshape(bottomFirstRow, left, bottomRows, cols)
    self.confirmOverwrite.reshape(bottomFirstRow, left, bottomRows, cols)
    self.interactivePrediction.reshape(bottomFirstRow, left, bottomRows, cols)
    self.interactivePrompt.reshape(bottomFirstRow, left, bottomRows, cols)
    self.interactiveQuit.reshape(bottomFirstRow, left, bottomRows, cols)
    if self.showMessageLine:
      self.messageLine.reshape(bottomFirstRow, left, bottomRows, cols)
    self.interactiveFind.reshape(bottomFirstRow, left, bottomRows, cols)
    if 1:
      self.interactiveGoto.reshape(bottomFirstRow,
          left, bottomRows, cols)
    if self.showFooter and rows > 0:
      self.statusLine.reshape(
          bottomFirstRow - self.statusLineCount, left, self.statusLineCount,
          cols)
      rows -= self.statusLineCount
    if self.showLineNumbers and cols > lineNumbersCols:
      self.lineNumberColumn.reshape(top, left, rows, lineNumbersCols)
      cols -= lineNumbersCols
      left += lineNumbersCols
    if self.showRightColumn and cols > 0:
      self.rightColumn.reshape(top, left + cols - 1, rows, 1)
      cols -= 1
    Window.reshape(self, top, left, rows, cols)

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
    limit = min(maxRow, len(self.textBuffer.lines) - self.scrollRow)
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
    self.layout()
    if self.showMessageLine:
      self.messageLine.bringToFront()
    Window.focus(self)

  def nextFocusableWindow(self, start, reverse=False):
    # Keep the tab focus in the child branch. (The child view will call this,
    # tell the child there is nothing to tab to up here).
    return None

  def render(self):
    self.topInfo.onChange()
    self.drawLogoCorner()
    self.drawRightEdge()
    Window.render(self)

  def reshape(self, top, left, rows, cols):
    """Change self and sub-windows to fit within the given rectangle."""
    app.log.detail(top, left, rows, cols)
    Window.reshape(self, top, left, rows, cols)
    self.outerShape = (top, left, rows, cols)
    self.layout()

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
      historyScroll = self.textBuffer.fileHistory.get('scroll')
      if historyScroll is not None:
        self.scrollRow, self.scrollCol = historyScroll
      else:
        self.textBuffer.scrollToOptimalScrollPosition()

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

  def toggleShowTips(self):
    self.showTips = not self.showTips
    self.statusLineCount = 8 if self.showTips else 1
    self.layout()
    app.prefs.save('status', 'showTips', self.showTips)

  def unfocus(self):
    if self.showMessageLine:
      self.messageLine.detach()
    Window.unfocus(self)


class OptionsSelectionWindow(ViewWindow):
  """Mutex window."""
  def __init__(self, parent):
    if app.config.strict_debug:
      assert parent is not None
    ViewWindow.__init__(self, parent)
    self.color = app.color.get('top_info')

  def reshape(self, top, left, rows, cols):
    ViewWindow.reshape(self, top, left, rows, cols)
    self.layoutHorizontally(self.zOrder)

  def childSelected(self, selectedChild):
    app.log.info(self.zOrder)
    for child in self.zOrder:
      if child is not selectedChild:
        child.deselect()

  def render(self):
    self.blank(self.color)
    ViewWindow.render(self)


class OptionsTrinaryStateWindow(Window):
  def __init__(self, parent, label, prefCategory, prefName):
    if app.config.strict_debug:
      assert type(label) == str
    Window.__init__(self, parent)
    # TODO(dschuyler): Creating a text buffer is rather heavy for a toggle
    # control. This should get some optimization.
    self.setTextBuffer(app.text_buffer.TextBuffer())
    self.setController(app.cu_editor.ToggleController)
    self.setParent(parent)
    self.name = label
    self.prefCategory = prefCategory
    self.prefName = prefName
    self.color = app.color.get('keyword')
    self.focusColor = app.color.get('selected')

  def focus(self):
    Window.focus(self)

  def setUp(self, toggleOn, toggleOff, toggleUndefined, width=None):
    if app.config.strict_debug:
      assert type(toggleOn) == str
      assert type(toggleOff) == str
      assert type(toggleUndefined) == str
      assert width is None or type(width) == int
    self.toggleOn = toggleOn
    self.toggleOff = toggleOff
    self.toggleUndefined = toggleUndefined
    longest = max(len(toggleOn), len(toggleOff), len(toggleUndefined))
    self.width = width if width is not None else longest
    self.updateLabel()

  def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
    self.controller.toggleValue()

  def onPrefChanged(self, category, name):
    Window.onPrefChanged(self, category, name)
    if category != self.prefCategory or name != self.prefName:
      return
    self.updateLabel()

  def updateLabel(self):
    pref = app.prefs.prefs[self.prefCategory][self.prefName]
    if pref is None:
      label = self.toggleUndefined
    else:
      label = self.toggleOn if pref else self.toggleOff
    self.label = '%*s' % (self.width, label)

  def preferredSize(self, rowLimit, colLimit):
    return min(rowLimit, 1), min(colLimit, abs(self.width))

  def render(self):
    Window.render(self)
    if self.rows <= 0:
      return
    self.writeLineRow = 0
    color = self.focusColor if self.hasFocus else self.color
    self.writeLine(self.label[:self.cols], color)


class OptionsToggle(OptionsTrinaryStateWindow):
  def __init__(self, parent, label, prefCategory, prefName, width=None):
    if app.config.strict_debug:
      assert type(label) == str
      assert type(prefCategory) == str
      assert type(prefName) == str
    OptionsTrinaryStateWindow.__init__(self, parent, label, prefCategory,
        prefName)
    if 0:
      toggleOn = '[x]' + name
      toggleOff = '[ ]' + name
    if 0:
      toggleOn = unichr(0x2612) + ' ' + control['name']
      toggleOff = unichr(0x2610) + ' ' + control['name']
    if 0:
      toggleOn = '[+' + control['name'] + ']'
      toggleOff = '[-' + control['name'] + ']'
    OptionsTrinaryStateWindow.setUp(self, '[x]' + label, '[ ]' + label,
        '[-]' + label, width)


class RowWindow(ViewWindow):
  def __init__(self, host, separator):
    if app.config.strict_debug:
      assert(host)
    ViewWindow.__init__(self, host)
    self.color = app.color.get('keyword')
    self.separator = separator

  def preferredSize(self, rowLimit, colLimit):
    return min(rowLimit, 1), colLimit

  def render(self):
    self.blank(self.color)
    ViewWindow.render(self)

  def reshape(self, top, left, rows, cols):
    ViewWindow.reshape(self, top, left, rows, cols)
    #app.log.info(top, left, rows, cols, self)
    self.layoutHorizontally(self.zOrder, self.separator)


class OptionsRow(ViewWindow):
  class ControlElement:
    def __init__(self, type, name, reference, width=None, sep=" "):
      self.type = type
      self.name = name
      self.reference = reference
      self.width = width if width is not None else len(name)
      self.sep = sep

  def __init__(self, host):
    if app.config.strict_debug:
      assert(host)
    ViewWindow.__init__(self, host)
    self.host = host
    self.color = app.color.get('top_info')
    self.controlList = []
    self.group = None

  def addElement(self, draw, kind, name, reference, width, sep,
      extraWidth=0):
    if app.config.strict_debug:
      assert type(name) == str
      assert type(sep) == str
      assert type(width) in [type(None), int]
      assert type(extraWidth) == int
      if reference is not None:
        assert type(reference) == dict
        assert name in reference
    if self.group is not None:
      self.group.append(len(self.controlList))
    element = {
      'dict': reference,
      'draw': draw,
      'name': name,
      'sep': sep,
      'type': kind,
      'width': width if width is not None else len(name) + extraWidth
    }
    self.controlList.append(element)
    return element

  def addLabel(self, name, width=None, sep=" "):
    def draw(control):
      return control['name']
    return self.addElement(draw, 'label', name, None, width, sep)

  def addSortHeader(self, name, reference, width=None, sep=" |"):
    def draw(control):
      decoration = 'v' if control['dict'][control['name']] else '^'
      if control['dict'][control['name']] is None:
        decoration = '-'
      if control['width'] < 0:
        return '%s %s' % (control['name'], decoration)
      return '%s %s' % (decoration, control['name'])
    self.addElement(draw, 'sort', name, reference, width, sep, len(' v'))

  def addSelection(self, name, reference, width=None, sep="  "):
    if app.config.strict_debug:
      assert type(name) == str
    if 1:
      toggleOn = '(*)' + name
      toggleOff = '( )' + name
    def draw(control):
      return toggleOn if control['dict'][control['name']] else toggleOff
    group = []
    width = max(width, min(len(toggleOn), len(toggleOff)))
    self.addElement(draw, 'selection', name, reference, width, sep,
        len('(*)'))

  def removeThis_addToggle(self, name, reference, width=None, sep="  "):
    if app.config.strict_debug:
      assert type(name) == str
    if 1:
      toggleOn = '[x]' + name
      toggleOff = '[ ]' + name
    if 0:
      toggleOn = unichr(0x2612) + ' ' + control['name']
      toggleOff = unichr(0x2610) + ' ' + control['name']
    if 0:
      toggleOn = '[+' + control['name'] + ']'
      toggleOff = '[-' + control['name'] + ']'
    def draw(control):
      return toggleOn if control['dict'][control['name']] else toggleOff
    width = max(width, min(len(toggleOn), len(toggleOff)))
    self.addElement(draw, 'toggle', name, reference, width, sep, len('[-]'))

  def beginGroup(self):
    """Like a radio group, or column sort headers."""
    self.group = []

  def endGroup(self):
    """Like a radio group, or column sort headers."""
    pass

  def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
    row = self.scrollRow + paneRow
    col = self.scrollCol + paneCol
    offset = 0
    for index, control in enumerate(self.controlList):
      width = abs(control['width'])
      if offset <= col < offset + width:
        if control['type'] == 'selection':
          name = control['name']
          for element in self.group:
            elementName = self.controlList[element]['name']
            self.controlList[element]['dict'][elementName] = False
          control['dict'][name] = True
          self.host.controller.optionChanged(name, control['dict'][name])
          break
        if control['type'] == 'sort':
          name = control['name']
          newValue = not control['dict'][name]
          if index in self.group:
            for element in self.group:
              elementName = self.controlList[element]['name']
              self.controlList[element]['dict'][elementName] = None
          control['dict'][name] = newValue
          self.host.controller.optionChanged(name, control['dict'][name])
          break
        if control['type'] == 'toggle':
          name = control['name']
          control['dict'][name] = not control['dict'][name]
          self.host.controller.optionChanged(name, control['dict'][name])
          break
      offset += width + len(control['sep'])

  def preferredSize(self, rowLimit, colLimit):
    return min(rowLimit, 1), colLimit

  def render(self):
    if self.rows <= 0:
      return
    line = ''
    for control in self.controlList:
      label = control['draw'](control)
      line += '%*s%s' % (control['width'], label, control['sep'])
      if len(line) >= self.cols:
        break
    self.writeLineRow = 0
    self.writeLine(line[:self.cols], self.color)


class PopupWindow(Window):
  def __init__(self, host):
    if app.config.strict_debug:
      assert(host)
    Window.__init__(self, host)
    self.host = host
    self.controller = app.cu_editor.PopupController(self)
    self.setTextBuffer(app.text_buffer.TextBuffer())
    self.longestLineLength = 0
    self.__message = []
    self.showOptions = True
    # This will be displayed and should contain the keys that respond to user
    # input. This should be updated if you change the controller's command set.
    self.options = []

  def render(self):
    """
    Display a box of text in the center of the window.
    """
    maxRows, maxCols = self.host.rows, self.host.cols
    cols = min(self.longestLineLength + 6, maxCols)
    rows = min(len(self.__message) + 4, maxRows)
    self.resizeTo(rows, cols)
    self.moveTo(maxRows // 2 - rows // 2, maxCols // 2 - cols // 2)
    color = app.color.get('popup_window')
    for row in range(rows):
      if row == rows - 2 and self.showOptions:
        message = '/'.join(self.options)
      elif row == 0 or row >= rows - 3:
        self.addStr(row, 0, ' ' * cols, color)
        continue
      else:
        message = self.__message[row - 1]
      lineLength = len(message)
      spacing1 = (cols - lineLength) // 2
      spacing2 = cols - lineLength - spacing1
      self.addStr(row, 0, ' ' * spacing1 + message + ' ' * spacing2, color)

  def setMessage(self, message):
    """
    Sets the Popup window's message to the given message.
    message (str): A string that you want to display.
    Returns:
      None.
    """
    self.__message = message.split("\n")
    self.longestLineLength = max([len(line) for line in self.__message])

  def setOptionsToDisplay(self, options):
    """
    This function is used to change the options that are displayed in the
    popup window. They will be separated by a '/' character when displayed.

    Args:
      options (list): A list of possible keys which the user can press and
                      should be responded to by the controller.
    """
    self.options = options

  def setTextBuffer(self, textBuffer):
    Window.setTextBuffer(self, textBuffer)
    self.controller.setTextBuffer(textBuffer)

  def unfocus(self):
    self.detach()
    Window.unfocus(self)


class PaletteWindow(Window):
  """A window with example foreground and background text colors."""
  def __init__(self, prg):
    Window.__init__(self, prg)
    self.prg = prg
    self.resizeTo(16, 16 * 5)
    self.moveTo(8, 8)
    self.controller = app.cu_editor.PaletteDialogController(self)
    self.setTextBuffer(app.text_buffer.TextBuffer())

  def render(self):
    width = 16
    rows = 16
    for i in range(width):
      for k in range(rows):
        self.addStr(k, i * 5, ' %3d ' % (i + k * width,),
            app.color.get(i + k * width))

  def setTextBuffer(self, textBuffer):
    Window.setTextBuffer(self, textBuffer)
    self.controller.setTextBuffer(textBuffer)

  def unfocus(self):
    self.detach()
    Window.unfocus(self)


class SortableHeaderWindow(OptionsTrinaryStateWindow):
  def __init__(self, parent, label, prefCategory, prefName, width=None):
    if app.config.strict_debug:
      assert type(label) == str
      assert type(prefCategory) == str
      assert type(prefName) == str
    OptionsTrinaryStateWindow.__init__(self, parent, label, prefCategory,
        prefName)
    self.color = app.color.get('top_info')
    def draw(label, decoration, width):
      if width < 0:
        x = '%s %s' % (label, decoration)
      else:
        x = '%s %s' % (decoration, label)
      return '%*s' % (width, x)
    OptionsTrinaryStateWindow.setUp(self,
        draw(label, 'v', width),
        draw(label, '^', width),
        draw(label, '-', width))

  def deselect(self):
    self.controller.clearValue()

  def mouseClick(self, paneRow, paneCol, shift, ctrl, alt):
    self.parent.childSelected(self)
    self.controller.toggleValue()
