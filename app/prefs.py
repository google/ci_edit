# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.log
import re
import sys
import time
import traceback

importStartTime = time.time()

def joinReList(reList):
  return r"("+r")|(".join(reList)+r")"

__common_keywords = [
  'break', 'continue', 'do', 'else',
  'for', 'if', 'return', 'while',
]

__c_keywords = __common_keywords + [
  'case', 'const', 'double',
  'signed', 'sizeof', 'static', 'struct', 'switch',
  'typedef', 'unsigned',
]

__c_primitive_types = [
  'char', 'double', 'float', 'int', 'long', 'signed', 'short', 'unsigned',
  'int8_t', 'int16_t', 'int32_t', 'int64_t',
  'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
  'void', 'wchar_t',
]

__common_numbers = [
  #r'[-+]?[0-9]*\.?',
  r'[-+]?[0-9]*\.[0-9]+(?:[eE][+-][0-9]+)?[fF]?(?!\w)',
  r'[-+]?[0-9]+(?:\.[0-9]*(?:[eE][+-][0-9]+)?)?[fF]?(?!\w)',
  #r'[-+]?[0-9]+(?:\.[0-9]*(?:[eE][+-][0-9]+)?[fF]?)?',
  r'0[xX][^A-Fa-f0-0]+(?:[uUlL][lL]?[lL]?)?', # hexidecimal
  #r'[0-9]+', # decimal
  #r'[0-9]+\.[0-9]+', # float
  #r'[0-9]+\.', # float
  #r'\.[0-9]+', # float
  #r'[0-9]+\.[0-9]+[eE][-+][0-9]+', # exponential
  #r'[0-9]+\.[eE][-+][0-9]+', # exponential
  #r'\.[0-9]+[eE][-+][0-9]+', # exponential
  #r'0[^0-7]+', # octal
  #r'0[xX][^A-Fa-f0-0]+', # hexidecimal
]

numbersRe = re.compile(joinReList(__common_numbers))

def numberTest(str, expectRegs=True):
  sre = numbersRe.search(str)
  if sre:
    app.log.startup('asdf', str, sre.regs, sre.groups())
  else:
    app.log.startup('asdf', str, sre)


app.log.startup('asdf', numbersRe.pattern)
numberTest('.', False)
numberTest('2')
numberTest(' 2 ')
numberTest('242.2')
numberTest('.2')
numberTest('2.')
numberTest('.2a', False)
numberTest('2.a')
numberTest('+0.2e-15')
numberTest('02factor', False)
numberTest('02f')


