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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses
import io
import json
import os
import re
import sys
import time

import app.default_prefs
import app.log
import app.regex

importStartTime = time.time()
prefs = app.default_prefs.prefs

def joinReList(reList):
  return r"("+r")|(".join(reList)+r")"

def joinReWordList(reList):
  return r"(\b"+r"\b)|(\b".join(reList)+r"\b)"


def loadPrefs(fileName, category):
  prefs.setdefault(category, {})
  # Check the user home directory for preferences.
  prefsPath = os.path.expanduser(os.path.expandvars(
      "~/.ci_edit/prefs/%s.json" % (fileName,)))
  if os.path.isfile(prefsPath) and os.access(prefsPath, os.R_OK):
    with open(prefsPath, 'r') as f:
      try:
        additionalPrefs = json.loads(f.read())
        app.log.startup(additionalPrefs)
        prefs[category].update(additionalPrefs)
        app.log.startup('Updated editor prefs from', prefsPath)
        app.log.startup('as', prefs[category])
      except Exception as e:
        app.log.startup('failed to parse', prefsPath)
        app.log.startup('error', e)
  return prefs[category]

color8 = app.default_prefs.color8
color16 = app.default_prefs.color16
color256 = app.default_prefs.color256
prefs['color'] = color256

colorSchemeName = prefs['editor']['colorScheme']
if colorSchemeName == 'custom':
  # Check the user home directory for a color scheme preference. If found load
  # it to replace the default color scheme.
  prefs['color'].update(loadPrefs('color_scheme', 'color'))

color = prefs['color']
editor = loadPrefs('editor', 'editor')
devTest = prefs['devTest']
palette = prefs['palette']
startup = {}
status = loadPrefs('status', 'status')


grammars = {}
# Arrange all the grammars by name.
for k,v in prefs['grammar'].items():
  v['name'] = k
  grammars[k] = v

# Compile regexes for each grammar.
for k,v in prefs['grammar'].items():
  if 0:
    # keywords re.
    v['keywordsRe'] = re.compile(
        joinReWordList(v.get('keywords', []) + v.get('types', [])))
    v['errorsRe'] = re.compile(joinReList(v.get('error', [])))
    v['specialsRe'] = re.compile(joinReList(v.get('special', [])))
  # contains and end re.
  matchGrammars = []
  markers = []
  # Index [0]
  if v.get('escaped'):
    markers.append(v['escaped'])
    matchGrammars.append(v)
  else:
    # Add a non-matchable placeholder.
    markers.append(app.regex.kNonMatchingRegex)
    matchGrammars.append(None)
  # Index [1]
  if v.get('end'):
    markers.append(v['end'])
    matchGrammars.append(v)
  else:
    # Add a non-matchable placeholder.
    markers.append(app.regex.kNonMatchingRegex)
    matchGrammars.append(None)
  # Index [2..len(contains)]
  for grammarName in v.get('contains', []):
    g = grammars.get(grammarName, None)
    if g is None:
      app.log.startup('Available grammars:')
      for k,v in grammars.items():
        app.log.startup('  ', k, ':', len(v))
      raise Exception('missing grammar for "' + grammarName + '" in prefs.py')
    markers.append(g['begin'])
    matchGrammars.append(g)
  # Index [2+len(contains)..]
  markers += v.get('error', [])
  # Index [2+len(contains)+len(error)..]
  for keyword in v.get('keywords', []):
    markers.append(r'\b' + keyword + r'\b')
  # Index [2+len(contains)+len(error)+len(keywords)..]
  for types in v.get('types', []):
    markers.append(r'\b' + types + r'\b')
  # Index [2+len(contains)+len(error)+len(keywords)+len(types)..]
  markers += v.get('special', [])
  # Index [-1]
  markers.append(r'\n')
  #app.log.startup('markers', v['name'], markers)
  v['matchRe'] = re.compile(joinReList(markers))
  v['markers'] = markers
  v['matchGrammars'] = matchGrammars
  newGrammarIndexLimit = 2 + len(v.get('contains', []))
  errorIndexLimit = newGrammarIndexLimit + len(v.get('error', []))
  keywordIndexLimit = errorIndexLimit + len(v.get('keywords', []))
  typeIndexLimit = keywordIndexLimit + len(v.get('types', []))
  specialIndexLimit = typeIndexLimit + len(v.get('special', []))
  v['indexLimits'] = (newGrammarIndexLimit, errorIndexLimit, keywordIndexLimit,
      typeIndexLimit, specialIndexLimit)

# Reset the re.cache for user regexes.
re.purge()

nameToType = {}
extensions = {}
fileTypes = {}
for k,v in prefs['fileType'].items():
  for name in v.get('name', []):
    nameToType[name] = v.get('grammar')
  for ext in v['ext']:
    extensions[ext] = v.get('grammar')
  fileTypes[k] = v
if 0:
  app.log.info('extensions')
  for k,v in extensions.items():
    app.log.info('  ', k, ':', v)
  app.log.info('fileTypes')
  for k,v in fileTypes.items():
    app.log.info('  ', k, ':', v)

def init():
  defaultColor = prefs['color']['default']
  defaultKeywordsColor = prefs['color']['keyword']
  defaultSpecialsColor = prefs['color']['special']
  for k,v in grammars.items():
    # Colors.
    v['colorIndex'] = prefs['color'].get(k, defaultColor)
    if 0:
      v['keywordsColor'] = curses.color_pair(
          prefs['color'].get(k+'_keyword_color', defaultKeywordsColor))
      v['specialsColor'] = curses.color_pair(
          prefs['color'].get(k+'_special_color', defaultSpecialsColor))
  app.log.info('prefs init')

def getGrammar(filePath):
  if filePath is None:
    return grammars.get('text')
  name = os.path.split(filePath)[1]
  fileType = nameToType.get(name)
  if fileType is None:
    fileExtension = os.path.splitext(name)[1]
    fileType = extensions.get(fileExtension, 'text')
  return grammars.get(fileType)

def save(category, label, value):
  app.log.info(category, label, value)
  global prefs
  prefs.setdefault(category, {})
  prefs[category][label] = value
  prefsPath = os.path.expanduser(os.path.expandvars(
      "~/.ci_edit/prefs/%s.json" % (category,)))
  with open(prefsPath, 'w') as f:
    try:
      f.write(json.dumps(prefs[category]))
    except Exception as e:
      app.log.error('error writing prefs')
      app.log.exception(e)

app.log.startup('prefs.py import time', time.time() - importStartTime)

