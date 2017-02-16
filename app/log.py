#!/usr/bin/python
# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import inspect
import os
import sys
import traceback


screenLog = ["--- screen log ---"]
fullLog = ["--- begin log ---"]
enabledChannels = {'startup': True}
shouldWritePrintLog = False

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

def chanEnable(channel, isEnabled):
  global enabledChannels, fullLog, shouldWritePrintLog
  fullLog += ["%10s %10s: %s %r" % ('logging', 'chanEnable', channel, isEnabled)]
  if isEnabled:
    enabledChannels[channel] = isEnabled
    shouldWritePrintLog = True
  else:
    enabledChannels.pop(channel, None)

def chan(channel, *args):
  global enabledChannels, fullLog, screenLog
  if channel in enabledChannels:
    lines = parseLines(inspect.stack()[2], channel, *args)
    screenLog += lines
    fullLog += lines

def stack():
  global enabledChannels, fullLog, screenLog
  stack = inspect.stack()[1:]
  stack.reverse()
  for i,frame in enumerate(stack):
    fullLog += ["stack %2d %14s %4s %s" % (i, os.path.split(frame[1])[1],
        frame[2], frame[3])]

def info(*args):
  chan('info', *args)

def parser(*args):
  chan('parser', *args)

def startup(*args):
  chan('startup', *args)

def debug(*args):
  global enabledChannels, fullLog, screenLog
  if 'debug' in enabledChannels:
    lines = parseLines(inspect.stack()[1], 'debug_@@@', *args)
    screenLog += lines
    fullLog += lines

def detail(*args):
  global enabledChannels, fullLog, screenLog
  if 'detail' in enabledChannels:
    lines = parseLines(inspect.stack()[1], 'detail', *args)
    fullLog += lines

def error(*args):
  global fullLog, screenLog
  lines = parseLines(inspect.stack()[1], 'error', *args)
  fullLog += lines

def wrapper(func, shouldWrite=True):
  global shouldWritePrintLog
  shouldWritePrintLog = shouldWrite
  r = -1
  try:
    try:
      r = func()
    except BaseException, e:
      shouldWritePrintLog = True
      errorType, value, tb = sys.exc_info()
      out = traceback.format_exception(errorType, value, tb)
      for i in out:
        error(i[:-1])
  finally:
    flush()
  return r

def flush():
  global fullLog
  if shouldWritePrintLog:
    print "\n".join(fullLog)
