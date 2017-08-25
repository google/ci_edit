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
path = None

def get(index):
  global data
  if not len(data):
    return None
  return data[index % len(data)]

def add(filePath, cursorRow, cursorCol,
        markerRow, markerCol,
        penRow, penCol, selectionMode):
  global data
  bookmark = {
    'cursor': (cursorRow, cursorCol),
    'marker': (markerRow, markerCol),
    'path': filePath,
    'pen': (penRow, penCol),
    'mode': selectionMode,
  }
  data.append(bookmark)

def remove(index):
  global data
  if not len(data):
    return False
  del data[index % len(data)]
  return True

def loadUserBookmarks(filePath):
  global data, path
  try:
    path = filePath
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
    if path is not None:
      with open(path, "wb") as file:
        pickle.dump(data, file)
      app.log.info('wrote pickle')
  except Exception, e:
    app.log.error('exception')
