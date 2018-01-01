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
    self.savedFileStat = None # Used to determine if file on disk has changed.
    self.statsLock = threading.Lock()
    self.textBuffer = None
    self.thread = None
    self.updateStats()

  def run(self):
    while not self.thread.shouldExit:
      # Redraw the screen if the file changed READ ONLY permissions.
      oldFileIsReadOnly = self.fileInfo['isReadOnly']
      newFileIsReadOnly = self.getUpdatedFileInfo()['isReadOnly']
      program = self.textBuffer.view.host
      turnoverTime = 0
      redraw = False
      if program:
        if newFileIsReadOnly != oldFileIsReadOnly:
          print(1)
          redraw = True
        if self.fileContentOnDiskChanged():
          print(2)
          app.background.bg.put((program, 'popup', None))
          redraw = True
      if redraw:
        print(3)
        before = time.time()
        # Send a redraw request.
        app.background.bg.put((program, 'redraw', self.thread.semaphore))
        # Wait for bg thread to finish refreshing before sleeping.
        self.thread.semaphore.acquire()
        turnoverTime = time.time() - before
      time.sleep(max(self.pollingInterval - turnoverTime, 0))

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

  def setTextBuffer(self, textBuffer):
    self.textBuffer = textBuffer

  def fileOnDiskChanged(self):
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

  def fileContentOnDiskChanged(self):
    """
    Checks if a file has been modified since we last opened/saved it.

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