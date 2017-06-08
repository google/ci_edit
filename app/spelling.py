# Copyright 2017 Google Inc.
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

words = grammarWords.get('en-us', set())
words.update(grammarWords.get('en-misc', set()))
words.update(grammarWords.get('chromium', set()))
words.update(grammarWords.get('name', set()))
words.update(grammarWords.get('coding', set()))
words.update(grammarWords.get('contractions', set()))
words.update(grammarWords.get('user', set()))
# TODO(dschuyler): provide a UI to enable selected dictionaries.
words.update(grammarWords.get('cpp', set()))
words.update(grammarWords.get('en-gb', set()))
words.update(grammarWords.get('html', set()))


def isCorrect(word, grammarName):
  if len(word) <= 1:
    return True
  lowerWord = word.lower()
  if word in words or lowerWord in words:
    return True
  if lowerWord in grammarWords.get(grammarName, set()):
    return True
  if lowerWord.startswith('sub') and lowerWord[3:] in words:
    return True
  if lowerWord.startswith('un') and lowerWord[2:] in words:
    return True
  if 1:
    if len(word) == 2 and word[1] == 's' and word[0].isupper():
      # Upper case, with an 's' for plurality (e.g. PDFs).
      return True
  if 0:
    if len(re.sub('[A-Z]', '', word)) == 0:
      # All upper case.
      return True
  if 0:
    # TODO(dschuyler): This is an experiment. Considering a py specific word
    # list instead.
    if grammarName == 'py':
      # Handle run together (undelineated) words.
      if len(re.sub('[a-z]+', '', word)) == 0:
        for i in range(len(word), 0, -1):
          if word[:i] in words and word[i:] in words:
            return True
  #app.log.info(grammarName, word)
  return False
