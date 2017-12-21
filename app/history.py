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

"""
  Track user history to provide features such as resuming editing at the same
  cursor position after reloading a file; or a recent file list.
"""
import app.log
import cPickle as pickle
import os
import hashlib
import time
import app.prefs

userHistory = {}
pathToHistory = app.prefs.prefs['userData'].get('historyPath')

def loadUserHistory(filePath, historyPath=pathToHistory):
  """
  Retrieves the user's complete edit history for all files.

  Args:
    filePath (str): The absolute path to the file.
    historyPath (str): Defaults to pathToHistory.
      The path to the user's saved history.

  Returns:
    None.
  """
  global userHistory, pathToHistory
  pathToHistory = historyPath
  if os.path.isfile(historyPath):
    with open(historyPath, 'rb') as file:
      userHistory = pickle.load(file)

def saveUserHistory(fileInfo, fileStats,
                    fileHistory, historyPath=pathToHistory):
  """
  Saves the user's file history by writing to a pickle file.

  Args:
    fileInfo (tuple): Contains (lastChecksum, lastFileSize).
    fileHistory (dict): The history of the file that the user wants to save.
    fileStats (FileStats): The FileStat object of the file to be saved.
    historyPath (str): Defaults to pathToHistory.
      The path to the user's saved history.

  Returns:
    None.
  """
  global userHistory, pathToHistory
  lastChecksum, lastFileSize = fileInfo
  try:
    if historyPath is not None:
      pathToHistory = historyPath
      userHistory.pop((lastChecksum, lastFileSize), None)
      newChecksum, newFileSize = getFileInfo(fileStats)
      userHistory[(newChecksum, newFileSize)] = fileHistory
      with open(historyPath, 'wb') as file:
        pickle.dump(userHistory, file)
      app.log.info('wrote pickle')
  except Exception as e:
    app.log.exception(e)

def getFileInfo(fileStats, data=None):
  """
  Args:
    fileStats (FileStats): a FileStats object of a file.
    data (str): Defaults to None. This is the data
      returned by calling read() on a file object.

  Returns:
    A tuple containing the (checksum, fileSize) of the file.
  """
  fileInfo = fileStats.getTrackedFileInfo()
  checksum = calculateChecksum(fileStats.fullPath, data)
  fileSize = fileInfo['size']
  return (checksum, fileSize)

def getFileHistory(fileStats, data=None):
  """
  Takes in an file path and an optimal data
  argument and checks for the current file's history.
  It stores the current time in the file history and
  returns the file history. The second argument can be
  passed in if a file's data has already been read
  so that you do not have to read the file again.

  Args:
    fileStats (FileStats): The FileStat object of the requested file.
    data (str): Defaults to None. This is the data
      returned by calling read() on a file object.

  Returns:
    The file history (dict) of the desired file if it exists.
  """
  checksum, fileSize = getFileInfo(fileStats, data)
  fileHistory = userHistory.get((checksum, fileSize), {})
  fileHistory['adate'] = time.time()
  return fileHistory

def calculateChecksum(filePath, data=None):
  """
  Calculates the hash value of the specified file.
  The second argument can be passed in if a file's data has
  already been read so that you do not have to read the file again.

  Args:
    filePath (str): The absolute path to the file.
    data (str): Defaults to None. This is the data
      returned by calling read() on a file object.

  Returns:
    The hash value of the file's data.
  """
  app.log.info("Calculate checksum of the current file")
  hasher = hashlib.sha512()
  try:
    if data:
      hasher.update(data)
    else:
      with open(filePath, 'rb') as file:
        hasher.update(file.read())
    return hasher.hexdigest()
  except:
    return None

def clearUserHistory():
  """
  Clears user history for all files.

  Args:
    None.

  Returns:
    None.
  """
  global userHistory, pathToHistory
  userHistory = {}
  try:
    os.remove(pathToHistory)
    app.log.info("user history cleared")
  except Exception as e:
    app.log.error('clearUserHistory exception', e)

