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

import app.default_prefs
import app.log
import curses
import json
import os
import re
import sys
import time

importStartTime = time.time()

commentColorIndex = 2
defaultColorIndex = 18
foundColorIndex = 32
keywordsColorIndex = 21
selectedColor = 64  # Active find is a selection.
specialsColorIndex = 20
stringColorIndex = 5
outsideOfBufferColorIndex = 211

kNonMatchingRegex = r'^\b$'
kReNonMatching = re.compile(kNonMatchingRegex)
prefs = app.default_prefs.prefs

def joinReList(reList):
  return r"("+r")|(".join(reList)+r")"

def joinReWordList(reList):
  return r"(\b"+r"\b)|(\b".join(reList)+r"\b)"


if 1:
  # Check the user home directory for editor preferences.
  prefsPath = os.path.expanduser(os.path.expandvars(
      "~/.ci_edit/prefs/editor.json"))
  if os.path.isfile(prefsPath) and os.access(prefsPath, os.R_OK):
    with open(prefsPath, 'r') as f:
      try:
        editorPrefs = json.loads(f.read())
        app.log.startup(editorPrefs)
        prefs['editor'].update(editorPrefs)
      except:
        app.log.startup('failed to parse', prefsPath)

builtInColorSchemes = {
  'dark': {},
  'light': {},
  'sky': {},
}

colorSchemeName = prefs['editor']['colorScheme']
if colorSchemeName == 'custom':
  # Check the user home directory for a color scheme preference. If found load
  # it to replace the default color scheme.
  prefsPath = os.path.expanduser(os.path.expandvars(
      "~/.ci_edit/prefs/color_scheme.json"))
  if os.path.isfile(prefsPath) and os.access(prefsPath, os.R_OK):
    with open(prefsPath, 'r') as f:
      try:
        colorScheme = json.loads(f.read())
        app.log.startup(colorScheme)
        prefs['color'].update(colorScheme)
      except:
        app.log.startup('failed to parse', prefsPath)
elif colorSchemeName in builtInColorSchemes:
    prefs['color'].update(builtInColorSchemes[colorSchemeName])


grammars = {}
# Arrange all the grammars by name.
for k,v in prefs['grammar'].items():
  v['name'] = k
  grammars[k] = v

# Compile regexes for each grammar.
for k,v in prefs['grammar'].items():
  # keywords re.
  v['keywordsRe'] = re.compile(
      joinReWordList(v.get('keywords', []) + v.get('types', [])))
  v['specialsRe'] = re.compile(joinReList(v.get('special', [])))
  # contains and end re.
  matchGrammars = []
  markers = []
  if v.get('escaped'):
    markers.append(v['escaped'])
    matchGrammars.append(v)
  else:
    # Add a non-matchable placeholder.
    markers.append(kNonMatchingRegex)
    matchGrammars.append(None)
  if v.get('end'):
    markers.append(v['end'])
    matchGrammars.append(v)
  else:
    # Add a non-matchable placeholder.
    markers.append(kNonMatchingRegex)
    matchGrammars.append(None)
  for grammarName in v.get('contains', []):
    g = grammars.get(grammarName, None)
    if g is None:
      app.log.startup('Available grammars:')
      for k,v in grammars.items():
        app.log.startup('  ', k, ':', len(v))
      print 'missing grammar for "' + grammarName + '" in prefs.py'
      sys.exit(1)
    markers.append(g['begin'])
    matchGrammars.append(g)
  markers.append(r'\n')
  app.log.startup('markers', markers)
  v['matchRe'] = re.compile(joinReList(markers))
  v['matchGrammars'] = matchGrammars
# Reset the re.cache for user regexes.
re.purge()

extensions = {}
fileTypes = {}
for k,v in prefs['fileType'].items():
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
  for k,v in prefs['grammar'].items():
    # Colors.
    v['colorIndex'] = prefs['color'].get(k, defaultColor)
    if 0:
      v['keywordsColor'] = curses.color_pair(
          prefs['color'].get(k+'_keyword_color', defaultKeywordsColor))
      v['specialsColor'] = curses.color_pair(
          prefs['color'].get(k+'_special_color', defaultSpecialsColor))
  app.log.info('prefs init')

def getGrammar(fileExtension):
  if fileExtension is None:
    return grammars.get('none')
  fileType = extensions.get(fileExtension, 'text')
  return grammars.get(fileType)

app.log.startup('prefs.py import time', time.time() - importStartTime)

