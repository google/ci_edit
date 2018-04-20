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

__commonNumbersRegex = [
  r'[-+]?[0-9]*\.[0-9]+(?:[eE][+-][0-9]+)?[fF]?(?!\w)',
  r'[-+]?[0-9]+(?:\.[0-9]*(?:[eE][+-][0-9]+)?)?[fF]?(?!\w)',
  r'[-+]?[0-9]+(?:[uUlL][lL]?[lL]?)?(?!\w)',
  r'0[xX][^A-Fa-f0-9]+(?:[uUlL][lL]?[lL]?)?(?!\w)',
]
kReNumbers = re.compile(joinReList(__commonNumbersRegex))

# Trivia: all English contractions except 'sup, 'tis and 'twas will
# match this regex (with re.I):  [adegIlnotuwy]'[acdmlsrtv]
# The prefix part of that is used in the expression below to identify
# English contractions.
kEnglishContractionRegex = \
    r"(\"(\\\"|[^\"])*?\")|(?<![adegIlnotuwy])('(\\\'|[^'])*?')"

if 0:
  def numberTest(str, expectRegs):
    sre = kNumbersRe.search(str)
    if sre:
      app.log.startup('%16s %16s %-16s %s ' % (
          str, expectRegs, sre.regs[0], sre.groups()))
    else:
      app.log.startup('%16s %16s %-16s ' % (str, expectRegs, sre))


  numberTest('.', None)
  numberTest('2', (0, 1))
  numberTest(' 2 ', (1, 2))
  numberTest('242.2', (0, 5))
  numberTest('.2', (0, 2))
  numberTest('2.', (0, 2))
  numberTest('.2a', None)
  numberTest('2.a', (0, 1))
  numberTest('+0.2e-15', (0, 8))
  numberTest('02factor', None)
  numberTest('02f', (0, 3))
  numberTest('02ull', (0, 5))
  numberTest('02u', (0, 3))
