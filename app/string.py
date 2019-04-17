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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
try:
    unicode
except NameError:
    unicode = str
    unichr = chr

import app.config

ENCODE = {
    u'\\': u'\\\\',
    u'\a': u'\\a',
    u'\b': u'\\b',
    u'\f': u'\\f',
    u'\n': u'\\n',
    u'\r': u'\\r',
    u'\t': u'\\t',
    u'\v': u'\\v',
    u'\x7f': u'\\x7f',
}

DECODE = {
    u'\\': u'\\',
    u'a': u'\a',
    u'b': u'\b',
    u'f': u'\f',
    u'n': u'\n',
    u'r': u'\r',
    u't': u'\t',
    u'v': u'\v',
}


def pathEncode(path):
    if app.config.strict_debug:
        assert isinstance(path, unicode), repr(path)
    out = u""
    for i in range(len(path)):
        c = path[i]
        ord_c = ord(c)
        t = ENCODE.get(c)
        if t is not None:
            c = t
        elif ord_c < 32:
            c = u'\\x%02x' % (ord_c,)
        out += c
    return out


def pathDecode(path):
    if app.config.strict_debug:
        assert isinstance(path, unicode)
    out = u''
    limit = len(path)
    i = 0
    while i < limit:
        c = path[i]
        i += 1
        if c == u'\\':
            if i >= len(path):
                out += u'\\'
                break
            c = path[i]
            i += 1
            if c == u'x':
                c = unichr(path[i - 1:i + 3])
            elif c == u'u' or c == u'o':
                c = unichr(path[i - 1:i + 5])
            elif c == u'U':
                c = unichr(path[i - 1:i + 9])
            else:
                c = DECODE.get(c, u'\\')
        out += c
    return out


def columnWidth(string):
    """When rendering |string| how many character cells will be used? For ASCII
    characters this will equal len(string). For many Chinese characters and
    emoji the value will be greater than len(string), since many of them use two
    cells.
    """
    if app.config.strict_debug:
        assert isinstance(string, unicode)
    MIN_DOUBLE_WIDE_CHARACTER = u"\u3000"
    width = 0
    for i in string:
        if i > MIN_DOUBLE_WIDE_CHARACTER:
            width += 2
        else:
            width += 1
    return width

def wrapLines(lines, indent, width):
    """Word wrap lines of text.

    Args:
      lines (list of unicode): input text.
      indent (unicode): will be added as a prefix to each line of output.
      width (int): is the column limit for the strings. Each double-wide
        character counts as two columns.

    Returns:
      List of strings
    """
    if app.config.strict_debug:
        assert isinstance(lines, tuple), repr(lines)
        assert len(lines) == 0 or isinstance(lines[0], unicode)
        assert isinstance(indent, unicode), repr(path)
        assert isinstance(width, int), repr(int)
    # There is a textwrap library in Python, but I was having trouble getting it
    # to do exactly what I desired. It may be useful to revisit textwrap later.
    words = u" ".join(lines).split()
    output = [indent]
    indentLen = columnWidth(indent)
    index = 0
    while index < len(words):
        lineLen = columnWidth(output[-1])
        word = words[index]
        wordLen = columnWidth(word)
        if lineLen == indentLen and lineLen + wordLen < width:
            output[-1] += word
        elif lineLen + wordLen + 1 < width:
            output[-1] += u" " + word
        else:
            output.append(indent + word)
        index += 1
    return output
