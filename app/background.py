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
try:
    unicode
except NameError:
    unicode = str
    unichr = chr

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

import app.config
import app.profile
import app.render


class InstructionQueue(queue.Queue):

    def __init__(self, *args, **keywords):
        queue.Queue.__init__(self, *args, **keywords)

    def get(self, *args, **keywords):
        result = queue.Queue.get(self, *args, **keywords)
        if app.config.strict_debug:
            assert isinstance(result, tuple), repr(result)
            assert isinstance(result[0], unicode), repr(result[0])
        return result[0], result[1]

    def empty(self, *args, **keywords):
        # This thread yield (time.sleep(0)) dramatically improves Python3
        # performance. Without this line empty() will be called far too often.
        time.sleep(0)
        return queue.Queue.empty(self, *args, **keywords)

    def put(self, instruction, message):
        if app.config.strict_debug:
            assert isinstance(instruction, unicode), repr(instruction)
        queue.Queue.put(self, (instruction, message))


class BackgroundThread(threading.Thread):

    def __init__(self, toBackground, fromBackground, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self._toBackground = toBackground
        self._fromBackground = fromBackground

    def get(self):
        return self._fromBackground.get()

    def hasMessage(self):
        # This thread yield (time.sleep(0)) dramatically improves Python3
        # performance. Without this line empty() will be called far too often.
        time.sleep(0)
        return not self._fromBackground.empty()

    def hasUserEvent(self):
        time.sleep(0)  # See note in hasMessage().
        return not self._toBackground.empty()

    def put(self, instruction, message):
        self._toBackground.put(instruction, message)


def background(programWindow, inputQueue, outputQueue):
    cmdCount = 0
    block = True
    pid = os.getpid()
    signalNumber = signal.SIGUSR1
    while True:
        try:
            try:
                instruction, message = inputQueue.get(block)
                #profile = app.profile.beginPythonProfile()
                if instruction == u"quit":
                    app.log.info('bg received quit message')
                    return
                elif instruction == u"cmdList":
                    app.log.info(programWindow, message)
                    programWindow.executeCommandList(message)
                else:
                    assert False, instruction
                block = programWindow.shortTimeSlice()
                programWindow.render()
                # debugging only: programWindow.showWindowHierarchy()
                cmdCount += len(message)
                programWindow.program.backgroundFrame.setCmdCount(cmdCount)
                outputQueue.put(
                        u"render",
                        programWindow.program.backgroundFrame.grabFrame())
                os.kill(pid, signalNumber)
                #app.profile.endPythonProfile(profile)
                time.sleep(0)  # See note in hasMessage().
                if block or not inputQueue.empty():
                    continue
            except queue.Empty:
                pass
            block = programWindow.longTimeSlice()
            if block:
                programWindow.render()
                programWindow.program.backgroundFrame.setCmdCount(cmdCount)
                outputQueue.put(
                        u"render",
                        programWindow.program.backgroundFrame.grabFrame())
                os.kill(pid, signalNumber)
        except Exception as e:
            app.log.exception(e)
            app.log.error('bg thread exception', e)
            errorType, value, tracebackInfo = sys.exc_info()
            out = traceback.format_exception(errorType, value, tracebackInfo)
            outputQueue.put(u"exception", out)
            os.kill(pid, signalNumber)
            while True:
                instruction, message = inputQueue.get()
                if instruction == u"quit":
                    app.log.info('bg received quit message')
                    return



def startupBackground(programWindow):
    toBackground = InstructionQueue()
    fromBackground = InstructionQueue()
    bg = BackgroundThread(toBackground, fromBackground,
        target=background, args=(programWindow, toBackground, fromBackground))
    bg.setName('ci_edit_bg')
    bg.setDaemon(True)
    bg.start()
    #bg.toBackground = toBackground
    #bg.fromBackground = fromBackground
    return bg
