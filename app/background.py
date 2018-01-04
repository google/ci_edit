# Copyright 2017 Google Inc.
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

import app.profile
import app.render
import os
import Queue
import signal
import sys
import threading
import traceback


# The instance of the background thread.
bg = None


class BackgroundThread(threading.Thread):
  def __init__(self, *args, **keywords):
    threading.Thread.__init__(self, *args, **keywords)
    self.toBackground = None
    self.fromBackground = None

  def get(self):
    return self.fromBackground.get()

  def hasMessage(self):
    return not self.fromBackground.empty()

  def hasUserEvent(self):
    return not self.toBackground.empty()

  def put(self, data):
    self.toBackground.put(data)


def background(inputQueue, outputQueue):
  def redrawProgram(program, callerSemaphore):
    """
    Sends a SIGUSR1 signal to the current program and draws its screen.

    Args:
      program (CiProgram): an instance of the CiProgram object.

    Returns:
      None.
    """
    pid = os.getpid()
    signalNumber = signal.SIGUSR1
    program.render()
    outputQueue.put((app.render.frame.grabFrame(), callerSemaphore))
    os.kill(pid, signalNumber)

  block = True
  while True:
    try:
      try:
        program, message, callerSemaphore = inputQueue.get(block)
        #profile = app.profile.beginPythonProfile()
        if message == 'quit':
          app.log.info('bg received quit message')
          return
        elif message == 'redraw':
          app.log.info('bg received redraw message')
          assert(callerSemaphore != None)
          redrawProgram(program, callerSemaphore)
          continue
        elif message == 'popup':
          app.log.meta('bg received popup message')
          # assert(callerSemaphore != None)
          pid = os.getpid()
          signalNumber = signal.SIGUSR1
          outputQueue.put((('popup', None), callerSemaphore))
          os.kill(pid, signalNumber)
          continue
        program.executeCommandList(message)
        redrawProgram(program, callerSemaphore)
        #app.profile.endPythonProfile(profile)
        if not inputQueue.empty():
          continue
      except Queue.Empty:
        pass
      #continue
      tb = program.focusedWindow.textBuffer
      block = len(tb.parser.rows) >= len(tb.lines)
      if not block:
        program.focusedWindow.textBuffer.parseDocument()
        block = len(tb.parser.rows) >= len(tb.lines)
        if block:
          redrawProgram(program, callerSemaphore)
    except Exception as e:
      app.log.exception(e)
      app.log.error('bg thread exception', e)
      errorType, value, tracebackInfo = sys.exc_info()
      out = traceback.format_exception(errorType, value, tracebackInfo)
      outputQueue.put((('exception', out), None))
      os.kill(os.getpid(), signal.SIGUSR1)
      while True:
        program, message, callerSemaphore = inputQueue.get()
        if message == 'quit':
          app.log.info('bg received quit message')
          return

def startupBackground():
  global bg
  toBackground = Queue.Queue()
  fromBackground = Queue.Queue()
  bg = BackgroundThread(
      target=background, args=(toBackground, fromBackground))
  bg.setName('ci_edit_bg')
  bg.setDaemon(True)
  bg.start()
  bg.toBackground = toBackground
  bg.fromBackground = fromBackground
  return bg
