import app.background
import app.log
import app.prefs
import os
import time
import threading
import app.window

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
    self.fullPath = fullPath
    self.fileStats = None
    self.pollingInterval = pollingInterval
    # All necessary file info should be placed in this dictionary.
    self.fileInfo = {'isReadOnly': False,
                     'size': 0}
    self.statsLock = threading.Lock()
    self.textBuffer = None
    if app.prefs.editor['useBgThread']:
      self.threadSema = threading.Semaphore(0)
      self.threadShouldExit = False
      self.thread = self.startTracking()
    else:
      self.threadSema = None
      self.threadShouldExit = True
      self.thread = None
    self.updateStats()

  def run(self):
    while not self.threadShouldExit:
      # Redraw the screen if the file changed READ ONLY permissions.
      oldFileIsReadOnly = self.fileInfo['isReadOnly']
      newFileIsReadOnly = self.getUpdatedFileInfo()['isReadOnly']
      if (newFileIsReadOnly != oldFileIsReadOnly and
          self.textBuffer and self.textBuffer.view.textBuffer):
        app.background.bg.put(
            (self.textBuffer.view.host, 'redraw', self.threadSema))
        self.threadSema.acquire()
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
    self.updateStats()
    self.thread = self.startTracking()

  def startTracking(self):
    """
    Starts tracking the file whose path is specified in self.fullPath

    Args:
      None.

    Returns:
      The thread that was created to do the tracking.
    """
    if self.fullPath and app.prefs.editor['useBgThread']:
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
