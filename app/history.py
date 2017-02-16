
"""
  Track user history to provide features such as resuming editing at the same
  cursor position after reloading a file; or a recient file list.
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
  app.log.debug(keyPath, value)
  assert get(keyPath) == value

def loadUserHistory():
  global data, path
  try:
    if os.path.isfile(path):
      with open(path, "rb") as file:
        data = pickle.load(file)
    else:
      data = {}
  except Exception, e:
    app.log.error('exception in loadUserPrefs')
    data = {}

def saveUserHistory():
  global data, path
  app.log.debug(data)
  try:
    with open(path, "wb") as file:
      pickle.dump(data, file)
    app.log.info('wrote pickle')
  except Exception, e:
    app.log.error('exception in saveUserPrefs')
