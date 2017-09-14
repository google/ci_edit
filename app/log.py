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

import inspect
import os
import sys
import traceback


screenLog = ["--- screen log ---"]
fullLog = ["--- begin log ---"]
enabledChannels = {'meta': True, 'mouse': True, 'startup': True}
shouldWritePrintLog = False

if os.getenv('CI_EDIT_USE_FAKE_CURSES'):
  enabledChannels = {
    'error': True, 'info': True, 'meta': True, 'mouse': True, 'startup': True
  }
  shouldWritePrintLog = True

def getLines():
  global screenLog
  return screenLog

def parseLines(frame, channel, *args):
  if not len(args):
    args = [""]
  msg = str(args[0])
  if 1:
    msg = "%s %s %s %s: %s"%(channel, os.path.split(frame[1])[1],
        frame[2], frame[3], msg)
  prior = msg
  for i in args[1:]:
    if not len(prior) or prior[-1] != '\n':
      msg += ' '
    prior = str(i)
    msg += prior
  return msg.split("\n")

def channelEnable(channel, isEnabled):
  global enabledChannels, fullLog, shouldWritePrintLog
  fullLog += ["%10s %10s: %s %r" % ('logging', 'channelEnable', channel,
      isEnabled)]
  if isEnabled:
    enabledChannels[channel] = isEnabled
    shouldWritePrintLog = True
  else:
    enabledChannels.pop(channel, None)

def channel(channel, *args):
  global enabledChannels, fullLog, screenLog
  if channel in enabledChannels:
    lines = parseLines(inspect.stack()[2], channel, *args)
    screenLog += lines
    fullLog += lines

def caller(*args):
  global fullLog, screenLog
  caller = inspect.stack()[2]
  msg = ("%s %s %s" % (
      os.path.split(caller[1])[1], caller[2], caller[3]),) + args
  lines = parseLines(inspect.stack()[1], "caller", *msg)
  screenLog += lines
  fullLog += lines

def exception(e):
  error(e)
  errorType, value, tracebackInfo = sys.exc_info()
  out = traceback.format_exception(errorType, value, tracebackInfo)
  for i in out:
    error(i[:-1])


def stack():
  global fullLog, screenLog
  stack = inspect.stack()[1:]
  stack.reverse()
  for i,frame in enumerate(stack):
    line = ["stack %2d %14s %4s %s" % (i, os.path.split(frame[1])[1],
        frame[2], frame[3])]
    screenLog += line
    fullLog += line

def info(*args):
  channel('info', *args)

def meta(*args):
  """Log information related to logging."""
  channel('meta', *args)

def mouse(*args):
  channel('mouse', *args)

def parser(*args):
  channel('parser', *args)

def startup(*args):
  channel('startup', *args)

def debug(*args):
  global enabledChannels, fullLog, screenLog
  if 'debug' in enabledChannels:
    lines = parseLines(inspect.stack()[1], 'debug_@@@', *args)
    screenLog += lines
    fullLog += lines

def detail(*args):
  global enabledChannels, fullLog
  if 'detail' in enabledChannels:
    lines = parseLines(inspect.stack()[1], 'detail', *args)
    fullLog += lines

def error(*args):
  global fullLog
  lines = parseLines(inspect.stack()[1], 'error', *args)
  fullLog += lines

def wrapper(function, shouldWrite=True):
  global shouldWritePrintLog
  shouldWritePrintLog = shouldWrite
  r = -1
  try:
    try:
      r = function()
    except BaseException, e:
      shouldWritePrintLog = True
      errorType, value, tracebackInfo = sys.exc_info()
      out = traceback.format_exception(errorType, value, tracebackInfo)
      for i in out:
        error(i[:-1])
  finally:
    flush()
  return r

def writeToFile(path):
  fullPath = os.path.expanduser(os.path.expandvars(path))
  with open(fullPath, 'w+') as out:
    out.write("\n".join(fullLog)+"\n")

def flush():
  global fullLog
  if shouldWritePrintLog:
    print "\n".join(fullLog)
