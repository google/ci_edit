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

import app.default_prefs
import app.log
import app.regex


def joinReList(reList):
    return r"(" + r")|(".join(reList) + r")"


def joinReWordList(reList):
    return r"(\b" + r"\b)|(\b".join(reList) + r"\b)"


class Prefs():

    def __init__(self):
        self.prefsDirectory = "~/.ci_edit/prefs/"
        prefs = app.default_prefs.prefs
        self.color8 = app.default_prefs.color8
        self.color16 = app.default_prefs.color16
        self.color256 = app.default_prefs.color256
        self.color = self.color256
        self.editor = prefs.get('editor', {})
        self.devTest = prefs.get('devTest', {})
        self.palette = prefs.get('palette', {})
        self.startup = {}
        self.status = prefs.get(u"status", {})
        self.userData = prefs.get(u"userData", {})
        self.__setUpGrammars(prefs.get(u"grammar", {}))
        self.__setUpFileTypes(prefs.get(u"fileType", {}))
        self.init()

    def loadPrefs(self, fileName, category):
        # Check the user home directory for preferences.
        prefsPath = os.path.expanduser(
            os.path.expandvars(
                os.path.join(self.prefsDirectory, "%s.json" % (fileName,))))
        if os.path.isfile(prefsPath) and os.access(prefsPath, os.R_OK):
            with io.open(prefsPath, 'r') as f:
                try:
                    additionalPrefs = json.loads(f.read())
                    app.log.startup(additionalPrefs)
                    category.update(additionalPrefs)
                    app.log.startup('Updated editor prefs from', prefsPath)
                    app.log.startup('as', category)
                except Exception as e:
                    app.log.startup('failed to parse', prefsPath)
                    app.log.startup('error', e)
        return category

    def init(self):
        self.editor = self.loadPrefs('editor', self.editor)
        self.status = self.loadPrefs('status', self.status)

        self.colorSchemeName = self.editor['colorScheme']
        if self.colorSchemeName == 'custom':
            # Check the user home directory for a color scheme preference. If found
            # load it to replace the default color scheme.
            self.color = self.loadPrefs('color_scheme', self.color)

        defaultColor = self.color['default']
        defaultKeywordsColor = self.color['keyword']
        defaultSpecialsColor = self.color['special']
        for k, v in self.grammars.items():
            # Colors.
            v['colorIndex'] = self.color.get(k, defaultColor)
            if 0:
                v['keywordsColor'] = curses.color_pair(
                    self.color.get(k + '_keyword_color', defaultKeywordsColor))
                v['specialsColor'] = curses.color_pair(
                    self.color.get(k + '_special_color', defaultSpecialsColor))
        app.log.info('prefs init')

    def category(self, name):
        return {
            'color': self.color,
            'editor': self.editor,
            'startup': self.startup,
        }[name]

    def getGrammar(self, filePath):
        if filePath is None:
            return self.grammars.get('text')
        name = os.path.split(filePath)[1]
        fileType = self.nameToType.get(name)
        if fileType is None:
            fileExtension = os.path.splitext(name)[1]
            fileType = self.extensions.get(fileExtension, 'text')
        return self.grammars.get(fileType)

    def save(self, category, label, value):
        app.log.info(category, label, value)
        prefCategory = self.category(category)
        prefCategory[label] = value
        prefsPath = os.path.expanduser(
            os.path.expandvars(
                os.path.join(self.prefsDirectory, "%s.json" % (category,))))
        with io.open(prefsPath, 'w', encoding=u"utf-8") as f:
            try:
                f.write(json.dumps(prefs[category]))
            except Exception as e:
                app.log.error('error writing prefs')
                app.log.exception(e)

    def __setUpGrammars(self, defaultGrammars):
        self.grammars = {}
        # Arrange all the grammars by name.
        for k, v in defaultGrammars.items():
            v['name'] = k
            self.grammars[k] = v

        # Compile regexes for each grammar.
        for k, v in defaultGrammars.items():
            if 0:
                # keywords re.
                v['keywordsRe'] = re.compile(
                    joinReWordList(v.get('keywords', []) + v.get('types', [])))
                v['errorsRe'] = re.compile(joinReList(v.get('errors', [])))
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
                g = self.grammars.get(grammarName, None)
                if g is None:
                    app.log.startup('Available grammars:')
                    for k, v in self.grammars.items():
                        app.log.startup('  ', k, ':', len(v))
                    raise Exception('missing grammar for "' + grammarName +
                                    '" in prefs.py')
                markers.append(g['begin'])
                matchGrammars.append(g)
            # Index [2+len(contains)..]
            markers += v.get('errors', [])
            # Index [2+len(contains)+len(error)..]
            for keyword in v.get('keywords', []):
                markers.append(r'\b' + keyword + r'\b')
            # Index [2+len(contains)+len(error)+len(keywords)..]
            for types in v.get('types', []):
                markers.append(r'\b' + types + r'\b')
            # Index [2+len(contains)+len(error)+len(keywords)+len(types)..]
            markers += v.get('special', [])
            # Index [-2]
            markers.append(u'[\u3000-\uffff]+')
            # Index [-1]
            markers.append(r'\n')
            #app.log.startup('markers', v['name'], markers)
            v['matchRe'] = re.compile(joinReList(markers))
            v['markers'] = markers
            v['matchGrammars'] = matchGrammars
            newGrammarIndexLimit = 2 + len(v.get('contains', []))
            errorIndexLimit = newGrammarIndexLimit + len(v.get('errors', []))
            keywordIndexLimit = errorIndexLimit + len(v.get('keywords', []))
            typeIndexLimit = keywordIndexLimit + len(v.get('types', []))
            specialIndexLimit = typeIndexLimit + len(v.get('special', []))
            v['indexLimits'] = (newGrammarIndexLimit, errorIndexLimit,
                                keywordIndexLimit, typeIndexLimit,
                                specialIndexLimit)

        # Reset the re.cache for user regexes.
        re.purge()

    def __setUpFileTypes(self, defaultFileTypes):
        self.nameToType = {}
        self.extensions = {}
        fileTypes = {}
        for k, v in defaultFileTypes.items():
            for name in v.get('name', []):
                self.nameToType[name] = v.get('grammar')
            for ext in v['ext']:
                self.extensions[ext] = v.get('grammar')
            fileTypes[k] = v
        if 0:
            app.log.info('extensions')
            for k, v in extensions.items():
                app.log.info('  ', k, ':', v)
            app.log.info('fileTypes')
            for k, v in fileTypes.items():
                app.log.info('  ', k, ':', v)
