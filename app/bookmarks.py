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

import app.log
import cPickle as pickle
import os

data = []
path = "bookmarks.dat"

def get(index):
  global data
  if not len(data):
    return None
  return data[index % len(data)]

def add(filePath, row, col, length, selectionMode):
  global data
  bookmark = {
    'path': filePath,
    'row': row,
    'col': col,
    'length': length,
    'mode': selectionMode,
  }
  data.append(bookmark)

def remove(index):
  global data
  if not len(data):
    return False
  del data[index % len(data)]
  return True

def loadUserBookmarks():
  global data, path
  try:
    if os.path.isfile(path):
      with open(path, "rb") as file:
        data = pickle.load(file)
    else:
      data = []
  except Exception, e:
    app.log.error('exception')
    data = []

def saveUserBookmarks():
  global data, path
  try:
    with open(path, "wb") as file:
      pickle.dump(data, file)
    app.log.info('wrote pickle')
  except Exception, e:
    app.log.error('exception')
