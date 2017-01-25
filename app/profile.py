

import time

profiles = {}

def start():
  return time.time()

def current(key, value):
  profiles[key] = value

def highest(key, value):
  if value > profiles.get(key):
    profiles[key] = value

def lowest(key, value):
  if value < profiles.get(key, value):
    profiles[key] = value

def highestDelta(key, start):
  delta = time.time() - start
  if delta > profiles.get(key):
    profiles[key] = delta

def runningDelta(key, start):
  delta = time.time() - start
  profiles[key] = profiles.get(key, 0)*.9
  if delta > profiles[key]:
    profiles[key] = delta

def results():
  return "one\ntwo\nthree"


