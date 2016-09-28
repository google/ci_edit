# These prefs are not fully working.
prefs = {
  'filetype': {
    'binary': {
      'ext': ['.exe', '.jpg', '.jpeg', '.png', '.o', '.obj', '.pyc', '.pyo'],
      'grammer': None,
      'type': 'binary',
    },
    'c': {
      'ext': ['.c', '.cc', '.cpp', '.h', '.hpp'],
      'grammer': 'c',
      'type': 'text',
    },
    'html': {
      'ext': ['.htm', '.html'],
      'grammer': 'html',
      'type': 'text',
    },
    'js': {
      'ext': ['.json', '.js'],
      'grammer': 'js',
      'type': 'text',
    },
    'python': {
      'ext': ['.py'],
      'grammer': 'py',
      'type': 'text',
    },
  },
  'grammer': {
    # A grammer is
    # 'grammer_name': {
    #   'begin': None or string,
    #   'continuation': None or string,
    #   'end': None or string,
    #   'escape': None or string,
    #   'indent': None or string,
    #   'keywords': None or list of string,
    #   'within': None or list of 'grammer_name',
    # }
    'c': {
      'begin': None,
      'end': None,
      'escape': None,
      'indent': '  ',
      'keywords': [
        'class', 'else', 'for', 'if', 'return', 'sizeof', 'static', 'struct',
        'typedef', 'while',
      ],
      'types': [
        'char', 'double', 'float', 'int', 'long', 'short', 'unsigned',
        'int8_t', 'int16_t', 'int32_t', 'int64_t',
        'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
      ],
      'within': None,
    },
    'c_block_comment': {
      'begin': '/*',
      'end': '*/',
      'escape': None,
      'indent': '  ',
      'keywords': [],
      'within': 'c',
    },
    'c_line_comment': {
      'begin': '//',
      'end': '\n',
      'escape': '\\',
      'indent': '  ',
      'keywords': [],
      'within': 'c',
    },
    'c_preprocessor': {
      'begin': '#',
      'end': '\n',
      'escape': None,
      'indent': '  ',
      'keywords': [
        'define', 'defined', 'endif', 'if', 'ifdef', 'ifndef', 'include', 'undef',
      ],
      'within': 'c',
    },
    'c_string1': {
      'begin': '"',
      'end': '"',
      'escape': '\\',
      'indent': '  ',
      'keywords': [],
      'within': 'c',
    },
    'css': {
      'begin': '<style',
      'end': '</style>',
      'escape': None,
      'indent': '  ',
      'keywords': [],
      'within': 'html',
    },
    'html': {
      'escape': None,
      'indent': '  ',
      'keywords': [
        'a', 'div', 'img', 'span',
      ],
    },
    'js': {
      'escape': None,
      'indent': '  ',
      'keywords': [
        'if', 'for', 'return', 'while',
      ],
      'within': 'html',
    },
    'md': {
      'escape': None,
      'indent': '  ',
      'keywords': [],
    },
    'py': {
      'escape': '\\',
      'indent': '  ',
      'keywords': [
        'and', 'as', 'class', 'def', 'from', 'if', 'import', 'for', 'or',
        'return', 'while',
      ],
      'within': None,
    },
    'py_comment': {
      'begin': '#',
      'continuation': '# ',
      'end': '\n',
      'escape': None,
      'indent': '  ',
      'keywords': [],
      'within': ['py'],
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
    },
  },
}