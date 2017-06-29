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

import app.log
import curses
import re
import sys
import time
import traceback

importStartTime = time.time()

commentColorIndex = 2
defaultColorIndex = 18
foundColorIndex = 32
keywordsColorIndex = 21
selectedColor = 64 # Active find is a selection.
specialsColorIndex = 20
stringColorIndex = 5
outsideOfBufferColorIndex = 211

kNonMatchingRegex = r'^\b$'
kReNonMatching = re.compile(kNonMatchingRegex)

def joinReList(reList):
  return r"("+r")|(".join(reList)+r")"

def joinReWordList(reList):
  return r"(\b"+r"\b)|(\b".join(reList)+r"\b)"

__common_keywords = [
  'break', 'continue', 'else',
  'for', 'if', 'return', 'while',
]

__c_keywords = __common_keywords + [
  'case', 'const', 'default', 'do',
  'goto', 'sizeof', 'static', 'struct', 'switch',
  'typedef',
]

__c_primitive_types = [
  'bool', 'char', 'double', 'float', 'int', 'long', 'signed', 'short',
  'unsigned',
  'int8_t', 'int16_t', 'int32_t', 'int64_t',
  'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
  'void', 'wchar_t',
]

# Trivia: all English contractions except 'sup, 'tis and 'twas will
# match this regex (with re.I):  [adegIlnotuwy]'[acdmlsrtv]
# The prefix part of that is used in the expression below to identify
# English contractions.
__english_contraction = \
    r"(\"(\\\"|[^\"])*?\")|(?<![adegIlnotuwy])('(\\\'|[^'])*?')"

__special_string_escapes = [
  r'\\\\', r'\\b', r'\\f', r'\\n', r'\\r', r'\\t', r'\\v', r'\\0[0-7]{0,3}',
]

__common_numbers = [
  r'[-+]?[0-9]*\.[0-9]+(?:[eE][+-][0-9]+)?[fF]?(?!\w)',
  r'[-+]?[0-9]+(?:\.[0-9]*(?:[eE][+-][0-9]+)?)?[fF]?(?!\w)',
  r'[-+]?[0-9]+(?:[uUlL][lL]?[lL]?)?(?!\w)',
  r'0[xX][^A-Fa-f0-9]+(?:[uUlL][lL]?[lL]?)?(?!\w)',
]

numbersRe = re.compile(joinReList(__common_numbers))

def numberTest(str, expectRegs):
  sre = numbersRe.search(str)
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

