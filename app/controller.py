# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

"""Manager for key bindings."""

import app.log
import curses
import curses.ascii


class Controller:
  """A Controller is a keyboard mapping from keyboard/mouse events to editor
  commands."""
  def __init__(self, host, name):
    self.host = host
    self.commandDefault = None
    self.commandSet = None
    self.name = name

  def changeToHostWindow(self, ignored=1):
    self.host.changeFocusTo(self.host)

  def changeToFileOpen(self):
    self.host.changeFocusTo(self.host.interactiveOpen)

  def changeToFind(self):
    self.host.changeFocusTo(self.host.interactiveFind)

  def changeToFindPrior(self):
    curses.ungetch(self.savedCh)
    self.host.changeFocusTo(self.host.interactiveFind)

  def changeToGoto(self):
    self.host.changeFocusTo(self.host.interactiveGoto)

  def changeToQuit(self):
    app.log.debug()
    self.host.changeFocusTo(self.host.interactiveQuit)

  def changeToSaveAs(self):
    app.log.debug()
    self.host.changeFocusTo(self.host.interactiveSaveAs)

  def doCommand(self, ch):
    self.savedCh = ch
    cmd = self.commandSet.get(ch)
    if cmd:
      cmd()
    else:
      self.commandDefault(ch)

  def focus(self):
    app.log.info('base controller focus()')
    pass

  def maybeChangeToQuit(self):
    app.log.debug()
    tb = self.host.textBuffer
    app.history.set(['files', tb.fullPath, 'cursor'],
        (tb.cursorRow, tb.cursorCol))
    if not tb.isDirty():
      self.host.quitNow()
    self.host.changeFocusTo(self.host.interactiveQuit)

  def maybeChangeToSaveAs(self):
    app.log.debug()
    tb = self.host.textBuffer
    if tb.file:
      tb.fileWrite()
      return
    self.changeToSaveAs()

  def onChange(self):
    pass

  def saveDocument(self):
    app.log.info('saveDocument', self.document)
    if self.document and self.document.textBuffer:
      self.document.textBuffer.fileWrite()

  def saveEventChangeToHostWindow(self, ignored=1):
    curses.ungetch(self.savedCh)
    self.host.changeFocusTo(self.host)

  def unfocus(self):
    pass


class MainController:
  """The different keyboard mappings are different controllers. This class
  manages a collection of keyboard mappings and allows the user to switch
  between them."""
  def __init__(self, host):
    #self.view = host
    self.commandDefault = None
    self.commandSet = None
    self.controllers = {}
    self.controllerList = []
    self.controller = None

  def add(self, controller):
    self.controllers[controller.name] = controller
    self.controllerList.append(controller)
    self.controller = controller

  def doCommand(self, ch):
    self.controller.doCommand(ch)

  def focus(self):
    app.log.info('MainController.focus')
    self.controller.focus()
    if 0:
      self.commandDefault = self.controller.commandDefault
      commandSet = self.controller.commandSet.copy()
      commandSet.update({
        curses.KEY_F2: self.nextController,
      })
      self.controller.commandSet = commandSet

  def onChange(self):
    self.controller.onChange()

  def nextController(self):
    app.log.info('nextController')
    return
    if self.controller is self.controllers['cuaPlus']:
      app.log.info('MainController.nextController cua')
      self.controller = self.controllers['cua']
    elif self.controller is self.controllers['cua']:
      app.log.info('MainController.nextController emacs')
      self.controller = self.controllers['emacs']
    elif self.controller is self.controllers['emacs']:
      app.log.info('MainController.nextController vim')
      self.controller = self.controllers['vim']
    else:
      app.log.info('MainController.nextController cua')
      self.controller = self.controllers['cua']
    self.controller.setTextBuffer(self.textBuffer)
    self.focus()

  def setTextBuffer(self, textBuffer):
    app.log.info('MainController.setTextBuffer', self.controller)
    self.textBuffer = textBuffer
    self.controller.setTextBuffer(textBuffer)

  def unfocus(self):
    self.controller.unfocus()