# These prefs are not fully working.
prefs = {
  'filetype': {
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
    'python': {
      'ext': ['.py'],
      'grammar': 'py',
    },
  },
  'grammar': {
    # A grammar is
    # 'grammar_name': {
    #   'begin': None or string,
    #   'continued': None or string, Prefixed used when continuing to another line,
    #   'end': None or string,
    #   'escape': None or string,
    #   'indent': None or string,
    #   'keywords': None or list of string,
    #   'single_line': Boolean, Whether entire grammar must be on a single line,
    #   'type': text or binary. default: text.
    #   'contains': other grammars that may be contained within this grammar.
    # }
    'bash': {
      'escape': '\\',
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
        'c_string1', 'c_string2', 'hex_number'],
    },
    'cpp': {
      'indent': '  ',
      'keywords': __c_keywords + [
        'auto', 'catch', 'class', 'constexpr',
        'namespace', 'nullptr',
        'private', 'protected', 'public',
        'template', 'this', 'throw', 'typename',
      ],
      'namespaces': [
        '::', 'std::',
      ],
      'types': __c_primitive_types,
      'contains': ['cpp_block_comment', 'cpp_line_comment', 'c_preprocessor',
        'c_string1', 'c_string2', 'hex_number'],
    },
    'cpp_block_comment': {
      'begin': r'/\*',
      'continued': ' * ',
      'end': r'\*/',
      'indent': '  ',
      'keywords': [],
      'nestable': False,
    },
    'cpp_line_comment': {
      'begin': '//',
      'continued': '// ',
      'end': r'(?<!\\)\n',
      'indent': '  ',
      'keywords': [],
      'nestable': False,
    },
    'c_preprocessor': {
      'begin': '#',
      'end': r'\n',
      'escape': r'\\\n',
      'indent': '  ',
      'keywords': [
        '#\s*?define', '#\s*?defined', '#\s*?elif', '#\s*?endif',
        '#\s*?if', '#\s*?ifdef', '#\s*?ifndef', '#\s*?include',
        '#\s*?undef',
      ],
      #'contains': ['file_path_quoted', 'file_path_bracketed'],
    },
    'c_string1': {
      'begin': "'",
      'end': "'",
      'escape': '\\',
      'indent': '  ',
      'keywords': [
        r'\b', r'\f', r'\n', r'\r', r'\t', r'\v', r'\0..',
      ],
      'single_line': True,
    },
    'c_string2': {
      'begin': '"',
      'end': '"',
      'escape': '\\',
      'indent': '  ',
      'keywords': [
        r'\b', r'\f', r'\n', r'\r', r'\t', r'\v', r'\0..',
      ],
      'single_line': True,
    },
    'css': {
      'begin': '<style',
      'end': '</style>',
      'indent': '  ',
      'keywords': [],
      'contains': ['cpp_block_comment'],
    },
    'html': {
      'indent': '  ',
      'keywords': [
        'a', 'b', 'body', 'button', 'div', 'head', 'html', 'img', 'input',
        'select', 'span',
      ],
      'contains': ['c_string1', 'c_string2', 'css', 'html_block_comment', 'js'],
    },
    'hex_number': {
      'begin': '0x',
      'end': '[^0-9a-fA-F]',
    },
    'html_block_comment': {
      'begin': '<!--',
      'end': '-->',
      'indent': '  ',
    },
    'java': {
      'indent': '  ',
      'keywords': __common_keywords + [
        'case', 'false',
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
        'arguments', 'break', 'case', 'continue',
        'false', 'for', 'function', 'if', 'return',
        'switch', 'this', 'true', 'while',
      ],
      'contains': ['c_string1', 'c_string2', 'cpp_block_comment',
          'cpp_line_comment'],
    },
    'md': {
      'indent': '  ',
      'keywords': [],
    },
    'number': {
      'begin': '[1-9]',
      'end': '[^0-9]',
    },
    'octal_number': {
      'begin': '0',
      'end': '[^0-7]',
    },
    'py': {
      'escape': '\\',
      'indent': '  ',
      'keywords': __common_keywords + [
        'and', 'as', 'assert', 'class',
        'def', 'dict', 'elif', 'except',
        'False', 'from', 'function',
        'global', 'import', 'in', 'is', 'len', 'list',
        'None', 'not',
        'or', 'pass',
        'raise', 'range',
        'self',
        'True', 'try', 'tuple',
        'until', 'yeild',
      ],
      'namespaces': [
        'os\.', 'os\.path\.', 'sys\.', 'traceback\.', 're\.',
      ],
      'types': [
        'Exception',
      ],
      'contains': ['c_string1', 'c_string2',
          'pound_comment', 'py_string1', 'py_string2'],
    },
    'pound_comment': {
      'begin': '#',
      'continuation': '# ',
      'end': '\\n',
      'indent': '  ',
      'keywords': [],
    },
    'py_string1': {
      'begin': "'''",
      'end': "'''",
      'escape': '\\',
      'indent': '  ',
      'keywords': [],
      'within': ['py'],
    },
    'py_string2': {
      'begin': '"""',
      'end': '"""',
      'escape': '\\',
      'indent': '  ',
      'keywords': [],
      'within': ['py'],
    },
    #'quoted_string1': {
    #  # This is not a programming string, there are no escape chars.
    #  'begin': "'",
    #  'end': "'",
    #},
    'quoted_string2': {
      # This is not a programming string, there are no escape chars.
      'begin': '"',
      'end': '"',
    },
    'text': {
      'indent': '  ',
      'keywords': [],
      'contains': ['quoted_string2'],
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
  matchGrammars = []
  markers = []
  if v.get('end'):
    markers.append(v['end'])
    matchGrammars.append(v)
  else:
    # Add a non-matchable placeholder.
    markers.append('^\\b$')
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
  regex = joinReList(markers)
  v['matchRe'] = re.compile(regex)
  v['matchGrammars'] = matchGrammars
# Reset the re.cache for user regexes.
re.purge()

extensions = {}
filetypes = {}
for k,v in prefs['filetype'].items():
  for ext in v['ext']:
    extensions[ext] = v.get('grammar')
  filetypes[k] = v
if 0:
  app.log.info('extensions')
  for k,v in extensions.items():
    app.log.info('  ', k, ':', v)
  app.log.info('filetypes')
  for k,v in filetypes.items():
    app.log.info('  ', k, ':', v)

def getGrammar(fileExtension):
  filetype = extensions.get(fileExtension)
  return grammars.get(filetype)

app.log.startup('prefs.py import time', time.time() - importStartTime)

