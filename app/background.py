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


class BackgroundThread:
  def get(self):
    return self.fromBackground.get()

  def hasMessage(self):
    return not self.fromBackground.empty()

  def put(self, data):
    self.toBackground.put(data)


def background(input, output):
  block = True
  while True:
    try:
      program, message = input.get(block)
      program.executeCommandList(message)
    except Queue.Empty, e:
      pass
    program.render()
    output.put(app.render.frame.grabFrame())
    os.kill(0, signal.SIGALRM)
    tb = program.focusedWindow.textBuffer
    if not tb.parser:
      block = True
      continue
    block = len(tb.parser.rows) >= len(tb.lines)
    if not block:
      tb.parseGrammars()
    #while self.doWork() and input.empty():
    #os.kill(0, signal.SIGHUP)
    #os.kill(0, signal.SIGALRM)

def startupBackground():
  toBackground = Queue.Queue()
  fromBackground = Queue.Queue()
  bg = threading.Thread(
      target=background, args=(toBackground, fromBackground))
  bg.setName('ci_edit_bg')
  bg.setDaemon(True)
  bg.start()
  result = BackgroundThread()
  result.toBackground = toBackground
  result.fromBackground = fromBackground
  return result
