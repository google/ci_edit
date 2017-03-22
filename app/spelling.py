# Copyright 2017 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.log
import os

dictionaryPath = 'app/dictionary.en-US.words'

words = set()
grammarWords = {}

if os.path.isfile(dictionaryPath):
  with open(dictionaryPath, 'r') as f:
    lines = f.readlines()
    index = 0
    while not len(lines[index]) or lines[index][0] == '#':
      index += 1
    words = set([w for l in lines for w in l.split()])
    #print (words)
else:
  app.log.error('dictionary not found', dictionaryPath)

def isCorrect(word, grammarName):
  if len(word) <= 1:
    return True
  if word.lower() in words:
    return True
  return word in grammarWords.get(grammarName, set())