# These prefs are not fully working.
prefs = {
  'colors': {
    '_pre_selection': stringColorIndex,
    'default': defaultColorIndex,
    'text': defaultColorIndex,
    'keywords': keywordsColorIndex,
    'specials': specialsColorIndex,
    'c': defaultColorIndex,
    'cpp_block_comment': commentColorIndex,
    'cpp_line_comment': commentColorIndex,
    'c_preprocessor': 1,
    'c_raw_string1': stringColorIndex,
    'c_raw_string2': stringColorIndex,
    'c_string1': stringColorIndex,
    'c_string2': stringColorIndex,
    'regex_string': stringColorIndex,
    'doc_block_comment': commentColorIndex,
    'html_block_comment': commentColorIndex,
    'pound_comment': commentColorIndex,
    'py_raw_string1': stringColorIndex,
    'py_raw_string2': stringColorIndex,
    'py_string1': stringColorIndex,
    'py_string2': stringColorIndex,
    'quoted_string2': stringColorIndex,
  },
  'editor': {
    'captiveCursor': False,
    'showLineNumbers': True,
    'showStatusLine': True,
    'showTopInfo': True,
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
      'ext': ['.c', '.h'],
      'grammar': 'c',
    },
    'cpp': {
      'ext': ['.cc', '.cpp', '.cxx', '.c++', '.hpp', '.hxx', '.h++', '.inc'],
      'grammar': 'cpp',
    },
    'css': {
      'ext': ['.css', '_css.html'],
      'grammar': 'css',
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
    'text': {
      'ext': ['.txt', ''],
        'grammar': 'text',
    },
  },
  'grammar': {
    # A grammar is
    # 'grammar_name': {
    #   'begin': None or regex,
    #   'continued': None or string,
    #       Prefixed used when continuing to another line,
    #   'end': None or regex,
    #   'escaped': None or regex,
    #   'indent': None or string,
    #   'keywords': None or list of string,
    #   'single_line': Boolean, Whether entire grammar must be on a single line,
    #   'type': text or binary. default: text.
    #   'contains': other grammars that may be contained within this grammar.
    # }
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
        'break', 'case', 'continue', 'do', 'done', 'exit', 'fi', 'if', 'for',
        'return', 'switch', 'then', 'while',
      ],
      'contains': ['c_string1', 'c_string2', 'pound_comment'],
    },
    'binary': {
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
        'auto', 'catch', 'class', 'constexpr', 'false',
        'namespace', 'nullptr',
        'private', 'protected', 'public',
        'template', 'this', 'throw', 'true', 'typename',
      ],
      'namespaces': [
        '::', 'std::',
      ],
      'types': __c_primitive_types,
      'contains': ['cpp_block_comment', 'cpp_line_comment', 'c_preprocessor',
        'c_string1', 'c_string2'],
    },
    'cpp_block_comment': {
      'begin': r'/\*',
      'continued': ' * ',
      'end': r'\*/',
      'indent': '  ',
      'keywords': [],
      'special': [
        r'\bNOTE:', r'TODO\([^)]+\)',
      ],
    },
    'cpp_line_comment': {
      'begin': '//',
      'continued': '// ',
      'end': r'(?<!\\)\n',
      'indent': '  ',
      'keywords': [],
      'special': [
        r'\bNOTE:', r'TODO\([^)]+\)',
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
        r'^\s*#\s*?ifndef\b', r'^\s*#\s*?include\b', r'^\s*#\s*?undef\b',
      ],
      #'contains': ['file_path_quoted', 'file_path_bracketed'],
    },
    'c_raw_string1': {
      'begin': "[uU]?[rR]'",
      'end': "'",
      'escaped': r"\\.",
      'indent': '  ',
      'single_line': True,
    },
    'c_raw_string2': {
      'begin': '[uU]?[rR]"',
      'end': '"',
      'escaped': r'\\.',
      'indent': '  ',
      'single_line': True,
    },
    'c_string1': {
      'begin': "'(?!'')",
      'end': r"'",
      'escaped': r'\\.',
      'indent': '  ',
      'special': __special_string_escapes + [r"\\'"],
      'single_line': True,
    },
    'c_string2': {
      'begin': '"(?!"")',
      'end': r'"',
      'escaped': r'\\.',
      'indent': '  ',
      'special': __special_string_escapes + [r'\\"'],
      'single_line': True,
    },
    'css': {
      'begin': '<style',
      'end': '</style>',
      'indent': '  ',
      'keywords': [
        'absolute', 'attr', 'block', 'border-box', 'calc', 'center', 'default',
        'ease', 'hidden',
        'inherit', 'left', 'none',
        'px', 'rgb', 'rgba', 'right', 'rotate[XYZ]?', 'scale[XYZ]?', 'solid',
        'transform', 'translate[XYZ]?', 'transparent', 'var',
      ],
      'special': [
        r'@apply\b', r'\d+deg\b', r'\d+em\b', r'\d+px\b',
        r'\d+rem\b', r'[\w-]+:',
      ],
      'contains': ['cpp_block_comment'],
    },
    'doc_block_comment': {
      'begin': r'/\*\*',
      'continued': ' * ',
      'end': r'\*/',
      'indent': '  ',
      'keywords': [],
      'special': [
        r'@param\b', r'@private\b', r'@protected\b', r'@type\b', r'@typedef\b',
        r'@return\b', r'\bNOTE:', r'TODO\([^)]+\)',
      ],
      'types': ['Array', 'boolean', 'string', 'Object'],
    },
    'html': {
      'indent': '  ',
      'keywords': [
        'body', 'button', 'div', 'head', 'html', 'href', 'img', 'input',
        'script', 'select', 'span', 'style',
      ],
      'special': [r'&.{1,5}?;',],
      'contains': [
        'quoted_string1', 'quoted_string2', 'css', 'html_block_comment', 'js',
      ],
    },
    'html_block_comment': {
      'begin': '<!--',
      'end': '-->',
      'indent': '  ',
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
        'arguments', 'break', 'case', 'class', 'continue', 'default',
        'document', 'else',
        'false', 'for', 'function', 'if', 'let', 'return',
        'switch', 'this', 'true', 'var', 'while',
      ],
      'special': [
        '\bsetTimeout\b', '\brequestCallback\b', '\bconsole\b', '\bwindow\b',
      ],
      'contains': [
        'c_string1', 'c_string2', 'doc_block_comment', 'cpp_block_comment',
        'cpp_line_comment', 'regex_string',
      ],
    },
    'md': {
      'indent': '  ',
      'keywords': [],
      'special': [r'\[[^]]+\]\([^)]+\)'],
      'contains': ['quoted_string1', 'quoted_string2'],
    },
    'none': {
      'spelling': False,
    },
    'py': {
      'indent': '  ',
      'keywords': __common_keywords + [
        'and', 'as', 'assert', 'class',
        'def', 'dict', 'elif', 'except',
        'False', 'from',
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
        r'\bNOTE:', r'TODO\([^)]+\)',
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
      'escaped': r'\\.',
      'indent': '  ',
      'special': __special_string_escapes + [r"\\'"],
    },
    'py_string2': {
      'begin': '[uU]?"""',
      'end': '"""',
      'escaped': r'\\.',
      'indent': '  ',
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
    'text': {
      'indent': '  ',
      'contains': ['quoted_string1', 'quoted_string2'],
    },
  },
}


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
  for k,v in prefs['grammar'].items():
    # Colors.
    v['colorIndex'] = prefs['colors'].get(k, defaultColorIndex)
    v['color'] = curses.color_pair(v['colorIndex'])
    v['keywordsColor'] = curses.color_pair(
        prefs['colors'].get(k+'_keyword_color', keywordsColorIndex))
    v['specialsColor'] = curses.color_pair(
        prefs['colors'].get(k+'_special_color', specialsColorIndex))
  app.log.info('prefs init')

def getGrammar(fileExtension):
  if fileExtension is None:
    return grammars.get('none')
  fileType = extensions.get(fileExtension, 'text')
  return grammars.get(fileType)

app.log.startup('prefs.py import time', time.time() - importStartTime)

