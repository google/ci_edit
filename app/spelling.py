# Copyright 2017 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.log
import glob
import os

dictionaryPath = 'app/dictionary.en-US.words'

grammarWords = {}

for path in glob.iglob('app/dictionary.*.words'):
  if os.path.isfile(path):
    grammarName = path[len('app/dictionary.'):-len('.words')]
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
  if word.lower() in words:
    return True
  if grammarName not in grammarWords:
    app.log.info(grammarName)
  return word in grammarWords.get(grammarName, set())
