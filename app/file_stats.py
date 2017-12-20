import os
import time
import threading
import app.log

class FileStats:
  """
  An object to monitor the statistical information of a file. To prevent
  synchronization issues, If you want to retrieve multiple attributes
  consecutively, you must acquire the FileStats object lock before accessing the
  object's stats and release it when you are are done.
  """
  def __init__(self, fullPath='', pollingInterval=2):
    """
    Args:
      fullPath (str): The absolute path of the file you want to keep track of.
      pollingInterval (float): The frequency at which you want to poll the file.
    """
    self.pollingInterval = pollingInterval
    self.fullPath = fullPath
    self.fileStats = None
    self.textBuffer = None
    self.lock = threading.Lock()
    self.isReadOnly = False
    self.threadShouldExit = False
    self.thread = self.startTracking()
    self.updateStats()

  def run(self):
    while not self.threadShouldExit:
      oldReadOnly = self.isReadOnly
      if (self.updateStats() and
          self.isReadOnly != oldReadOnly and
          self.textBuffer and
          self.textBuffer.view.textBuffer):
        # This call requires the view's textbuffer to be set.
        self.textBuffer.view.render()
      time.sleep(self.pollingInterval)

  def changeMonitoredFile(self, fullPath):
    """
    Stops tracking whatever file this object was monitoring before and tracks
    the newly specified file. The text buffer should be set in order for the
    created thread to work properly.

    Args:
      None.

    Returns:
      None.
    """
    if self.thread:
      self.threadShouldExit = True
      self.thread.join()
      self.threadShouldExit = False
    self.fullPath = fullPath
    self.thread = self.startTracking()
    self.updateStats()

  def startTracking(self):
    """
    Starts tracking the file whose path is specified in self.fullPath

    Args:
      None.

    Returns:
      The thread that was created to do the tracking.
    """
    if self.fullPath:
      thread = threading.Thread(target=self.run)
      thread.daemon = True # Do not continue running if main program exits.
      thread.start()
      return thread

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
      self.lock.acquire()
      self.fileStats = os.stat(self.fullPath)
      self.isReadOnly = not os.access(self.fullPath, os.W_OK)
      self.lock.release()
      return True
    except Exception as e:
      app.log.info("Exception occurred while updating file stats thread:", e)
      self.lock.release()
      return False

  def getFileSize(self):
    """
    Calculates the size of the monitored file.

    Args:
      None.

    Returns:
      The size of the file in bytes.
    """
    if self.fileStats:
      return self.fileStats.st_size
    else:
      return 0

  def getFileStats(self):
    return self.fileStats

  def getFullPath(self):
    return self.fullPath

  def fileIsReadOnly(self):
    return self.isReadOnly

  def fileChanged(self):
    """
    Compares the file's stats with the recorded stats we have in memory.

    Args:
      None.

    Returns:
      The new file stats if the file has changed. Otherwise, None.
    """
    s1 = self.fileStats
    s2 = os.stat(self.fullPath)
    app.log.info('st_mode', s1.st_mode, s2.st_mode)
    app.log.info('st_ino', s1.st_ino, s2.st_ino)
    app.log.info('st_dev', s1.st_dev, s2.st_dev)
    app.log.info('st_uid', s1.st_uid, s2.st_uid)
    app.log.info('st_gid', s1.st_gid, s2.st_gid)
    app.log.info('st_size', s1.st_size, s2.st_size)
    app.log.info('st_mtime', s1.st_mtime, s2.st_mtime)
    app.log.info('st_ctime', s1.st_ctime, s2.st_ctime)
    if (s1.st_mode == s2.st_mode and
        s1.st_ino == s2.st_ino and
        s1.st_dev == s2.st_dev and
        s1.st_uid == s2.st_uid and
        s1.st_gid == s2.st_gid and
        s1.st_size == s2.st_size and
        s1.st_mtime == s2.st_mtime and
        s1.st_ctime == s2.st_ctime):
      return s2

  def setTextBuffer(self, textBuffer):
    self.textBuffer = textBuffer