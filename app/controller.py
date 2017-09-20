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

"""Manager for key bindings."""

import app.log
import curses
import curses.ascii
import app.curses_util


class Controller:
  """A Controller is a keyboard mapping from keyboard/mouse events to editor
  commands."""
  def __init__(self, host, name):
    self.host = host
    self.commandDefault = None
    self.commandSet = None
    self.textBuffer = None
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

  def doCommand(self, ch, meta):
    # Check the commandSet for the input with both its string and integer
    # representation.
    self.savedCh = ch
    cmd = (self.commandSet.get(ch) or
          self.commandSet.get(app.curses_util.cursesKeyName(ch)))
    if cmd:
      cmd()
    else:
      self.commandDefault(ch, meta)

  def focus(self):
    app.log.info('base controller focus()')
    pass

  def confirmationPromptFinish(self, ignore=1):
    self.host.userIntent = 'edit'
    self.changeToHostWindow()

  def closeHostFile(self):
    """Close the current file and switch to another or create an empty file."""
    app.buffer_manager.buffers.closeTextBuffer(self.host.textBuffer)
    self.host.userIntent = 'edit'
    tb = app.buffer_manager.buffers.getUnsavedBuffer()
    if not tb:
      tb = app.buffer_manager.buffers.nextBuffer()
      if not tb:
        tb = app.buffer_manager.buffers.newTextBuffer()
    self.host.setTextBuffer(tb)

  def closeFile(self):
    app.log.info()
    self.closeHostFile()
    #app.buffer_manager.buffers.closeTextBuffer(self.host.textBuffer)
    #self.host.setTextBuffer(app.buffer_manager.buffers.newTextBuffer())
    self.confirmationPromptFinish()

  def closeOrConfirmClose(self):
    """If the file is clean, close it. If it is dirty, prompt the user
        about whether to lose unsaved changes."""
    tb = self.host.textBuffer
    if not tb.isDirty():
      self.closeHostFile()
      return
    if self.host.userIntent == 'edit':
      self.host.userIntent = 'close'
    self.changeToConfirmClose()

  def overwriteHostFile(self):
    """Close the current file and switch to another or create an empty file."""
    self.host.textBuffer.fileWrite()
    if self.host.userIntent == 'quit':
      self.quitOrSwitchToConfirmQuit()
      return
    if self.host.userIntent == 'close':
      self.closeHostFile()
    self.changeToHostWindow()

  def writeOrConfirmOverwrite(self):
    """Ask whether the file should be overwritten."""
    app.log.debug()
    tb = self.host.textBuffer
    if not tb.isSafeToWrite():
      self.changeToConfirmOverwrite()
      return
    tb.fileWrite()
    # TODO(dschuyler): Is there a deeper issue here that necessitates saving
    # the message? Does this only need to wrap the changeToHostWindow()?
    saveMessage = tb.message  # Store the save message so it is not overwritten.
    if self.host.userIntent == 'quit':
      self.quitOrSwitchToConfirmQuit()
      return
    if self.host.userIntent == 'close':
      self.closeHostFile()
    self.changeToHostWindow()
    tb.message = saveMessage  # Restore the save message.

  def quitOrSwitchToConfirmQuit(self):
    app.log.debug()
    tb = self.host.textBuffer
    self.host.userIntent = 'quit'
    if tb.isDirty():
      self.changeToConfirmQuit()
      return
    tb = app.buffer_manager.buffers.getUnsavedBuffer()
    if tb:
      self.host.setTextBuffer(tb)
      self.changeToConfirmQuit()
      return
    app.buffer_manager.buffers.debugLog()
    self.host.quitNow()

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

  def setTextBuffer(self, textBuffer):
    app.log.info(textBuffer)
    self.textBuffer = textBuffer

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

  def doCommand(self, ch, meta):
    self.controller.doCommand(ch, meta)

  def focus(self):
    app.log.info('MainController.focus')
    self.controller.focus()
    if 0:
      self.commandDefault = self.controller.commandDefault
      commandSet = self.controller.commandSet.copy()
      commandSet.update({
        app.curses_util.KEY_F2: self.nextController,
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

