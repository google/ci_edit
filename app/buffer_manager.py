# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.log
import app.history
import app.text_buffer
import os
import sys
import time


class BufferManager:
  """Manage a set of text buffers. Some text buffers may be hidden."""
  def __init__(self):
    self.buffers = {}

  def loadTextBuffer(self, path):
    expandedPath = os.path.abspath(os.path.expanduser(os.path.expandvars(path)))
    app.history.set(['files', expandedPath, 'adate'], time.time())
    textBuffer = self.buffers.get(path, None)
    app.log.info('X textBuffer', repr(textBuffer));
    if not textBuffer:
      app.log.info(' loadTextBuffer new')
      textBuffer = app.text_buffer.TextBuffer()
      if os.path.isfile(expandedPath):
        textBuffer.fileLoad(expandedPath)
      elif os.path.isdir(expandedPath):
        app.log.info('Tried to open directory as a file', expandedPath)
        return
      else:
        app.log.info('creating a new file at\n ', expandedPath)
        textBuffer.fileLoad(expandedPath)
    self.buffers[expandedPath] = textBuffer
    if 0:  # logging.
      for i,k in self.buffers.items():
        app.log.info('  ', i)
        app.log.info('    ', k)
        #app.log.info('    ', repr(k.lines))
        #app.log.info('    ', len(k.lines) and k.lines[0])
      app.log.info(' loadTextBuffer')
      app.log.info(expandedPath)
      app.log.info(' loadTextBuffer')
      app.log.info(repr(textBuffer))
    return textBuffer

  def readStdin(self):
    app.log.info('reading from stdin')
    # Create a new input stream for the file data.
    # Fd is short for file descriptor. os.dup and os.dup2 will duplicate file
    # descriptors.
    stdinFd = sys.stdin.fileno()
    newFd = os.dup(stdinFd)
    newStdin = open("/dev/tty")
    os.dup2(newStdin.fileno(), stdinFd)
    fileInput = os.fdopen(newFd, "r")
    # Create a text buffer to read from alternate stream.
    textBuffer = app.text_bufer.TextBuffer()
    textBuffer.lines = [""]
    textBuffer.savedAtRedoIndex = 0
    textBuffer.file = fileInput
    textBuffer.fileFilter()
    textBuffer.file.close()
    textBuffer.file = None
    app.log.info('finished reading from stdin')
    self.fullPath = None
    self.relativePath = None
    return textBuffer

  def fileClose(self, path):
    pass

