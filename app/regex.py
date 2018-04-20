# Copyright 2018 Google Inc.
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

import re


def joinReList(reList):
  return r"("+r")|(".join(reList)+r")"

def joinReWordList(reList):
  return r"(\b"+r"\b)|(\b".join(reList)+r"\b)"


kNonMatchingRegex = r'^\b$'
kReNonMatching = re.compile(kNonMatchingRegex)

kReBrackets = re.compile('[[\]{}()]')

kReComments = re.compile('(?:#|//).*$|/\*.*?\*/|<!--.*?-->')

kReEndSpaces = re.compile(r'\s+$')

kReStrings = re.compile(
    r"(\"\"\".*?(?<!\\)\"\"\")|('''.*?(?<!\\)''')|(\".*?(?<!\\)\")|('.*?(?<!\\)')")

# The first group is a hack to allow upper case pluralized, e.g. URLs.
kReSubwords = re.compile(
    r'(?:[A-Z]{2,}s\b)|(?:[A-Z][a-z]+)|(?:[A-Z]+(?![a-z]))|(?:[a-z]+)')

kReSubwordBoundaryFwd = re.compile(
    '(?:[_-]?[A-Z][a-z-]+)|(?:[_-]?[A-Z]+(?![a-z]))|(?:[_-]?[a-z]+)|(?:\W+)')

kReSubwordBoundaryRvr = re.compile(
    '(?:[A-Z][a-z-]+[_-]?)|(?:[A-Z]+(?![a-z])[_-]?)|(?:[a-z]+[_-]?)|(?:\W+)')

kReWordBoundary = re.compile('(?:\w+)|(?:\W+)')

__commonNumbersRegex = (
    # Don't include the [-+]? at the start of a number because it mismatches
    # an equation like 0x33-0x44.
    r'(?:'
    r'0[xX][A-Fa-f0-9]+'
    r'|\d+(?:(?:[uUlL][lL]?[lL]?)|\.?(?:\d+)?(?:e[-+]\d+)?[fFdD]?)?'
    r'|\.\d+[fFdD]?'
    r')'
    #r'0[xX][^A-Fa-f0-9]+(?:[uUlL][lL]?[lL]?)?(?!\w)',
    #r'[-+]?[0-9]*\.[0-9]+(?:[eE][+-][0-9]+)?[fF]?(?!\w)',
    #r'[-+]?[0-9]+(?:\.[0-9]*(?:[eE][+-][0-9]+)?)?[fF]?(?!\w)',
    #r'[-+]?[0-9]+(?:[uUlL][lL]?[lL]?)?(?!\w)',
    )
kReNumbers = re.compile(__commonNumbersRegex)

# Trivia: all English contractions except 'sup, 'tis and 'twas will
# match this regex (with re.I):  [adegIlnotuwy]'[acdmlsrtv]
# The prefix part of that is used in the expression below to identify
# English contractions.
kEnglishContractionRegex = \
    r"(\"(\\\"|[^\"])*?\")|(?<![adegIlnotuwy])('(\\\'|[^'])*?')"
