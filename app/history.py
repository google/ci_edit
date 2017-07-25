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

fileHistory = {}
userHistory = {}
historyPath = None
hasher = None
checksum = None

def get(keyPath, default={}):
  return fileHistory.setdefault(keyPath[-1], default)

def set(keyPath, value):
  # element = fileHistory.setdefault(keyPath[-1], {})
  fileHistory[keyPath[-1]] = value
  #assert get(keyPath) == value

def loadUserHistory(historyPath, filePath):
  global userHistory, fileHistory, checksum
  if os.path.isfile(historyPath):
    with open(historyPath, 'rb') as file:
      userHistory = pickle.load(file)
    checksum = calculateChecksum(filePath)
    fileHistory = userHistory.get(checksum, {})

def saveUserHistory(historyPath, filePath):
  global userHistory, fileHistory, checksum
  try:
    if historyPath is not None:
      userHistory.pop(checksum, None)
      checksum = calculateChecksum(filePath)
      userHistory[checksum] = fileHistory
      with open(historyPath, 'wb') as file:
        pickle.dump(userHistory, file)
      app.log.info('wrote pickle')
  except Exception, e:
    app.log.error('exception')

def calculateChecksum(filePath):
  hasher = hashlib.sha512()
  with open(filePath, 'rb') as file:
    hasher.update(file.read())
  return hasher.hexdigest()

# def clearUserHistory():
#   """
#   Clears user history for all files.
#   """
#   global fileHistory, userHistory, path
#   fileHistory = {}
#   userHistory = {}
#   try:
#     os.remove(path)
#     app.log.info("user history cleared")
#   except Exception as e:
#     app.log.error('clearUserHistory exception', e)

