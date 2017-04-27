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

  def changeToConfirmClose(self):
    self.host.changeFocusTo(self.host.confirmClose)

  def changeToConfirmOverwrite(self):
    self.host.changeFocusTo(self.host.confirmOverwrite)

  def changeToConfirmQuit(self):
    self.host.changeFocusTo(self.host.interactiveQuit)

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

  def changeToPrediction(self):
    self.host.changeFocusTo(self.host.interactivePrediction)

  def changeToPrompt(self):
    self.host.changeFocusTo(self.host.interactivePrompt)

  def changeToQuit(self):
    self.host.changeFocusTo(self.host.interactiveQuit)

  def changeToSaveAs(self):
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

  def closeHostFile(self):
    """Close the current file and switch to another or create an empty file."""
    app.buffer_manager.buffers.closeTextBuffer(self.host.textBuffer)
    tb = app.buffer_manager.buffers.getUnsavedBuffer()
    if not tb:
      tb = app.buffer_manager.buffers.nextBuffer()
      if not tb:
        tb = app.buffer_manager.buffers.newTextBuffer()
    self.host.setTextBuffer(tb)

  def closeOrConfirmClose(self):
    """If the file is clean, close it. If it is dirty, prompt the user
        about whether to lose unsaved changes."""
    if self.host.userIntent == 'edit':
      self.host.userIntent = 'close'
    tb = self.host.textBuffer
    if not tb.isDirty():
      self.closeHostFile()
      return
    self.changeToConfirmClose()

  def overwriteHostFile(self):
    """Close the current file and switch to another or create an empty file."""
    self.host.textBuffer.fileWrite()
    if self.host.userIntent == 'quit':
      self.quitOrSwitchToConfirmQuit()
      return
    elif self.host.userIntent == 'close':
      self.host.userIntent = 'edit'
      self.closeHostFile()
    self.changeToHostWindow()

  def writeOrConfirmOverwrite(self):
    """Ask whether the file should be overwritten."""
    app.log.debug()
    tb = self.host.textBuffer
    if tb.isSafeToWrite():
      tb.fileWrite()
      if self.host.userIntent == 'quit':
        self.quitOrSwitchToConfirmQuit()
        return
      elif self.host.userIntent == 'close':
        self.host.userIntent = 'edit'
        self.closeHostFile()
      self.changeToHostWindow()
      return
    self.changeToConfirmOverwrite()

  def quitOrSwitchToConfirmQuit(self):
    app.log.debug()
    tb = self.host.textBuffer
    self.host.userIntent = 'quit'
    app.history.set(['files', tb.fullPath, 'cursor'],
        (tb.cursorRow, tb.cursorCol))
    if not tb.isDirty():
      tb = app.buffer_manager.buffers.getUnsavedBuffer()
      if not tb:
        app.buffer_manager.buffers.debugLog()
        self.host.quitNow()
        return
      self.host.setTextBuffer(tb)
    self.changeToConfirmQuit()

  def saveOrChangeToSaveAs(self):
    app.log.debug()
    tb = self.host.textBuffer
    if tb.fullPath:
      self.writeOrConfirmOverwrite()
      return
    self.changeToSaveAs()

  def onChange(self):
    pass

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

