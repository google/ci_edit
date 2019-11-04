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

# For Python 2to3 support.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
try:
    import Queue as queue
except ImportError:
    import queue
import signal
import sys
import threading
import time
import traceback

import app.profile
import app.render


class BackgroundThread(threading.Thread):

    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self.toBackground = None
        self.fromBackground = None

    def get(self):
        return self.fromBackground.get()

    def hasMessage(self):
        # This thread yield (time.sleep(0)) dramatically improves Python3
        # performance. Without this line empty() will be called far too often.
        time.sleep(0)
        return not self.fromBackground.empty()

    def hasUserEvent(self):
        time.sleep(0)  # See note in hasMessage().
        return not self.toBackground.empty()

    def put(self, data):
        self.toBackground.put(data)


def background(inputQueue, outputQueue):
    cmdCount = 0
    block = True
    pid = os.getpid()
    signalNumber = signal.SIGUSR1
    while True:
        try:
            try:
                program, message = inputQueue.get(block)
                #profile = app.profile.beginPythonProfile()
                if message == 'quit':
                    app.log.info('bg received quit message')
                    return
                program.executeCommandList(message)
                block = program.shortTimeSlice()
                program.render()
                # debugging only: program.showWindowHierarchy()
                cmdCount += len(message)
                program.program.backgroundFrame.setCmdCount(cmdCount)
                outputQueue.put(program.program.backgroundFrame.grabFrame())
                os.kill(pid, signalNumber)
                #app.profile.endPythonProfile(profile)
                time.sleep(0)  # See note in hasMessage().
                if block or not inputQueue.empty():
                    continue
            except queue.Empty:
                pass
            block = program.longTimeSlice()
            if block:
                program.render()
                program.program.backgroundFrame.setCmdCount(cmdCount)
                outputQueue.put(program.program.backgroundFrame.grabFrame())
                os.kill(pid, signalNumber)
        except Exception as e:
            app.log.exception(e)
            app.log.error('bg thread exception', e)
            errorType, value, tracebackInfo = sys.exc_info()
            out = traceback.format_exception(errorType, value, tracebackInfo)
            outputQueue.put(('exception', out))
            os.kill(pid, signalNumber)
            while True:
                program, message = inputQueue.get()
                if message == 'quit':
                    app.log.info('bg received quit message')
                    return


def startupBackground():
    toBackground = queue.Queue()
    fromBackground = queue.Queue()
    bg = BackgroundThread(
        target=background, args=(toBackground, fromBackground))
    bg.setName('ci_edit_bg')
    bg.setDaemon(True)
    bg.start()
    bg.toBackground = toBackground
    bg.fromBackground = fromBackground
    return bg
