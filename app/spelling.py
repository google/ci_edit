# Copyright 2017 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.log
import glob
import os
import re


grammarWords = {}

def loadWords(dirPath):
  global grammarWords
  dirPath = os.path.join(dirPath, 'dictionary.')
  for path in glob.iglob(dirPath+'*.words'):
    if os.path.isfile(path):
      grammarName = path[len(dirPath):-len('.words')]
      with open(path, 'r') as f:
        lines = f.readlines()
        index = 0
        while not len(lines[index]) or lines[index][0] == '#':
          index += 1
        # TODO(dschuyler): Word contractions are hacked by storing the
        # components of the contraction. So didn, doesn, and isn are considered
        # 'words'.
        grammarWords[grammarName] = set([
            p for l in lines for w in l.split() for p in w.split("'")])
loadWords(os.path.dirname(__file__))
loadWords(os.path.expanduser("~/.ci_edit/dictionaries"))

words = grammarWords.get('en-US', set())
words.update(grammarWords.get('coding', set()))
words.update(grammarWords.get('contractions', set()))
words.update(grammarWords.get('user', set()))


def isCorrect(word, grammarName):
  if len(word) <= 1:
    return True
  if word in words or word.lower() in words:
    return True
  if re.sub('^sub', '', word.lower()) in words:
    return True
  if word.lower() in grammarWords.get(grammarName, set()):
    return True
  if len(re.sub('[A-Z]+', '', word)) == 0:
    # All upper case.
    return True
  #app.log.info(grammarName, word)
  return False
