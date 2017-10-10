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

import app.render
import os
import Queue
import signal
import threading


class BackgroundThread(threading.Thread):
  def get(self):
    return self.fromBackground.get()

  def hasMessage(self):
    return not self.fromBackground.empty()

  def hasUserEvent(self):
    return not self.toBackground.empty()

  def put(self, data):
    self.toBackground.put(data)


def background(input, output):
  block = True
  while True:
    try:
      try:
        program, message = input.get(block)
        if message == 'quit':
          app.log.info('bg received quit message')
          return
        program.executeCommandList(message)
        program.render()
        output.put(app.render.frame.grabFrame())
        os.kill(0, signal.SIGALRM)
      except Queue.Empty, e:
        pass
      #if not input.empty():
      #  continue
      tb = program.focusedWindow.textBuffer
      if not tb.parser:
        block = True
        continue
      block = len(tb.parser.rows) >= len(tb.lines)
      if not block:
        tb.linesToData()
        tb.parser.parse(tb.data, tb.rootGrammar,
            len(tb.parser.rows),
            len(tb.lines))
        #tb.parseGrammars()
        block = len(tb.parser.rows) >= len(tb.lines)
        if block:
          program.render()
          output.put(app.render.frame.grabFrame())
          os.kill(0, signal.SIGALRM)
      #os.kill(0, signal.SIGHUP)
    except Exception, e:
      app.log.error('bg thread exception')
      app.log.exception(e)

def startupBackground():
  global bg
  toBackground = Queue.Queue()
  fromBackground = Queue.Queue()
  bg = BackgroundThread(
      target=background, args=(toBackground, fromBackground))
  bg.setName('ci_edit_bg')
  bg.start()
  bg.toBackground = toBackground
  bg.fromBackground = fromBackground
  return bg
