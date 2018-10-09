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

import re
import os

import app.log
import app.regex

commentColorIndex = 2
defaultColorIndex = 18
foundColorIndex = 32
keywordsColorIndex = 21
selectedColor = 64  # Active find is a selection.
specialsColorIndex = 20
stringColorIndex = 5
outsideOfBufferColorIndex = 211

_todo = r'TODO\([\S@.]+\)'

__common_keywords = [
  'break', 'continue', 'else',
  'for', 'if', 'return', 'while',
]

__c_keywords = __common_keywords + [
  'case', 'const', 'default', 'do', 'enum',
  'goto', 'sizeof', 'static', 'struct', 'switch',
  'typedef',
]

__c_primitive_types = [
  'bool', 'char', 'double', 'float', 'int',
  'int8_t', 'int16_t', 'int32_t', 'int64_t',
  'int_fast8_t', 'int_fast16_t', 'int_fast32_t', 'int_fast64_t',
  'int_least8_t', 'int_least16_t', 'int_least32_t', 'int_least64_t',
  'int_max_t',
  'int8_t', 'int16_t', 'int32_t', 'int64_t',
  'intptr_t', 'ptrdiff_t', 'size_t',
  'long', 'signed', 'short',
  'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
  'uint_fast8_t', 'uint_fast16_t', 'uint_fast32_t', 'uint_fast64_t',
  'uint_least8_t', 'uint_least16_t', 'uint_least32_t', 'uint_least64_t',
  'uint_max_t', 'uintptr_t',
  'unsigned',
  'void', 'wchar_t',
]

__chrome_extension = r'''\b[a-z]{32}\b'''
__sha_1 = r'''\b[a-z0-9]{40}\b'''

__special_string_escapes = [
  r'\\\\', r'\\b', r'\\f', r'\\n', r'\\r', r'\\t', r'\\v', r'\\0[0-7]{0,3}',
  __chrome_extension, __sha_1,
]

color8 = {
  '_pre_selection': 1,
  'bracket': 1,
  'c': 0,
  'c_preprocessor': 1,
  'c_raw_string1': 3,
  'c_raw_string2': 3,
  'c_string1': 3,
  'c_string2': 3,
  'context_menu': 1,
  'cpp_block_comment': 2,
  'cpp_line_comment': 2,
  'cpp_string_literal': 2,
  'debug_window': 1,
  'default': 0,
  'doc_block_comment': 3,
  'error': 7,
  'found_find': 1,
  'highlight': 3,
  'html_block_comment': 2,
  'html_element': 1,
  'html_element_end': 1,
  'js_string': 3,
  'keyword': 1,
  'line_number': 7,
  'line_number_current': 6,
  'line_overflow': 7,
  'logo': 7,
  'matching_bracket': 1,
  'matching_find': 1,
  'md_link': 2,
  'message_line': 3,
  'misspelling': 3,
  'number': 1,
  'outside_document': 7,
  'popup_window': 0,
  'pound_comment': 3,
  'py_raw_string1': 2,
  'py_raw_string2': 2,
  'py_string1': 2,
  'py_string2': 2,
  'quoted_string2': 2,
  'regex_string': 2,
  'right_column': 6,
  'selected': 5,
  'special': 1,
  'status_line': 7,
  'status_line_error': 7,
  'text': 0,
  'top_info': 7,
  'trailing_space': 1,
  'type': 1,
}

for i in color8.values():
  assert 0 <= i < 8, i

