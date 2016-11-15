#!/usr/bin/python
# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import sys
import traceback


screenLog = ["--- screen log ---"]
fullLog = ["--- begin log ---"]
shouldWritePrintLog = False

def getLines():
  global screenLog
  return screenLog

def parseLines(*args):
  if not len(args):
    return [""]
  msg = str(args[0])
  prior = msg
  for i in args[1:]:
    if not len(prior) or prior[-1] != '\n':
      msg += ' '
    prior = str(i)
    msg += prior
  return msg.split("\n")

def info(*args):
  global screenLog
  global fullLog
  lines = parseLines(*args)
  screenLog += lines
  fullLog += lines

def detail(*args):
  global screenLog
  global fullLog
  lines = parseLines(*args)
  fullLog += lines

def error(*args):
  global screenLog
  global fullLog
  lines = parseLines(*args)
  fullLog += lines

def wrapper(func):
  try:
    try:
      func()
    except Exception, e:
      errorType, value, tb = sys.exc_info()
      out = traceback.format_exception(errorType, value, tb)
      for i in out:
        error(i[:-1])
  finally:
    flush()

def flush():
  global fullLog
  if shouldWritePrintLog:
    print "\n".join(fullLog)
