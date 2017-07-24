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

data = {}
path = None
md5 = hashlib.md5()

def get(keyPath, default=None):
  global data
  data = data.setdefault(keyPath[-1], {})
  return data.get(keyPath[-1], default)

def set(keyPath, value):
  global data
  data = data.setdefault(keyPath[-1], {})
  data[keyPath[-1]] = value
  #assert get(keyPath) == value

def loadUserHistory(filePath):
  global data, path
  try:
    path = filePath
    if os.path.isfile(path):
      with open(path, "rb") as file:
        data = pickle.load(file)
    else:
      data = {}
    import pdb; pdb.set_trace()
  except Exception, e:
    app.log.error('exception')
    data = {}

def saveUserHistory():
  global data, path
  try:
    if path is not None:
      with open(path, "wb") as file:
        pickle.dump(data, file)
      app.log.info('wrote pickle')
    import pdb; pdb.set_trace()
  except Exception, e:
    app.log.error('exception')

def clearUserHistory():
  """
  Clears all user history from all files.
  """
  global data, path
  data = {}
  try:
    os.remove(path)
    app.log.info("user history cleared")
  except Exception as e:
    app.log.error('clearUserHistory exception', e)