color256 = {
  '_pre_selection': stringColorIndex,
  'bracket': 6,
  'c': defaultColorIndex,
  'c_preprocessor': 1,
  'c_raw_string1': stringColorIndex,
  'c_raw_string2': stringColorIndex,
  'c_string1': stringColorIndex,
  'c_string2': stringColorIndex,
  'context_menu': 201,
  'cpp_block_comment': commentColorIndex,
  'cpp_line_comment': commentColorIndex,
  'cpp_string_literal': stringColorIndex,
  'debug_window': defaultColorIndex,
  'default': defaultColorIndex,
  'doc_block_comment': commentColorIndex,
  'error': 9,
  'found_find': foundColorIndex,
  'highlight': 96,
  'html_block_comment': commentColorIndex,
  'html_element': keywordsColorIndex,
  'html_element_end': keywordsColorIndex,
  'js_string': stringColorIndex,
  'keyword': keywordsColorIndex,
  'line_number': 168,
  'line_number_current': 146,
  'line_overflow': 105,
  'logo': 168,
  'matching_bracket': 201,
  'matching_find': 9,
  'md_link': stringColorIndex,
  'message_line': 3,
  'misspelling': 9,
  'number': 31,
  'outside_document': outsideOfBufferColorIndex,
  'popup_window': 117,
  'pound_comment': commentColorIndex,
  'py_raw_string1': stringColorIndex,
  'py_raw_string2': stringColorIndex,
  'py_string1': stringColorIndex,
  'py_string2': stringColorIndex,
  'quoted_string2': stringColorIndex,
  'regex_string': stringColorIndex,
  'right_column': outsideOfBufferColorIndex,
  'selected': selectedColor,
  'special': specialsColorIndex,
  'status_line': 168,
  'status_line_error': 161,
  'text': defaultColorIndex,
  'top_info': 168,
  'trailing_space': 180,
  'type': keywordsColorIndex,
}

for i in color256.values():
  assert 0 <= i < 256, i

# Please keep these color dictionaries in sync.
assert color8.keys() == color256.keys()


