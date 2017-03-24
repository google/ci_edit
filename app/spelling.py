# Copyright 2017 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.log
import glob
import os
import re


pathPrefix = os.path.join(
    os.path.dirname(__file__), 'dictionary.')

grammarWords = {}

for path in glob.iglob(pathPrefix+'*.words'):
  if os.path.isfile(path):
    grammarName = path[len(pathPrefix):-len('.words')]
    with open(path, 'r') as f:
      lines = f.readlines()
      index = 0
      while not len(lines[index]) or lines[index][0] == '#':
        index += 1
      grammarWords[grammarName] = set([w for l in lines for w in l.split()])
words = grammarWords.get('en-US', set())


def isCorrect(word, grammarName):
  if len(word) <= 1:
    return True
  if word in words or word.lower() in words:
    return True
  if re.sub('^sub', '', word.lower()) in words:
    return True
  app.log.info(grammarName, word)
  if grammarName not in grammarWords:
    app.log.info(grammarName, word)
  if word.lower() in grammarWords.get(grammarName, set()):
    return True
  if len(re.sub('[A-Z]+', '', word)) == 0:
    # All upper case.
    return True
  return False
