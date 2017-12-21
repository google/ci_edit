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

import app.log
import app.history
import app.text_buffer
import io
import os
import sys

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
    for fileBuffer in self.buffers:
      if fileBuffer.isDirty():
        return fileBuffer
    return None

  def newTextBuffer(self):
    textBuffer = app.text_buffer.TextBuffer()
    textBuffer.lines = [unicode("")]
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

  def topBuffer(self):
    app.log.info()
    self.debugLog()
    if len(self.buffers):
      return self.buffers[0]
    return None

  def getValidTextBuffer(self, textBuffer):
    """If |textBuffer| is a managed buffer return it, otherwise create a new
    buffer. Primarily used to determine if a held reference to a textBuffer is
    still valid."""
    if textBuffer in self.buffers:
      del self.buffers[self.buffers.index(textBuffer)]
      self.buffers.append(textBuffer)
      return textBuffer
    textBuffer = app.text_buffer.TextBuffer()
    self.buffers.append(textBuffer)
    return textBuffer

  def loadTextBuffer(self, relPath, view):
    fullPath = os.path.abspath(os.path.expanduser(os.path.expandvars(relPath)))
    app.log.info(fullPath)
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
      textBuffer.view = view
      self.buffers.append(textBuffer)
    if 0:
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
    try:
      with io.open(newFd, "r") as fileInput:
        textBuffer.fileFilter(fileInput.read())
    except Exception as e:
      app.log.exception(e)
    app.log.info('finished reading from stdin')
    return textBuffer

  def untrackBuffer_(self, fileBuffer):
    app.log.debug(fileBuffer.fullPath)
    self.buffers.remove(fileBuffer)

  def renameBuffer(self, fileBuffer, fullPath):
    """
    For now, when you change the path of a fileBuffer, you should also be
    updating its fileStat object, so that it tracks the new file as well.
    """
    # TODO(dschuyler): this can be phased out. It was from a time when the
    # buffer manager needed to know if a path changed.
    fileBuffer.fullPath = fullPath

  def fileClose(self, path):
    pass


buffers = BufferManager()
