#!/usr/bin/python
# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import sys
import traceback


globalPrintLog = "--- begin log ---\n"
shouldWritePrintLog = False


def log(*args):
  global globalPrintLog
  if not len(args):
    globalPrintLog += "\n"
    return
  msg = str(args[0])
  prior = msg
  for i in args[1:]:
    if not len(prior) or prior[-1] != '\n':
      msg += ' '
    prior = str(i)
    msg += prior
  globalPrintLog += msg + "\n"

def wrapper(func):
  try:
    try:
      func()
    except Exception, e:
      errorType, value, tb = sys.exc_info()
      out = traceback.format_exception(errorType, value, tb)
      for i in out:
        logPrint(i[:-1])
  finally:
    global globalPrintLog
    if shouldWritePrintLog:
      print globalPrintLog

def flush():
  global globalPrintLog
  if shouldWritePrintLog:
    print globalPrintLog