# These prefs are not fully working.
prefs = {
  'color': {
  },
  'devTest': {
  },
  'editor': {
    'autoInsertClosingCharacter': False,
    'captiveCursor': False,
    'colorScheme': 'default',
    'filesShowDotFiles': True,
    'filesShowSizes': True,
    'filesShowModifiedDates': True,
    'filesSortAscendingByName': True,
    'filesSortAscendingBySize': None,
    'filesSortAscendingByModifiedDate': None,
    'findDotAll': False,
    'findIgnoreCase': True,
    'findLocale': False,
    'findMultiLine': False,
    'findUnicode': True,
    'findUseRegex': True,
    'findVerbose': False,
    'findWholeWord': False,
    'indentation': '  ',
    'lineLimitIndicator': 80,
    'naturalScrollDirection': True,
    'onSaveStripTrailingSpaces': True,
    'optimalCursorCol': 0.98,  # Ratio of columns: 0 left, 1.0 right.
    'optimalCursorRow': 0.28,  # Ratio of rows: 0 top, 0.5 middle, 1.0 bottom.
    'palette': 'default',
    'palette8': 'default8',
    'predictionShowOpenFiles': True,
    'predictionShowAlternateFiles': True,
    'predictionShowRecentFiles': True,
    'predictionSortAscendingByType': True,
    'predictionSortAscendingByName': None,
    'predictionSortAscendingByStatus': None,
    'saveUndo': True,
    'showLineNumbers': True,
    'showStatusLine': True,
    'showTopInfo': True,
    'useBgThread': True,
  },
  'fileType': {
    'bash': {
      'ext': ['.bash', '.sh'],
      'grammar': 'bash',
    },
    'binary': {
      'ext': [
        '.exe', '.gz', '.gzip', '.jar', '.jpg', '.jpeg', '.o', '.obj',
        '.png', '.pyc', '.pyo', '.tgz', '.tiff', '.zip',
      ],
      'grammar': 'binary',
    },
    'c': {
      'ext': ['.c'],
      'grammar': 'c',
    },
    'cpp': {
      'ext': [
        '.cc', '.cpp', '.cxx', '.c++', '.hpp', '.hxx', '.h++', '.inc',
        '.h'  # Hmm, some source uses .h for cpp headers.
      ],
      'grammar': 'cpp',
    },
    'css': {
      'ext': ['.css', '_css.html'],
      'grammar': 'css',
    },
    'dart': {
      'ext': ['.dart',],
      'grammar': 'dart',
    },
    'golang': {
      'ext': ['.go',],
      'grammar': 'golang',
    },
    'grd': {
      'ext': ['.grd', '.grdp'],
      'grammar': 'grd',
    },
    'html': {
      'ext': ['.htm', '.html'],
      'grammar': 'html',
    },
    'java': {
      'ext': ['.java',],
      'grammar': 'java',
    },
    'js': {
      'ext': ['.json', '.js'],
      'grammar': 'js',
    },
    'md': {
      'ext': ['.md'],
      'grammar': 'md',
    },
    'python': {
      'ext': ['.py'],
      'grammar': 'py',
    },
    'rust': {
      'ext': ['.rust'],
      'grammar': 'rust',
    },
    'text': {
      'ext': ['.txt', ''],
        'grammar': 'text',
    },
  },
  'grammar': {
    # A grammar is
    # 'grammar_name': {
    #   'begin': None or regex,
    #   'continuation': None or string,
    #       Prefixed used when continuing to another line,
    #   'end': None or regex,
    #   'end_key': None or regex to determine dynamic end tag. For 'here
    #       documents' and c++ string literals.
    #   'error': None or list of string.
    #   'escaped': None or regex,
    #   'indent': None or string,
    #   'numbers': None or list of string,
    #   'keywords': None or list of string. Matches whole words only (wraps
    #       values in \b).
    #   'single_line': Boolean, Whether entire grammar must be on a single line,
    #   'special': None or list of string.
    #   'type': text or binary. default: text.
    #   'contains': other grammars that may be contained within this grammar.
    # }
    # The entries for 'error', 'keywords', and 'special' are very similar.
    # Other than 'keywords' being wrapped in \b markers, the difference between
    # them is just how they are drawn (color and style).
    '_pre': {
      'contains': ['_pre_selection'],
      'spelling': False,
    },
    '_pre_selection': {
      'begin': r'-->',
      'end': r'<--',
      'spelling': False,
    },
    'bash': {
      'indent': '  ',
      'keywords': [
        'basename', 'break', 'case', 'chmod', 'continue', 'cp',
        'dirname', 'do', 'done', 'echo', 'else', 'exit',
        'fi', 'find', 'if', 'for',
        'ln', 'mkdir', 'read', 'return', 'rm', 'sleep', 'switch', 'then',
        'while',
      ],
      'contains': ['c_string1', 'c_string2', 'pound_comment'],
    },
    'binary': {
      'spelling': False,
      'type': 'binary',
    },
    'c': {
      'indent': '  ',
      'keywords': __c_keywords,
      'types': __c_primitive_types,
      'contains': ['cpp_block_comment', 'cpp_line_comment', 'c_preprocessor',
        'c_string1', 'c_string2'],
    },
    'cpp': {
      'indent': '  ',
      'keywords': __c_keywords + [
        'auto', 'catch', 'class', 'constexpr', 'delete', 'explicit', 'false',
        'mutable', 'namespace', 'new', 'nullptr', 'override',
        'private', 'protected', 'public',
        'template', 'this', 'throw', 'true', 'typename',
      ],
      'namespaces': [
        '::', 'std::',
      ],
      'types': __c_primitive_types,
      'contains': ['cpp_block_comment', 'cpp_line_comment', 'c_preprocessor',
        'cpp_string_literal', 'c_string1', 'c_string2'],
    },
    'cpp_block_comment': {
      'begin': r'/\*',
      'continuation': ' * ',
      'end': r'\*/',
      'indent': '  ',
      'keywords': [],
      'special': [
        r'\bNOTE:', _todo, __chrome_extension, __sha_1,
      ],
    },
    'cpp_line_comment': {
      'begin': '//',
      'continuation': '// ',
      'end': r'(?<!\\)\n',
      'indent': '  ',
      'keywords': [],
      'special': [
        r'\bNOTE:', _todo, __chrome_extension, __sha_1,
      ],
    },
    'c_preprocessor': {
      'begin': r'^#',
      'end': r'(?<!\\)\n',
      'indent': '  ',
      'special': [
        r'^\s*#\s*?define\b', r'^\s*#\s*?defined\b', r'^\s*#\s*?elif\b',
        r'^\s*#\s*?else\b',
        r'^\s*#\s*?endif\b', r'^\s*#\s*?if\b', r'^\s*#\s*ifdef\b',
        r'^\s*#\s*?elif\b',
        r'^\s*#\s*?ifndef\b', r'^\s*#\s*?include\b', r'^\s*#\s*?undef\b',
      ],
      #'contains': ['file_path_quoted', 'file_path_bracketed'],
    },
    'c_raw_string1': {
      'begin': "[uU]?[rR]'",
      'end': "'",
      'escaped': r"\\'",
      'indent': '  ',
      'single_line': True,
      'special': __special_string_escapes + [r"\\\\"],
    },
    'c_raw_string2': {
      'begin': '[uU]?[rR]"',
      'end': '"',
      'escaped': r'\\"',
      'indent': '  ',
      'single_line': True,
      'special': __special_string_escapes + [r"\\\\"],
    },
    'cpp_string_literal': {
      'begin': r'R"',
      # TODO(dschuyler): backslash and whitespace are invalid in the |end_key|.
      'end_key': r'''([^(]*)\(''',
      'end': r'\)\0"',
      'single_line': False,
    },
    'c_string1': {
      'begin': "'(?!'')",
      'end': r"'",
      'escaped': r"\\'",
      'indent': '  ',
      'special': __special_string_escapes + [r"\\'"],
      'single_line': True,
    },
    'c_string2': {
      'begin': '"(?!"")',
      'end': r'"',
      'escaped': r'\\"',
      'indent': '  ',
      'special': __special_string_escapes + [r'\\"'],
      'single_line': True,
    },
    'css': {
      'begin': '<style',
      'end': '</style>',
      'indent': '  ',
      'keywords': [
        'host', 'slotted',
      ],
      'special': [
        r'#[\w-]+'
      ],
      'contains': ['cpp_block_comment', 'css_block'],
    },
    'css_block': {
      'begin': r'\{',
      'end': r'\}',
      'indent': '  ',
      'keywords': [
        'background-color', 'color', 'display',
        'font-family', 'font-size',
        'height', 'max-height', 'min-height',
        'width', 'max-width', 'min-width',
      ],
      'special': [
        r'@apply\b',
      ],
      'contains': ['cpp_block_comment', 'css_value'],
    },
    'css_value': {
      'begin': ':',
      'end': ';',
      'error': [
        r'#(?:[^;]{1,2}|[^;]{5}|[^;]{7}|[^;]{9,})\b',
      ],
      'indent': '  ',
      'keywords': [
        'absolute', 'attr', 'block', 'border-box', 'calc', 'center', 'default',
        'ease', 'hidden',
        'inherit', 'left', 'none',
        'px', 'rgb', 'rgba', 'right', 'rotate[XYZ]?', 'scale[XYZ]?', 'solid',
        'transform', 'translate[XYZ]?', 'transparent', 'var',
      ],
      'special': [
        r'@apply\b', r'\d+deg\b', r'\d+em\b', r'\d+px\b', r'\d+rem\b',
        r'#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})'
      ],
      'contains': ['cpp_block_comment',],
    },
    'dart': {
      'indent': '  ',
      'keywords': [
        'abstract', 'as', 'assert', 'async', 'async', 'await', 'break', 'case',
        'catch', 'class', 'const', 'continue', 'covariant', 'default',
        'deferred', 'do', 'dynamic', 'else', 'enum', 'export', 'extends',
        'external', 'factory', 'false', 'final', 'finally', 'for', 'get', 'if',
        'implements', 'import', 'in', 'interface', 'is', 'library', 'mixin',
        'new', 'null', 'operator', 'part', 'rethrow', 'return', 'set', 'static',
        'super', 'switch', 'sync', 'this', 'throw', 'true', 'try', 'typedef',
        'var', 'void', 'while', 'with', 'yield',
      ],
      'special': [
        r'@override',
      ],
      'contains': [
        # This list is carefully ordered. Don't sort it.
        'py_string1', 'py_string2', 'py_raw_string1', 'py_raw_string2',
        'c_raw_string1', 'c_raw_string2', 'c_string1', 'c_string2',
        'cpp_line_comment',
      ],
    },
    'doc_block_comment': {
      'begin': r'/\*\*',
      'continuation': ' * ',
      'end': r'\*/',
      'indent': '  ',
      'keywords': [],
      'special': [
        r'@param\b', r'@private\b', r'@protected\b', r'@type\b', r'@typedef\b',
        r'@return\b', r'\bNOTE:', _todo,
      ],
      'types': ['Array', 'boolean', 'string', 'Object'],
    },
    'error': {
      'indent': '  ',
      'spelling': False,
    },
    'golang': {
      'indent': '  ',
      'keywords': [
        'break', 'case', 'chan', 'const', 'continue', 'default', 'defer',
        'else', 'fallthrough', 'for', 'func', 'go', 'goto', 'if', 'import',
        'interface', 'map', 'package', 'range', 'return', 'select', 'struct',
        'switch', 'type', 'var',
      ],
      'special': [
        #r'(?<!\w)__.*?__(?!\w)',
      ],
      'contains': [
      ],
    },
    'grd': {
      'keywords': [ 'flattenhtml', 'allowexternalscript' ],
    },
    'html': {
      'begin': '<html>',
      'end': app.regex.kNonMatchingRegex,
      'errors': ['</br>', '</hr>', '</img>', '</input>',],
      'indent': '  ',
      'keywords': [
        #'body', 'button', 'div', 'head', 'html', 'href', 'img', 'input',
        #'script', 'select', 'span', 'style',
      ],
      'special': [
        r'&.{1,5}?;', '<if\s+expr="[^"]*[^>]*>', '</if>',
      ],
      'contains': [
        'quoted_string1', 'quoted_string2', 'css', 'html_block_comment', 'js',
        'html_element', 'html_element_end',
      ],
    },
    'html_block_comment': {
      'begin': '<!--',
      'end': '-->',
      'indent': '  ',
    },
    'html_element': {
      'begin': r'<[\w-]+',  # The '-' is used by Polymer.
      'contains': ['html_element_attribute',],
      'end': '>',
      'special': [r'\w+',],
    },
    'html_element_attribute': {
      'begin': '\\??="',
      'end': '"',
    },
    'html_element_end': {
      'begin': r'</\w+',
      'end': '>',
    },
    'java': {
      'indent': '  ',
      'keywords': __common_keywords + [
        'case', 'class', 'default', 'do', 'false',
        'interface',
        'switch', 'this', 'true',
      ],
      'contains': ['c_string1', 'c_string2', 'cpp_block_comment',
          'cpp_line_comment'],
    },
    'js': {
      'begin': '<script',
      'end': '</script>',
      'indent': '  ',
      'keywords': [
        'arguments', 'break', 'case', 'class', 'const', 'continue',
        'default', 'delete', 'document', 'else', 'false', 'for', 'function',
        'if', 'instanceof', 'let', 'of', 'return', 'static', 'switch', 'super',
        'this', 'true', 'undefined', 'var', 'while', 'yield',
       ],
      'special': [
        '\bsetTimeout\b', '\brequestCallback\b', '\bconsole\b', '\bwindow\b',
      ],
      'contains': [
        'c_string1', 'c_string2', 'doc_block_comment', 'cpp_block_comment',
        'cpp_line_comment', 'regex_string', 'js_string',
      ],
    },
    'js_string': {
      'begin': r"`",
      'end': r"`",
      'escaped': r"\\`",
      'indent': '  ',
      'special': __special_string_escapes + [r"\\`", r"(?<!\\)\$\{[^}]*\}"],
      'single_line': False,
    },
    'keyword': {
      'indent': '  ',
      'spelling': False,
    },
    'md': {
      'indent': '  ',
      'keywords': [],
      #'special': [r'\[[^]]+\]\([^)]+\)'],
      'contains': [
        'md_link',
        #'quoted_string1', 'quoted_string2'
      ],
    },
    'md_link': {
      'begin': "\[",
      'end': "\]",
      'escaped': r"\\\]",
      'indent': '  ',
    },
    'none': {
      'spelling': False,
    },
    'py': {
      'indent': '  ',
      'keywords': __common_keywords + [
        'and', 'as', 'assert', 'class',
        'def', 'del', 'dict', 'elif', 'except',
        'False', 'finally', 'from',
        'global', 'import', 'in', 'is', 'len', 'list',
        'None', 'not',
        'or', 'pass',
        'raise', 'range',
        'self',
        'True', 'try', 'tuple',
        'until', 'with', 'yield',
      ],
      'namespaces': [
        'os\.', 'os\.path\.', 'sys\.', 'traceback\.', 're\.',
      ],
      'special': [
        #r'(?<!\w)__.*?__(?!\w)',
      ],
      'types': [
        'Exception',
      ],
      'contains': [
        # This list is carefully ordered. Don't sort it.
        'py_string1', 'py_string2', 'py_raw_string1', 'py_raw_string2',
        'c_raw_string1', 'c_raw_string2', 'c_string1', 'c_string2',
        'pound_comment',
      ],
    },
    'pound_comment': {
      'begin': '#',
      'continuation': '# ',
      'end': r'\n',
      'indent': '  ',
      'keywords': [],
      'special': [
        r'\bNOTE:', _todo,
      ],
    },
    'py_raw_string1': {
      'begin': "[uU]?[rR]'''",
      'end': "'''",
      'escaped': r"\\'",
      'indent': '  ',
      #'special': [r"\''?'?$"],
    },
    'py_raw_string2': {
      'begin': '[uU]?[rR]"""',
      'end': '"""',
      'escaped': r'\\"',
      'indent': '  ',
      #'special': [r'\\"'],
    },
    'py_string1': {
      'begin': "[uU]?'''",
      'end': "'''",
      'escaped': r"\\'",
      #'indent': '  ',
      'special': __special_string_escapes + [r"\\'"],
    },
    'py_string2': {
      'begin': '[uU]?"""',
      'end': '"""',
      'escaped': r'\\"',
      #'indent': '  ',
      'special': __special_string_escapes + [r'\\"'],
    },
    'quoted_string1': {
      # This is not a programming string, there are no escape chars.
      'begin': "'",
      'end': "'",
    },
    'quoted_string2': {
      # This is not a programming string, there are no escape chars.
      'begin': '"',
      'end': '"',
    },
    'regex_string': {
      'begin': r"(?<=[\n=:;([{,])(?:\s*)/(?![/*])",
      'end': "/",
      'escaped': r'\\.',
      'indent': '  ',
      'special': __special_string_escapes + [r"\\/"],
      'single_line': True,
    },
    'rust': {
      'indent': '  ',
      'keywords': [
        'abstract', 'alignof', 'as', 'become', 'box', 'break', 'const',
        'continue', 'crate', 'do', 'else', 'enum', 'extern', 'false', 'final',
        'fn', 'for', 'if', 'impl', 'in', 'let', 'loop', 'macro', 'match', 'mod',
        'move', 'mut', 'offsetof', 'override', 'priv', 'pub', 'pure', 'ref',
        'return', 'Self', 'self', 'sizeof', 'static', 'struct', 'super',
        'trait', 'true', 'type', 'typeof', 'unsafe', 'unsized', 'use',
        'virtual', 'where', 'while', 'yield',
      ],
      'special': [
        #r'(?<!\w)__.*?__(?!\w)',
      ],
      'contains': [
      ],
    },
    'special': {
      'indent': '  ',
      'spelling': False,
    },
    'text': {
      'special': [__sha_1,],
      'contains': ['quoted_string1', 'quoted_string2'],
    },
    'type': {
      'indent': '  ',
      'spelling': False,
    },
  },
  'palette': {
    # Note: index 0 of each palette is not set, it remains as the system entry.
    "test": {
      # Same foreground color in all 256 slots.
      "foregroundIndexes": [18] * 256,
      # Separate background color in every slot.
      "backgroundIndexes": [i for i in range(0, 256)],
    },
    "dark": {
      # This series repeats 8 times (32 * 8 = 256).
      "foregroundIndexes": [
        14,  202,  39,   39,   39,   39,  39,  39,
        39,  39, 39, 39,   12, 13, 14,  15,
        202, 14, 14, 202, 202,  202, 22, 23,  24, 25, 26, 27,   28, 29, 30,  57,
      ] * 8,
      # Each of the foreground colors repeat 8 times (32 * 8 = 256).
      "backgroundIndexes":
        [232] * 32 + [229] * 32 +   [6] * 32 + [221] * 32 +
        [245] * 32 + [244] * 32 + [243] * 32 + [225] * 32,
    },
    "default8": {
      # With only 8 colors, make a custom pair for each slot.
      "foregroundIndexes": [0, 4, 2, 3, 4, 5, 6, 0],
      "backgroundIndexes": [1, 7, 7, 7, 7, 7, 7, 7],
    },
    "default": {
      # This series repeats 8 times (32 * 8 = 256).
      "foregroundIndexes": [
        18,  1,  2,   3,   4,   5,  6,  7,   8,  9, 10, 11,   12, 13, 14,  15,
        94, 134, 0, 240, 138,  21, 22, 23,  24, 25, 26, 27,   28, 29, 30,  57,
      ] * 8,
      # Each of the foreground colors repeat 8 times (32 * 8 = 256).
      "backgroundIndexes":
        [231] * 32 + [229] * 32 +  [14] * 32 + [221] * 32 +
        [255] * 32 + [254] * 32 + [253] * 32 + [225] * 32,
    },
  },
  'status': {
    'showTips': False,
  },
  'userData': {
    'homePath': os.path.expanduser('~/.ci_edit'),
    'historyPath': os.path.join(os.path.expanduser('~/.ci_edit'),
        'history.dat'),
  },
}
