import app.background
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
    self.fileStats = None
    self.pollingInterval = pollingInterval
    # All necessary file info should be placed in this dictionary.
    self.fileInfo = {'isReadOnly': False,
                     'size': 0}
    self.statsLock = threading.Lock()
    self.textBuffer = None
    self.thread = self.startTracking()
    self.updateStats()

  def run(self):
    while not self.thread.shouldExit:
      # Redraw the screen if the file changed READ ONLY permissions.
      oldFileIsReadOnly = self.fileInfo['isReadOnly']
      newFileIsReadOnly = self.getUpdatedFileInfo()['isReadOnly']
      turnoverTime = 0
      if newFileIsReadOnly != oldFileIsReadOnly:
        program = self.textBuffer.view.host
        before = time.time()
        app.background.bg.put((program, [], self.thread.semaphore))
        # Wait for bg thread to finish refreshing before sleeping
        self.thread.semaphore.acquire()
        turnoverTime = time.time() - before
      time.sleep(max(self.pollingInterval - turnoverTime, 0))

  def changeMonitoredFile(self, fullPath):
    """
    Stops tracking whatever file this object was monitoring before and tracks
    the newly specified file. The self.textBuffer attribute must
    be set in order for the created thread to work properly.

    Args:
      None.

    Returns:
      None.
    """
    if self.thread:
      self.thread.shouldExit = True
    self.fullPath = fullPath
    self.updateStats()
    self.startTracking()

  def startTracking(self):
    """
    Starts tracking the file whose path is specified in self.fullPath. Sets
    self.thread to this new thread.

    Args:
      None.

    Returns:
      The thread that was created to do the tracking (FileTracker object).
    """
    if self.fullPath and app.prefs.editor['useBgThread']:
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

  def getFileInfo(self):
    """
    Returns the current fileInfo that is stored in memory.
    """
    return self.fileInfo.copy()

  def setTextBuffer(self, textBuffer):
    self.textBuffer = textBuffer
