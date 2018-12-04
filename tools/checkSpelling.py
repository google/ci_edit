#!/usr/bin/env python

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

from __future__ import print_function

import io
import os
import re
import sys
from fnmatch import fnmatch

ciEditDir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ciEditDir)
import app.regex
import app.spelling

print("checking spelling")

doValues = False
root = (len(sys.argv) > 1 and sys.argv[1]) or "."
filePattern = (len(sys.argv) > 2 and sys.argv[2]) or "*.*"


kReIgnoreDirs = re.compile(r'''/\.git/''')
kReIgnoreFiles = re.compile(r'''\.pyc$|.pyo$''')
assert kReIgnoreDirs.search('/apple/.git/orange')
assert kReIgnoreFiles.search('/apple.pyc')
app.spelling.loadWords(os.path.join(ciEditDir, 'app'))

allUnrecognizedWords = set()

def handleFile(fileName):
  global allUnrecognizedWords
  # print(fileName, end="")
  with io.open(fileName, "r") as f:
    data = f.read()
    if not data: return set()

    unrecognizedWords = set()
    for found in re.finditer(app.regex.kReSubwords, data):
      reg = found.regs[0]
      word = data[reg[0]:reg[1]]
      if not app.spelling.isCorrect(word, 'py'):
        unrecognizedWords.add(word.lower())

    if unrecognizedWords:
      print('found', fileName)
      print(unrecognizedWords)
      print()
    return unrecognizedWords

def walkTree(root):
  unrecognizedWords = set()
  for (dirPath, dirNames, fileNames) in os.walk(root):
    if kReIgnoreDirs.search(dirPath):
      continue
    for fileName in filter(lambda x: fnmatch(x, filePattern), fileNames):
      if kReIgnoreFiles.search(fileName):
        continue
      unrecognizedWords.update(handleFile(os.path.join(dirPath, fileName)))
  return unrecognizedWords

if os.path.isfile(root):
  print(handleFile(root))
elif os.path.isdir(root):
  words = sorted(walkTree(root))
  for i in words:
    print(i)
else:
  print("root is not a file or directory")

print("end")
