# Copyright 2018 Google Inc.
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

import app.background
import app.curses_util
import app.log
import app.prefs
import os
import time
import threading
import app.window

class FileTracker(threading.Thread):
  def __init__(self, *args, **keywords):
    threading.Thread.__init__(self, *args, **keywords)
    self.shouldExit = False
    self.semaphore = threading.Semaphore(0)

class FileStats:
  """
  An object to monitor the statistical information of a file. It will
  automatically update the information through polling if multithreading
  is allowed. Otherwise, you must either call updateStats() or
  getUpdatedFileInfo() to obtain the updated information from disk.
  """

  def __init__(self, fullPath='', pollingInterval=2):
    """
    Args:
      fullPath (str): The absolute path of the file you want to keep track of.
      pollingInterval (float): The frequency at which you want to poll the file.
    """
    self.fullPath = fullPath
    # The stats of the file since we last checked it. This should be
    # the most updated version of the file's stats.
    self.fileStats = None
    self.pollingInterval = pollingInterval
    # This is updated only when self.fileInfo has been fully updated. We use
    # this variable in order to not have to wait for the statsLock.
    self.currentFileInfo = {'isReadOnly': False,
                            'size': 0}
    # All necessary file info should be placed in this dictionary.
    self.fileInfo = self.currentFileInfo.copy()
    # Used to determine if file on disk has changed since the last save
    self.savedFileStat = None
    self.statsLock = threading.Lock()
    self.textBuffer = None
    self.thread = None
    self.updateStats()

  def run(self):
    while not self.thread.shouldExit:
      oldFileIsReadOnly = self.fileInfo['isReadOnly']
      program = self.textBuffer.view.host
      redraw = False
      waitOnSemaphore = False
      if program:
        if self.fileContentChangedSinceCheck() and self.__popupWindow:
          self.__popupWindow.setUpWindow(
              message="The file on disk has changed.\nReload file?",
              displayOptions=self.__popupDisplayOptions,
              controllerOptions=self.__popupControllerOptions)
          self.__popupWindow.controller.callerSemaphore = self.thread.semaphore
          app.background.bg.put((program, 'popup', self.thread.semaphore))
          self.thread.semaphore.acquire() # Wait for popup to load
          redraw = True
          waitOnSemaphore = True
        # Check if file read permissions have changed.
        newFileIsReadOnly = self.fileInfo['isReadOnly']
        if newFileIsReadOnly != oldFileIsReadOnly:
          redraw = True
      if redraw:
        # Send a redraw request.
        app.background.bg.put((program, [], self.thread.semaphore))
        self.thread.semaphore.acquire() # Wait for redraw to finish
      if waitOnSemaphore:
        self.thread.semaphore.acquire() # Wait for user to respond to popup.
      time.sleep(self.pollingInterval)

  def startTracking(self):
    """
    Starts tracking the file whose path is specified in self.fullPath. Sets
    self.thread to this new thread.

    Args:
      None.

    Returns:
      The thread that was created to do the tracking (FileTracker object).
    """
    self.thread = FileTracker(target=self.run)
    self.thread.daemon = True # Do not continue running if main program exits.
    self.thread.start()
    return self.thread

  def updateStats(self):
    """
    Update the stats of the file in memory with the stats of the file on disk.

    Args:
      None.

    Returns:
      True if the file stats were updated. False if an exception occurred and
      the file stats could not be updated.
    """
    try:
      self.statsLock.acquire()
      self.fileStats = os.stat(self.fullPath)
      self.fileInfo['isReadOnly'] = not os.access(self.fullPath, os.W_OK)
      self.fileInfo['size'] = self.fileStats.st_size
      self.currentFileInfo = self.fileInfo.copy()
      self.statsLock.release()
      return True
    except Exception as e:
      app.log.info("Exception occurred while updating file stats thread:", e)
      self.statsLock.release()
      return False

  def getUpdatedFileInfo(self):
    """
    Syncs the in-memory file information with the information on disk. It
    then returns the newly updated file information.
    """
    self.updateStats()
    self.statsLock.acquire()
    info = self.fileInfo.copy() # Shallow copy.
    self.statsLock.release()
    return info

  def getCurrentFileInfo(self):
    """
    Retrieves the current file info that we have in memory.
    """
    return self.currentFileInfo

  def setPopupWindow(self, popupWindow):
    """
    Sets the file stat's object's reference to the popup window that
    it will use to notify the user of any changes.

    Args:
      popupWindow (PopupWindow): The popup window that this object will use.

    Returns:
      None.
    """
    # The keys that the user can press to respond to the popup window.
    self.__popupControllerOptions = {
      ord('Y'): popupWindow.controller.reloadBuffer,
      ord('y'): popupWindow.controller.reloadBuffer,
      ord('N'): popupWindow.controller.changeToInputWindow,
      ord('n'): popupWindow.controller.changeToInputWindow,
      app.curses_util.KEY_ESCAPE: popupWindow.controller.changeToInputWindow,
    }
    # The options that will be displayed on the popup window.
    self.__popupDisplayOptions = ['Y', 'N']
    self.__popupWindow = popupWindow

  def setTextBuffer(self, textBuffer):
    self.textBuffer = textBuffer

  def fileChangedSinceSave(self):
    """
    Checks whether the file on disk has changed since we last opened/saved it.
    This includes checking its permission bits, modified time, metadata modified
    time, file size, and other statistics.

    Args:
      None.

    Returns:
      True if the file on disk has changed. Otherwise, False.
    """
    try:
      if (self.updateStats() and self.fileStats):
        s1 = self.fileStats
        s2 = self.savedFileStat
        app.log.info('st_ino', s1.st_ino, s2.st_ino)
        app.log.info('st_dev', s1.st_dev, s2.st_dev)
        app.log.info('st_uid', s1.st_uid, s2.st_uid)
        app.log.info('st_gid', s1.st_gid, s2.st_gid)
        app.log.info('st_size', s1.st_size, s2.st_size)
        app.log.info('st_mtime', s1.st_mtime, s2.st_mtime)
        return not (s1.st_mode == s2.st_mode and
                    s1.st_ino == s2.st_ino and
                    s1.st_dev == s2.st_dev and
                    s1.st_uid == s2.st_uid and
                    s1.st_gid == s2.st_gid and
                    s1.st_size == s2.st_size and
                    s1.st_mtime == s2.st_mtime and
                    s1.st_ctime == s2.st_ctime)
      return False
    except Exception as e:
      print(e)

  def fileContentChangedSinceCheck(self):
    """
    Checks if a file has been modified since we last checked it from disk.

    Args:
      None.

    Returns:
      True if the file has been modified. Otherwise, False.
    """
    try:
      s1 = self.fileStats
      if (self.updateStats() and self.fileStats):
        s2 = self.fileStats
        app.log.info('st_mtime', s1.st_mtime, s2.st_mtime)
        return not s1.st_mtime == s2.st_mtime
      return False
    except Exception as e:
      print(e)

  def fileContentChangedSinceSave(self):
    """
    Checks if a file has been modified since we last saved the file.

    Args:
      None.

    Returns:
      True if the file has been modified. Otherwise, False.
    """
    try:
      if (self.updateStats() and self.fileStats):
        s1 = self.fileStats
        s2 = self.savedFileStat
        app.log.info('st_mtime', s1.st_mtime, s2.st_mtime)
        return not s1.st_mtime == s2.st_mtime
      return False
    except Exception as e:
      print(e)

  def cleanup(self):
    if self.thread:
      self.thread.shouldExit = True