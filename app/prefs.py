# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.log
import sys
import traceback


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
      'end': None,
      'escape': '\\',
      'indent': '  ',
      'keywords': [
        'break', 'case', 'continue', 'do', 'done', 'exit', 'fi', 'if', 'for',
        'return', 'switch', 'while',
      ],
      'contains': ['c_string1', 'c_string2', 'pound_comment'],
    },
    'binary': {
      'end': None,
      'type': 'binary',
    },
    'c': {
      'begin': None,
      'end': None,
      'escape': None,
      'indent': '  ',
      'keywords': __c_keywords,
      'types': __c_primitive_types,
      'contains': ['cpp_block_comment', 'cpp_line_comment', 'c_preprocessor',
        'c_string1', 'c_string2', 'hex_number'],
    },
    'cpp': {
      'begin': None,
      'end': None,
      'escape': None,
      'indent': '  ',
      'keywords': __c_keywords + [
        'auto', 'catch', 'class', 'const',
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
      'begin': '/\\*',
      'continued': ' * ',
      'end': '\\*/',
      'escape': None,
      'indent': '  ',
      'keywords': [],
      'nestable': False,
    },
    'cpp_line_comment': {
      'begin': '//',
      'continued': '// ',
      'end': '\n',
      'escape': '\\\n',
      'indent': '  ',
      'keywords': [],
      'nestable': False,
    },
    'c_preprocessor': {
      'begin': '#',
      'end': '\n',
      'escape': '\\\n',
      'indent': '  ',
      'keywords': [
        '#\s*?define', '#\s*?defined', '#\s*?elif', '#\s*?endif',
        '#\s*?if', '#\s*?ifdef', '#\s*?ifndef', '#\s*?include',
        '#\s*?undef',
      ],
      'contains': ['file_path_quoted', 'file_path_bracketed'],
    },
    'c_string1': {
      'begin': "'",
      'end': "'",
      'escape': '\\',
      'indent': '  ',
      'keywords': [
        '\\b', '\\f', '\\n', '\\r', '\\0..',
      ],
      'single_line': True,
    },
    'c_string2': {
      'begin': '"',
      'end': '"',
      'escape': '\\',
      'indent': '  ',
      'keywords': [
        '\\b', '\\f', '\\n', '\\r', '\\0..',
      ],
      'single_line': True,
    },
    'css': {
      'begin': '<style',
      'end': '</style>',
      'escape': None,
      'indent': '  ',
      'keywords': [],
      'contains': ['cpp_block_comment'],
    },
    'html': {
      'escape': None,
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
      'escape': None,
      'indent': '  ',
      'keywords': [],
      'prefix': '',
    },
    'java': {
      'begin': None,
      'end': None,
      'escape': None,
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
      'escape': None,
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
      'escape': None,
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
      'end': '\n',
      'escape': None,
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
    'text': {
      'begin': None,
      'end': None,
      'escape': None,
      'indent': '  ',
      'keywords': [],
      'contains': ['quoted_string'],
    },
  },
}


class PrefsUtil:
  def __init__(self, prefs):
    self.grammars = {}
    if 0:
      app.log.info('grammars', prefs['grammar'])
    for k,v in prefs['grammar'].items():
      self.grammars[k] = v
    if 0:
      app.log.info('grammars')
      for k,v in self.grammars.items():
        app.log.info('  ', k, ':', v)
    self.extensions = {}
    self.filetypes = {}
    for k,v in prefs['filetype'].items():
      for ext in v['ext']:
        self.extensions[ext] = v.get('grammar')
      self.filetypes[k] = v
    if 0:
      app.log.info('extensions')
      for k,v in self.extensions.items():
        app.log.info('  ', k, ':', v)
      app.log.info('filetypes')
      for k,v in self.filetypes.items():
        app.log.info('  ', k, ':', v)

  def getGrammar(self, fileExtension):
    filetype = self.extensions.get(fileExtension)
    return self.grammars.get(filetype)

if 1:
  try:
    util = PrefsUtil(prefs)
  except Exception, e:
    errorType, value, tb = sys.exc_info()
    out = traceback.format_exception(errorType, value, tb)
    for i in out:
      app.log.error(i[:-1])
    app.log.flush()


