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
    self.ramBuffers = []

  def getUnsavedBuffer(self):
    for buffer in self.buffers.values():
      if buffer.isDirty():
        return buffer
    if len(self.ramBuffers):
      return self.ramBuffers[0]
    return None

  def newTextBuffer(self):
    textBuffer = app.text_buffer.TextBuffer()
    textBuffer.lines = [""]
    textBuffer.savedAtRedoIndex = 0
    self.ramBuffers.append(textBuffer)
    return textBuffer

  def loadTextBuffer(self, relPath):
    fullPath = os.path.abspath(os.path.expanduser(os.path.expandvars(relPath)))
    app.history.set(['files', fullPath, 'adate'], time.time())
    textBuffer = self.buffers.get(fullPath, None)
    app.log.info('X textBuffer', repr(textBuffer));
    if not textBuffer:
      if os.path.isdir(fullPath):
        app.log.info('Tried to open directory as a file', fullPath)
        return
      if not os.path.isfile(fullPath):
        app.log.info('creating a new file at\n ', fullPath)
      textBuffer = app.text_buffer.TextBuffer()
      self.renameBuffer(textBuffer, fullPath)
      textBuffer.fileLoad()
    if 0:  # logging.
      for i,k in self.buffers.items():
        app.log.info('  ', i)
        app.log.info('    ', k)
        #app.log.info('    ', repr(k.lines))
        #app.log.info('    ', len(k.lines) and k.lines[0])
      app.log.info(' loadTextBuffer')
      app.log.info(fullPath)
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
    # Create a text buffer to read from alternate stream.
    textBuffer = self.newTextBuffer()
    with os.fdopen(newFd, "r") as fileInput:
      textBuffer.fileFilter(fileInput.read())
    app.log.info('finished reading from stdin')
    return textBuffer

  def renameBuffer(self, buffer, fullPath):
    try:
      index = self.ramBuffers.index(buffer)
      del self.ramBuffers[index]
    except ValueError:
      try:
        del self.buffers[buffer.fullPath]
      except KeyError:
        pass
    buffer.fullPath = fullPath
    self.buffers[fullPath] = buffer

  def fileClose(self, path):
    pass


buffers = BufferManager()
