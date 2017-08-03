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

fileHistory = {}
userHistory = {}
pathToHistory = app.prefs.prefs['userData'].get('historyPath')
checksum = None
fileSize = 0

def get(key, default={}):
  return fileHistory.setdefault(key, default)

def set(key, value):
  fileHistory[key] = value

def loadUserHistory(filePath, historyPath=pathToHistory):
  global userHistory, fileHistory, checksum, fileSize, pathToHistory
  pathToHistory = historyPath
  if os.path.isfile(historyPath):
    with open(historyPath, 'rb') as file:
      userHistory = pickle.load(file)
    checksum = calculateChecksum(filePath)
    fileSize = os.stat(filePath).st_size
    fileHistory = userHistory.get((checksum, fileSize), {})
  fileHistory['adate'] = time.time()

def saveUserHistory(filePath, historyPath=pathToHistory):
  global userHistory, fileHistory, checksum, fileSize, pathToHistory
  try:
    if historyPath is not None:
      pathToHistory = historyPath
      userHistory.pop((checksum, fileSize), None)
      checksum = calculateChecksum(filePath)
      fileSize = os.stat(filePath).st_size
      userHistory[(checksum, fileSize)] = fileHistory
      with open(historyPath, 'wb') as file:
        pickle.dump(userHistory, file)
      app.log.info('wrote pickle')
  except Exception, e:
    app.log.error('exception')

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
  global fileHistory, userHistory, pathToHistory
  fileHistory = {}
  userHistory = {}
  try:
    os.remove(pathToHistory)
    app.log.info("user history cleared")
  except Exception as e:
    app.log.error('clearUserHistory exception', e)

