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
  global userHistory, fileHistory, checksum, fileSize, pathToHistory
  pathToHistory = historyPath
  if os.path.isfile(historyPath):
    with open(historyPath, 'rb') as file:
      userHistory = pickle.load(file)

def saveUserHistory(fileInfo, fileHistory, historyPath=pathToHistory):
  """
  Args:
    fileInfo (tuple): Contains (filePath, lastChecksum, lastFileSize).
    fileHistory (dict): The history of the file that the user wants to save.
    historyPath (str): The path to the user's saved history.

  Returns:
    None
  """
  global userHistory, pathToHistory
  filePath, lastChecksum, lastFileSize = fileInfo
  try:
    if historyPath is not None:
      pathToHistory = historyPath
      userHistory.pop((lastChecksum, lastFileSize), None)
      newChecksum, newFileSize = getFileInfo(filePath)
      userHistory[(newChecksum, newFileSize)] = fileHistory
      with open(historyPath, 'wb') as file:
        pickle.dump(userHistory, file)
      app.log.info('wrote pickle')
  except Exception, e:
    app.log.error('exception')

def getFileHistory(filePath):
  checksum, fileSize = getFileInfo(filePath)
  fileHistory = userHistory.get((checksum, fileSize), {})
  fileHistory['adate'] = time.time()
  return fileHistory

def getFileInfo(filePath):
  """
  Args:
    filePath (str): The absolute path to the file.

  Returns:
    A tuple containing the checksum and size of the file.
  """
  try:
    checksum = calculateChecksum(filePath)
    fileSize = os.stat(filePath).st_size
    return (checksum, fileSize)
  except:
    return (None, 0)

def calculateChecksum(filePath):
  app.log.info("Calculate checksum of the current file")
  hasher = hashlib.sha512()
  with open(filePath, 'rb') as file:
    hasher.update(file.read())
  return hasher.hexdigest()

def clearUserHistory():
  """
  Clears user history for all files.
  """
  global userHistory, pathToHistory
  userHistory = {}
  try:
    os.remove(pathToHistory)
    app.log.info("user history cleared")
  except Exception as e:
    app.log.error('clearUserHistory exception', e)

