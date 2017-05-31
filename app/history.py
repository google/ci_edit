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

data = {}
path = "history.dat"

def get(keyPath, default=None):
  global data
  cursor = data
  for i in keyPath[:-1]:
    cursor = cursor.setdefault(i, {})
  return cursor.get(keyPath[-1], default)

def set(keyPath, value):
  global data
  cursor = data
  for i in keyPath[:-1]:
    cursor = cursor.setdefault(i, {})
  cursor[keyPath[-1]] = value
  #assert get(keyPath) == value

def loadUserHistory():
  global data, path
  try:
    if os.path.isfile(path):
      with open(path, "rb") as file:
        data = pickle.load(file)
    else:
      data = {}
  except Exception, e:
    app.log.error('exception')
    data = {}

def saveUserHistory():
  global data, path
  try:
    with open(path, "wb") as file:
      pickle.dump(data, file)
    app.log.info('wrote pickle')
  except Exception, e:
    app.log.error('exception')
