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
    # Using a dictionary lookup for buffers accelerates finding buffers by key
    # (the file path), but that's not the common use. Maintaining an ordered
    # list turns out to be more valuable.
    self.buffers = []

  def closeTextBuffer(self, textBuffer):
    """Warning this will throw away the buffer. Please be sure the user is
        ok with this before calling."""
    self.untrackBuffer_(textBuffer)

  def getUnsavedBuffer(self):
    for buffer in self.buffers:
      if buffer.isDirty():
        return buffer
    return None

  def newTextBuffer(self):
    textBuffer = app.text_buffer.TextBuffer()
    textBuffer.lines = [""]
    textBuffer.savedAtRedoIndex = 0
    self.buffers.append(textBuffer)
    app.log.info(textBuffer)
    self.debugLog()
    return textBuffer

  def nextBuffer(self):
    app.log.info()
    self.debugLog()
    if len(self.buffers):
      return self.buffers[0]
    return None

  def recentBuffer(self):
    app.log.info()
    self.debugLog()
    if len(self.buffers) > 1:
      return self.buffers[-2]
    return None

  def topBuffer(self):
    app.log.info()
    self.debugLog()
    if len(self.buffers):
      return self.buffers[0]
    return None

  def loadTextBuffer(self, relPath):
    fullPath = os.path.abspath(os.path.expanduser(os.path.expandvars(relPath)))
    app.log.info(fullPath)
    app.history.set(['files', fullPath, 'adate'], time.time())
    textBuffer = None
    for i,tb in enumerate(self.buffers):
      if tb.fullPath == fullPath:
        textBuffer = tb
        del self.buffers[i]
        self.buffers.append(tb)
        break
    app.log.info('Searched for textBuffer', repr(textBuffer));
    if not textBuffer:
      if os.path.isdir(fullPath):
        app.log.info('Tried to open directory as a file', fullPath)
        return
      if not os.path.isfile(fullPath):
        app.log.info('creating a new file at\n ', fullPath)
      textBuffer = app.text_buffer.TextBuffer()
      self.renameBuffer(textBuffer, fullPath)
      textBuffer.fileLoad()
      self.buffers.append(textBuffer)
    self.debugLog()
    return textBuffer

  def debugLog(self):
    bufferList = ''
    for i in self.buffers:
      bufferList += '\n  '+repr(i.fullPath)
      bufferList += '\n    '+repr(i)
      bufferList += '\n    dirty: '+str(i.isDirty())
    app.log.info('BufferManager'+bufferList)

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

  def untrackBuffer_(self, buffer):
    app.log.debug(buffer.fullPath)
    self.buffers.remove(buffer)

  def renameBuffer(self, buffer, fullPath):
    # TODO(dschuyler): this can be phased out. It was from a time when the
    # buffer manager needed to know if a path changed.
    buffer.fullPath = fullPath

  def fileClose(self, path):
    pass


buffers = BufferManager()
