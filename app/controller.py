# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

"""Manager for key bindings."""

import curses
import curses.ascii


class Controller:
  """A Controller is a keyboard mapping from keyboard/mouse events to editor
  commands."""
  def __init__(self, prg, host, name):
    self.prg = prg
    self.host = host
    self.commandDefault = None
    self.commandSet = None
    self.name = name

  def changeToInputWindow(self, ignored=1):
    self.prg.changeTo = self.prg.inputWindow

  def commandLoop(self):
    while not self.prg.exiting and not self.prg.changeTo:
      self.onChange()
      self.prg.refresh()
      ch = self.host.cursorWindow.getch()
      self.prg.ch = ch
      self.doCommand(ch)

  def doCommand(self, ch):
      cmd = self.commandSet.get(ch)
      if cmd:
        cmd()
      else:
        self.prg.log('commandDefault', repr(self.commandDefault))
        self.commandDefault(ch)

  def focus(self):
    pass

  def onChange(self):
    pass

  def saveEventChangeToInputWindow(self, ignored=1):
    self.prg.log('ungetch')
    curses.ungetch(self.prg.ch)
    self.prg.changeTo = self.prg.inputWindow

  def unfocus(self):
    pass


class MainController:
  """The different keyboard mappings are different controllers. This class
  manages a collection of keyboard mappings and allows the user to switch
  between them."""
  def __init__(self, prg, host):
    self.prg = prg
    self.host = host
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
      cmd = self.commandSet.get(ch)
      if cmd:
        cmd()
      else:
        self.prg.log('commandDefault', repr(self.commandDefault))
        self.commandDefault(ch)

  def commandLoop(self):
    self.prg.log('MainController.commandLoop')
    while not self.prg.exiting and not self.prg.changeTo:
      self.controller.onChange()
      self.prg.refresh()
      ch = self.host.cursorWindow.getch()
      self.prg.ch = ch
      self.doCommand(ch)
      if 0:
        self.commandDefault = self.controller.commandDefault
        commandSet = self.controller.commandSet.copy()
        commandSet.update({
          curses.KEY_F2: self.nextController,
        })
        self.commandSet = commandSet

  def focus(self):
    self.prg.log('MainController.focus')
    self.controller.focus()
    self.commandDefault = self.controller.commandDefault
    commandSet = self.controller.commandSet.copy()
    commandSet.update({
      curses.KEY_F2: self.nextController,
    })
    self.commandSet = commandSet
    self.commandLoop()

  def nextController(self):
    return
    if self.controller is self.controllers['cuaPlus']:
      self.prg.log('MainController.nextController cua')
      self.controller = self.controllers['cua']
    elif self.controller is self.controllers['cua']:
      self.prg.log('MainController.nextController emacs')
      self.controller = self.controllers['emacs']
    elif self.controller is self.controllers['emacs']:
      self.prg.log('MainController.nextController vim')
      self.controller = self.controllers['vim']
    else:
      self.prg.log('MainController.nextController cua')
      self.controller = self.controllers['cua']
    self.controller.setTextBuffer(self.textBuffer)
    self.focus()

  def setTextBuffer(self, textBuffer):
    self.prg.log('MainController.setTextBuffer', self.controller)
    self.textBuffer = textBuffer
    self.controller.setTextBuffer(textBuffer)

  def unfocus(self):
    self.controller.unfocus()

