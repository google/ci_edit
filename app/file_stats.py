import os
import time
import threading

class FileStats:
  def __init__(self, fullPath, pollingInterval=1):
    """
    Args:
      fullPath (str): The absolute path of the file you want to keep track of.
      pollingInterval (int): The frequency at which you want to poll the file.
    """
    self.pollingInterval = pollingInterval
    self.fullPath = fullPath
    self.fileStats = None
    self.lock = threading.Lock()
    self.isReadOnly = True
    thread = threading.Thread(target=self.run)

  def run(self):
    try:
      while True:
        self.lock.acquire()
        self.fileStats = os.stat(self.fullPath)
        self.isReadOnly = os.access(self.fullPath, os.W_OK)
        self.lock.release()
        time.sleep(self.interval)
    except Exception as e:
      app.log.info("Exception occurred while running file stats thread:", e)

  def getFileSize(self):
    if self.fileStats:
      return self.fileStats.st_size
    else:
      return 0

  def getFileStats(self):
    return self.fileStats

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