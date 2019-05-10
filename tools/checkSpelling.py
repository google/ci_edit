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

import glob
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

kReWords = re.compile(r'''(\w+)''')
# The first group is a hack to allow upper case pluralized, e.g. URLs.
kReSubwords = re.compile(
    r'((?:[A-Z]{2,}s\b)|(?:[A-Z][a-z]+)|(?:[A-Z]+(?![a-z]))|(?:[a-z]+))')


kReIgnoreDirs = re.compile(r'''/\.git/''')
kReIgnoreFiles = re.compile(
    r'''\.(pyc|pyo|png|a|jpg|tif|mp3|mp4|cpuperf|dylib|avi|so|plist|raw|webm)$''')
kReIncludeFiles = re.compile(
    r'''\.(cc)$''')
assert kReIgnoreDirs.search('/apple/.git/orange')
assert kReIgnoreFiles.search('/apple.pyc')

dictionaryList = glob.glob(os.path.join(ciEditDir, 'app/dictionary.*.words'))
dictionaryList = [i[15:-6] for i in dictionaryList]
print(dictionaryList)
pathPrefs = []
dictionary = app.spelling.Dictionary(dictionaryList, pathPrefs)
assert dictionary.isCorrect(u"has", 'cpp')

def handleFile(fileName, unrecognizedWords):
    # print(fileName, end="")
    try:
        with io.open(fileName, "r") as f:
            data = f.read()
            if not data: return
            for sre in kReSubwords.finditer(data):
                #print(repr(sre.groups()))
                word = sre.groups()[0].lower()
                if not dictionary.isCorrect(word, 'cpp'):
                    if word not in unrecognizedWords:
                        print (word, end=",")
                    unrecognizedWords.add(word)
    except UnicodeDecodeError:
        print("Error decoding:", fileName)


def walkTree(root):
    unrecognizedWords = set()
    for (dirPath, dirNames, fileNames) in os.walk(root):
        if kReIgnoreDirs.search(dirPath):
            continue
        for fileName in filter(lambda x: fnmatch(x, filePattern), fileNames):
            if kReIgnoreFiles.search(fileName):
                continue
            if kReIncludeFiles.search(fileName):
                handleFile(os.path.join(dirPath, fileName), unrecognizedWords)
    if unrecognizedWords:
        print('found', fileName)
        print(unrecognizedWords)
        print()
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
