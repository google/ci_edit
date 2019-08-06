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
import sys

import app.log
import app.regex

_todo = r"TODO\([\S@.]+\)"

__common_keywords = [
    "break", "continue", "else", "for", "if", "return", "while"
]

__c_keywords = __common_keywords + [
    "case", "const", "default", "do", "enum", "goto", "sizeof", "static",
    "struct", "switch", "typedef"
]

__c_primitive_types = [
    "bool", "char", "double", "float", "int", "int8_t", "int16_t", "int32_t",
    "int64_t", "int_fast8_t", "int_fast16_t", "int_fast32_t", "int_fast64_t",
    "int_least8_t", "int_least16_t", "int_least32_t", "int_least64_t",
    "int_max_t", "int8_t", "int16_t", "int32_t", "int64_t", "intptr_t",
    "ptrdiff_t", "size_t", "long", "signed", "short", "uint8_t", "uint16_t",
    "uint32_t", "uint64_t", "uint_fast8_t", "uint_fast16_t", "uint_fast32_t",
    "uint_fast64_t", "uint_least8_t", "uint_least16_t", "uint_least32_t",
    "uint_least64_t", "uint_max_t", "uintptr_t", "unsigned", "void", "wchar_t"
]

if sys.version_info[0] == 2:
    # The Python2 re limits the number of named groups. Reduce the keywords
    # recognized.
    __cpp_keywords = [
        "auto", "break", "case", "catch", "class", "const", "constexpr",
        "continue", "default", "delete", "do", "else", "enum", "export",
        "false", "for", "friend", "if", "inline", "mutable", "namespace", "new",
        "noexcept", "nullptr", "override", "private", "protected", "public",
        "return", "sizeof", "static", "struct", "switch", "template", "this",
        "throw", "true", "typedef", "typename", "virtual", "while"
    ]
else:
    __cpp_keywords = [
        "alignas", "alignof", "and", "and_eq", "asm", "audit", "auto", "axiom",
        "bitand", "bitor", "break", "case", "catch", "class", "compl",
        "concept", "const", "const_cast", "consteval", "constexpr", "continue",
        "decltype", "default", "delete", "do", "dynamic_cast", "else", "enum",
        "explicit", "export", "extern", "false", "final", "for", "friend",
        "goto", "if", "inline", "mutable", "namespace", "new", "noexcept",
        "not", "not_eq", "nullptr", "operator", "or", "or_eq", "override",
        "private", "protected", "public", "register", "reinterpret_cast",
        "return", "sizeof", "static", "static_assert", "static_cast", "struct",
        "switch", "template", "this", "thread_local", "throw", "true",
        "typedef", "typename", "virtual", "volatile", "while", "xor", "xor_eq"
    ]

__chrome_extension = r"""\b[a-z]{32}\b"""
__sha_1 = r"""\b[a-z0-9]{40}\b"""

__special_string_escapes = [
    r"\\\\",
    r"\\b",
    r"\\f",
    r"\\n",
    r"\\r",
    r"\\t",
    r"\\v",
    r"\\0[0-7]{0,3}",
    #r"%#?-?[0-9]*\.?[0-9]*z?.",
    __chrome_extension,
    __sha_1,
]

color8 = {
    "_pre_selection": 1,
    "bracket": 1,
    "c": 0,
    "c_path_bracketed_file": 3,
    "c_path_quoted_file": 3,
    "c_preprocessor": 1,
    "c_preprocessor_include": 1,
    "c_raw_string1": 3,
    "c_raw_string2": 3,
    "c_string1": 3,
    "c_string2": 3,
    "context_menu": 1,
    "cpp_block_comment": 2,
    "cpp_line_comment": 2,
    "cpp_string_literal": 2,
    "current_line": 1,
    "debug_window": 1,
    "default": 0,
    "doc_block_comment": 3,
    "error": 7,
    "found_find": 1,
    "highlight": 3,
    "html_block_comment": 2,
    "html_element": 1,
    "html_element_end": 1,
    "js_string": 3,
    "keyword": 1,
    "line_number": 7,
    "line_number_current": 6,
    "line_overflow": 7,
    "logo": 7,
    "matching_bracket": 1,
    "matching_find": 1,
    "md_link": 2,
    "message_line": 3,
    "misspelling": 3,
    "number": 1,
    "outside_document": 7,
    "popup_window": 0,
    "pound_comment": 3,
    "py_import": 1,
    "py_import_file": 2,
    "py_raw_string1": 2,
    "py_raw_string2": 2,
    "py_string1": 2,
    "py_string2": 2,
    "quoted_string2": 2,
    "regex_string": 2,
    "right_column": 6,
    "rs_byte_string1": 3,
    "rs_byte_string2": 3,
    "rs_raw_string": 3,
    "selected": 5,
    "special": 1,
    "status_line": 7,
    "status_line_error": 7,
    "text": 0,
    "top_info": 7,
    "trailing_space": 1,
    "type": 1,
}

for i in color8.values():
    assert 0 <= i < 8, i

commentColor16Index = 2
defaultColor16Index = 1
foundColor16Index = 3
keywordsColor16Index = 2
pathColor16Index = 6
selectedColor16Index = 4  # Active find is a selection.
specialsColor16Index = 5
stringColor16Index = 6
outsideOfBufferColor16Index = 7
borderColor16Index = 8
borderHighlightColor16Index = 9

color16 = {
    "_pre_selection": stringColor16Index,
    "bracket": 6,
    "c": defaultColor16Index,
    "c_path_bracketed_file": pathColor16Index,
    "c_path_quoted_file": pathColor16Index,
    "c_preprocessor": 1,
    "c_preprocessor_include": specialsColor16Index,
    "c_raw_string1": stringColor16Index,
    "c_raw_string2": stringColor16Index,
    "c_string1": stringColor16Index,
    "c_string2": stringColor16Index,
    "context_menu": 15,
    "cpp_block_comment": commentColor16Index,
    "cpp_line_comment": commentColor16Index,
    "cpp_string_literal": stringColor16Index,
    "current_line": 15,
    "debug_window": defaultColor16Index,
    "default": defaultColor16Index,
    "doc_block_comment": commentColor16Index,
    "error": 9,
    "found_find": foundColor16Index,
    "highlight": 15,
    "html_block_comment": commentColor16Index,
    "html_element": keywordsColor16Index,
    "html_element_end": keywordsColor16Index,
    "js_string": stringColor16Index,
    "keyword": keywordsColor16Index,
    "line_number": borderColor16Index,
    "line_number_current": borderHighlightColor16Index,
    "line_overflow": 15,
    "logo": borderColor16Index,
    "matching_bracket": 15,
    "matching_find": 9,
    "md_link": stringColor16Index,
    "message_line": borderColor16Index,
    "misspelling": 9,
    "number": 2,
    "outside_document": outsideOfBufferColor16Index,
    "popup_window": borderColor16Index,
    "pound_comment": commentColor16Index,
    "py_import": keywordsColor16Index,
    "py_import_file": stringColor16Index,
    "py_raw_string1": stringColor16Index,
    "py_raw_string2": stringColor16Index,
    "py_string1": stringColor16Index,
    "py_string2": stringColor16Index,
    "quoted_string2": stringColor16Index,
    "regex_string": stringColor16Index,
    "right_column": outsideOfBufferColor16Index,
    "rs_byte_string1": stringColor16Index,
    "rs_byte_string2": stringColor16Index,
    "rs_raw_string": stringColor16Index,
    "selected": selectedColor16Index,
    "special": specialsColor16Index,
    "status_line": borderColor16Index,
    "status_line_error": borderHighlightColor16Index,
    "text": defaultColor16Index,
    "top_info": borderColor16Index,
    "trailing_space": 15,
    "type": keywordsColor16Index,
}

for i in color16.values():
    assert 0 <= i < 16, i

commentColorIndex = 2
defaultColorIndex = 18
foundColorIndex = 32
keywordsColorIndex = 21
pathColorIndex = 30
selectedColor = 64  # Active find is a selection.
specialsColorIndex = 20
stringColorIndex = 5
outsideOfBufferColorIndex = 211

color256 = {
    "_pre_selection": stringColorIndex,
    "bracket": 6,
    "c": defaultColorIndex,
    "c_path_bracketed_file": pathColorIndex,
    "c_path_quoted_file": pathColorIndex,
    "c_preprocessor": 1,
    "c_preprocessor_include": specialsColorIndex,
    "c_raw_string1": stringColorIndex,
    "c_raw_string2": stringColorIndex,
    "c_string1": stringColorIndex,
    "c_string2": stringColorIndex,
    "context_menu": 201,
    "cpp_block_comment": commentColorIndex,
    "cpp_line_comment": commentColorIndex,
    "cpp_string_literal": stringColorIndex,
    "current_line": 180,
    "debug_window": defaultColorIndex,
    "default": defaultColorIndex,
    "doc_block_comment": commentColorIndex,
    "error": 9,
    "found_find": foundColorIndex,
    "highlight": 96,
    "html_block_comment": commentColorIndex,
    "html_element": keywordsColorIndex,
    "html_element_end": keywordsColorIndex,
    "js_string": stringColorIndex,
    "keyword": keywordsColorIndex,
    "line_number": 168,
    "line_number_current": 146,
    "line_overflow": 105,
    "logo": 168,
    "matching_bracket": 201,
    "matching_find": 9,
    "md_link": stringColorIndex,
    "message_line": 3,
    "misspelling": 9,
    "number": 31,
    "outside_document": outsideOfBufferColorIndex,
    "popup_window": 117,
    "pound_comment": commentColorIndex,
    "py_import": keywordsColorIndex,
    "py_import_file": stringColorIndex,
    "py_raw_string1": stringColorIndex,
    "py_raw_string2": stringColorIndex,
    "py_string1": stringColorIndex,
    "py_string2": stringColorIndex,
    "quoted_string2": stringColorIndex,
    "regex_string": stringColorIndex,
    "right_column": outsideOfBufferColorIndex,
    "rs_byte_string1": stringColorIndex,
    "rs_byte_string2": stringColorIndex,
    "rs_raw_string": stringColorIndex,
    "selected": selectedColor,
    "special": specialsColorIndex,
    "status_line": 168,
    "status_line_error": 161,
    "text": defaultColorIndex,
    "top_info": 168,
    "trailing_space": 180,
    "type": keywordsColorIndex,
}

for i in color256.values():
    assert 0 <= i < 256, i

# Please keep these color dictionaries in sync.
assert color8.keys() == color256.keys()
assert color16.keys() == color256.keys()

# These prefs are not fully working.
prefs = {
    "color": {},
    "devTest": {},
    # TODO(dschuyler): provide a UI to enable selected dictionaries.
    u"dictionaries": {
        # The base dictionaries are loaded at startup. They are active for all
        # documents.
        "base": [
            "acronyms",
            "coding",
            "contractions",
            "cpp",
            "css",
            "en-abbreviations",
            "en-gb",
            "en-misc",
            "en-us",
            "html",
            "name",
            "user",
        ],
        # If the expanded path to the current document contains |key| the list
        # of dictionaries are applied.
        "path_match": {
            u"/chromium/": [u"chromium"],
            u"/fuchsia/": [u"fuchsia"],
        },
    },
    "editor": {
        # E.g. When key "(" is pressed, "()" is typed.
        "autoInsertClosingCharacter": False,
        # When opening a path that starts with "//", the value is used to
        # replace the first slash in a double slash prefix.
        "baseDirEnv": u"/",  # u"${FUCHSIA_DIR}",
        # Scroll the window to keep the cursor on screen.
        "captiveCursor": False,
        "colorScheme": "default",
        # Show hidden files in file list.
        "filesShowDotFiles": True,
        # Show the size on disk for files in the file list.
        "filesShowSizes": True,
        "filesShowModifiedDates": True,
        "filesSortAscendingByName": True,
        "filesSortAscendingBySize": None,
        "filesSortAscendingByModifiedDate": None,
        "findDotAll": False,
        "findIgnoreCase": True,
        "findLocale": False,
        "findMultiLine": False,
        "findUnicode": True,
        "findUseRegex": True,
        "findVerbose": False,
        "findWholeWord": False,
        # An example indentation. If the grammar has its own indent that can
        # override this value.
        "indentation": "  ",
        "lineLimitIndicator": 80,
        # When the mouse wheel is moved, which way should the window scroll.
        "naturalScrollDirection": True,
        "onSaveStripTrailingSpaces": True,
        # Ratio of columns: 0 left, 1.0 right.
        "optimalCursorCol": 0.98,
        # Ratio of rows: 0 top, 0.5 middle, 1.0 bottom.
        "optimalCursorRow": 0.28,
        "palette": "default",
        "palette8": "default8",
        "palette16": "default16",
        "palette256": "default256",
        "predictionShowOpenFiles": True,
        "predictionShowAlternateFiles": True,
        "predictionShowRecentFiles": True,
        "predictionSortAscendingByPrediction": True,
        "predictionSortAscendingByType": None,
        "predictionSortAscendingByName": None,
        "predictionSortAscendingByStatus": None,
        "saveUndo": True,
        "showLineNumbers": True,
        "showStatusLine": True,
        "showTopInfo": True,
        # When expanding tabs to spaces, how many spaces to use. This is not
        # used for indentation, see "indentation" or grammar "indent".
        "tabSize": 8,
        # Use a background thread to process changes and parse grammars.
        "useBgThread": True,
    },
    "fileType": {
        "bash": {
            "ext": [".bash", ".sh"],
            "grammar": "bash",
        },
        "binary": {
            "ext": [
                ".exe", ".gz", ".gzip", ".jar", ".jpg", ".jpeg", ".o", ".obj",
                ".png", ".pyc", ".pyo", ".tgz", ".tiff", ".zip"
            ],
            "grammar":
            "binary",
        },
        "c": {
            "ext": [".c"],
            "grammar": "c",
        },
        "cpp": {
            "ext": [
                ".cc",
                ".cpp",
                ".cxx",
                ".c++",
                ".hpp",
                ".hxx",
                ".h++",
                ".inc",
                ".h"  # Hmm, some source uses .h for cpp headers.
            ],
            "grammar":
            "cpp",
        },
        "css": {
            "ext": [".css", "_css.html"],
            "grammar": "css",
        },
        "dart": {
            "ext": [
                ".dart",
            ],
            "grammar": "dart",
        },
        "gn": {
            "ext": [".gn"],
            "grammar": "gn",
        },
        "golang": {
            "ext": [
                ".go",
            ],
            "grammar": "golang",
        },
        "grd": {
            "ext": [".grd", ".grdp"],
            "grammar": "grd",
        },
        "html": {
            "ext": [".htm", ".html"],
            "grammar": "html",
        },
        "java": {
            "ext": [
                ".java",
            ],
            "grammar": "java",
        },
        "js": {
            "ext": [".json", ".js"],
            "grammar": "js",
        },
        "md": {
            "ext": [".md"],
            "grammar": "md",
        },
        "proto": {
            "ext": [".proto"],
            "grammar": "proto",
        },
        "python": {
            "ext": [".py"],
            "grammar": "py",
        },
        "rust": {
            "ext": [".rs"],
            "grammar": "rs",
        },
        "text": {
            "ext": [".txt", ""],
            "grammar": "text",
        },
        "words": {
            "ext": [".words", ""],
            "grammar": "words",
        },
    },
    "grammar": {
        # A grammar is
        # "grammar_name": {
        #   "begin": None or regex,
        #   "continuation": None or string,
        #       Prefixed used when continuing to another line,
        #   "end": None or regex; a value of None means that the "begin" regex
        #       contains the entire pattern (a leaf grammar),
        #   "end_key": None or regex to determine dynamic end tag. For "here
        #       documents" and c++ string literals.
        #   "error": None or list of string.
        #   "escaped": None or regex,
        #   "indent": None or string,
        #   "next": other grammars that may follow this grammar without nesting
        #       within it. (Contrast with "contains").
        #   "numbers": None or list of string,
        #   "keywords": None or list of string. Matches whole words only (wraps
        #       values in \b).
        #   "single_line": Boolean, Whether entire grammar must be on a single
        #       line,
        #   "special": None or list of string.
        #   "type": text or binary. default: text.
        #   "contains": other grammars that may be contained within this
        #       grammar.
        # }
        # The entries for "error", "keywords", and "special" are very similar.
        # Other than "keywords" being wrapped in \b markers, the difference
        # between them is just how they are drawn (color and style).
        "_pre": {
            "contains": ["_pre_selection"],
            "spelling": False,
        },
        "_pre_selection": {
            "begin": r"-->",
            "end": r"<--",
            "spelling": False,
        },
        # Bash shell.
        "bash": {
            "indent":
            "  ",
            "keywords": [
                "break", "case", "continue", "do", "done", "echo", "else",
                "esac", "exit", "fi", "if", "for", "return", "switch", "then",
                "while"
            ],
            # Not really types.
            "types": [
                "ag", "basename", "chmod", "cp", "dircolors", "dirname", "find",
                "ixoff", "ixon", "lesspipe", "ln", "mkdir", "read", "rm",
                "rmdir", "rxvt", "sed", "sleep", "ssh", "tput", "wc"
            ],
            "contains": ["c_string1", "c_string2", "pound_comment"],
        },
        "binary": {
            "spelling": False,
            "type": "binary",
        },
        # C language.
        "c": {
            "indent":
            "  ",
            "keywords":
            __c_keywords,
            "types":
            __c_primitive_types,
            "contains": [
                "cpp_block_comment", "cpp_line_comment", "c_preprocessor",
                "c_string1", "c_string2"
            ],
        },
        # C++ language.
        "cpp": {
            "indent":
            "  ",
            "keywords":
            __cpp_keywords,
            "namespaces": [
                "::",
                "std::",
            ],
            "types":
            __c_primitive_types + [
                "char8_t",
                "char16_t",
                "char32_t",
            ],
            "contains": [
                "cpp_block_comment", "cpp_line_comment", "c_preprocessor",
                "cpp_string_literal", "c_string1", "c_string2"
            ],
        },
        "cpp_block_comment": {
            "begin": r"/\*",
            "continuation": " * ",
            "end": r"\*/",
            "indent": "  ",
            "keywords": [],
            "special": [
                r"\bNOTE:",
                _todo,
                __chrome_extension,
                __sha_1,
            ],
        },
        "cpp_line_comment": {
            "begin": "//",
            "continuation": "// ",
            "end": r"(?<!\\)\n",
            "indent": "  ",
            "keywords": [],
            "special": [
                r"\bNOTE:",
                _todo,
                __chrome_extension,
                __sha_1,
            ],
        },
        "c_preprocessor": {
            "begin":
            r"^#",
            "end":
            r"(?<!\\)\n",
            "indent":
            "  ",
            "special": [
                r"\bdefine\b",
                r"\bdefined\b",
                r"\belif\b",
                r"\belif\b",
                r"\belse\b",
                r"\bendif\b",
                r"\bif\b",
                r"\bifdef\b",
                r"\bifndef\b",
                r"\binclude\b",
                r"\bpragma\b",
                r"\bundef\b",
            ],
            "next": [
                "c_preprocessor_include",
            ],
        },
        "c_preprocessor_include": {
            "begin": r"\binclude",
            "end": r"(?<!\\)\n",
            "contains": ["c_path_quoted_file", "c_path_bracketed_file"],
        },
        "c_raw_string1": {
            "begin": "[uU]?[rR]'",
            "end": "'",
            "escaped": r"\\'",
            "indent": "  ",
            "single_line": True,
            "special": __special_string_escapes + [r"\\'"],
        },
        "c_raw_string2": {
            "begin": "[uU]?[rR]\"",
            "end": "\"",
            "escaped": "\\\\\"",
            "indent": "  ",
            "single_line": True,
            "special": __special_string_escapes + ["\\\\\""],
        },
        "cpp_string_literal": {
            "begin": "R\"",
            # TODO(dschuyler): backslash and whitespace are invalid in the
            # |end_key|.
            "end_key": """R\"([^(]*)\\(""",
            "end": "\\)\\0\"",
            "single_line": False,
        },
        "c_string1": {
            "begin": "'(?!'')",
            "end": "'",
            "escaped": r"\\'",
            "indent": "  ",
            "special": __special_string_escapes + [r"\\'"],
            "single_line": True,
        },
        "c_string2": {
            "begin": "\"(?!\"\")",
            "end": "\"",
            "escaped": "\\\\\"",
            "indent": "  ",
            "special": __special_string_escapes + ["\\\\\""],
            "single_line": True,
        },
        "c_path_bracketed_file": {
            # Paths in includes don't allow escapes.
            "begin": """<[^>\\n]*>""",
            "end": None,  # Leaf grammar.
            "link_type": "c<",  # C system include file.
        },
        "c_path_quoted_file": {
            # Paths in includes don't allow escapes.
            "begin": '''"[^"\\n]*"''',
            "end": None,  # Leaf grammar.
            "link_type": "c\"",  # C non-system include file.
        },
        # Cascading Style Sheet.
        "css": {
            "begin": "<style",
            "end": "</style>",
            "indent": "  ",
            "keywords": [
                "host",
                "slotted",
            ],
            "special": [r"#[\w-]+"],
            "contains": ["cpp_block_comment", "css_block"],
        },
        "css_block": {
            "begin":
            r"\\{",
            "end":
            r"\\}",
            "indent":
            "  ",
            "keywords": [
                "background-color", "color", "display", "font-family",
                "font-size", "height", "max-height", "min-height", "width",
                "max-width", "min-width"
            ],
            "special": [
                r"@apply\b",
            ],
            "contains": ["cpp_block_comment", "css_value"],
        },
        "css_value": {
            "begin":
            ":",
            "end":
            ";",
            "errors": [
                r"#(?:[^;]{1,2}|[^;]{5}|[^;]{7}|[^;]{9,})\b",
            ],
            "indent":
            "  ",
            "keywords": [
                "absolute", "attr", "block", "border-box", "calc", "center",
                "default", "ease", "hidden", "inherit", "left", "none", "px",
                "rgb", "rgba", "right", "rotate[XYZ]?", "scale[XYZ]?", "solid",
                "transform", "translate[XYZ]?", "transparent", "var"
            ],
            "special": [
                r"@apply\b", r"\d+deg\b", r"\d+em\b", r"\d+px\b", r"\d+rem\b",
                r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})"
            ],
            "contains": [
                "cpp_block_comment",
            ],
        },
        # Dart language.
        "dart": {
            "indent":
            "  ",
            "keywords": [
                "abstract", "as", "assert", "async", "async", "await", "break",
                "case", "catch", "class", "const", "continue", "covariant",
                "default", "deferred", "do", "dynamic", "else", "enum",
                "export", "extends", "external", "factory", "false", "final",
                "finally", "for", "get", "if", "implements", "import", "in",
                "interface", "is", "library", "mixin", "new", "null",
                "operator", "part", "rethrow", "return", "set", "static",
                "super", "switch", "sync", "this", "throw", "true", "try",
                "typedef", "var", "void", "while", "with", "yield"
            ],
            "special": [
                "@override",
            ],
            "contains": [
                # This list is carefully ordered. Don"t sort it.
                "py_string1",
                "py_string2",
                "py_raw_string1",
                "py_raw_string2",
                "c_raw_string1",
                "c_raw_string2",
                "c_string1",
                "c_string2",
                "cpp_line_comment",
            ],
        },
        "doc_block_comment": {
            "begin":
            r"/\*\*",
            "continuation":
            " * ",
            "end":
            r"\*/",
            "indent":
            "  ",
            "keywords": [],
            "special": [
                r"@param\b",
                r"@private\b",
                r"@protected\b",
                r"@type\b",
                r"@typedef\b",
                r"@return\b",
                r"\bNOTE:",
                _todo,
            ],
            "types": ["Array", "boolean", "string", "Object"],
        },
        "error": {
            "indent": "  ",
            "spelling": False,
        },
        # Generate Ninja language.
        "gn": {
            "indent": "  ",
            "keywords": ["else", "false", "foreach", "if", "import", "true"],
            "special": [],
            "types": [],
            "contains": [
                "pound_comment",
                "c_string1",
                "c_string2",
            ],
        },
        # Go Language.
        "golang": {
            "indent":
            "  ",
            "keywords": [
                "break", "case", "chan", "const", "continue", "default",
                "defer", "else", "fallthrough", "for", "func", "go", "goto",
                "if", "import", "interface", "map", "nil", "package", "range",
                "return", "select", "struct", "switch", "type", "var"
            ],
            "special": [
                #r"(?<!\w)__.*?__(?!\w)",
            ],
            "contains": [
                "cpp_block_comment", "cpp_line_comment", "cpp_string_literal",
                "c_string1", "c_string2"
            ],
        },
        "grd": {
            "keywords": ["flattenhtml", "allowexternalscript"],
        },
        "html": {
            "begin":
            "<html>",
            "end":
            app.regex.kNonMatchingRegex,
            "errors": [
                "</br>",
                "</hr>",
                "</img>",
                "</input>",
            ],
            "indent":
            "  ",
            "keywords": [
                #"body", "button", "div", "head", "html", "href", "img",
                #"input", "script", "select", "span", "style",
            ],
            "special": [
                r"&.{1,5}?;",
                "<if\s+expr=\"[^\"]*[^>]*>",
                "</if>",
            ],
            "contains": [
                "quoted_string1",
                "quoted_string2",
                "css",
                "html_block_comment",
                "js",
                "html_element",
                "html_element_end",
            ],
        },
        "html_block_comment": {
            "begin": "<!--",
            "end": "-->",
            "indent": "  ",
        },
        "html_element": {
            "begin": r"<[\w-]+",  # The "-" is used by Polymer.
            "contains": [
                "html_element_attribute",
            ],
            "end": ">",
            "special": [
                r"\\w+",
            ],
        },
        "html_element_attribute": {
            "begin": "\\??=\"",
            "end": "\"",
        },
        "html_element_end": {
            "begin": r"</\\w+",
            "end": ">",
        },
        "java": {
            "indent":
            "  ",
            "keywords":
            __common_keywords + [
                "case", "class", "default", "do", "false", "interface",
                "switch", "this", "true"
            ],
            "contains":
            ["c_string1", "c_string2", "cpp_block_comment", "cpp_line_comment"],
        },
        # JavaScript language.
        "js": {
            "begin":
            "<script",
            "end":
            "</script>",
            "indent":
            "  ",
            "keywords": [
                "arguments", "break", "case", "class", "const", "continue",
                "default", "delete", "document", "else", "false", "for",
                "function", "if", "instanceof", "let", "of", "return", "static",
                "switch", "super", "this", "true", "undefined", "var", "while",
                "yield"
            ],
            "special": [
                "\bsetTimeout\b",
                "\brequestCallback\b",
                "\bconsole\b",
                "\bwindow\b",
            ],
            "contains": [
                "c_string1",
                "c_string2",
                "doc_block_comment",
                "cpp_block_comment",
                "cpp_line_comment",
                "regex_string",
                "js_string",
            ],
        },
        "js_string": {
            "begin": r"`",
            "end": r"`",
            "escaped": r"\\`",
            "indent": "  ",
            "special":
            __special_string_escapes + [r"\\`", r"(?<!\\)\$\{[^}]*\}"],
            "single_line": False,
        },
        "keyword": {
            "indent": "  ",
            "spelling": False,
        },
        # Markdown language.
        "md": {
            "indent": "  ",
            "keywords": [],
            #"special": [r"\[[^]]+\]\([^)]+\)"],
            "contains": [
                "md_link",
                #"quoted_string1", "quoted_string2"
            ],
        },
        "md_link": {
            "begin": "\[",
            "end": "\]",
            "escaped": r"\\\]",
            "indent": "  ",
        },
        "none": {
            "spelling": False,
        },
        # Proto buffer language.
        "proto": {
            "indent":
            "  ",
            "keywords":
            __common_keywords +
            ["message", "option", "package", "returns", "rpc", "syntax"],
            "namespaces": [],
            "special": [
                #r"(?<!\w)__.*?__(?!\w)",
            ],
            "types": [
                "bool", "bytes", "double", "enum", "float", "int8", "int16",
                "int32", "int64", "optional", "repeated", "required", "string",
                "uint8", "uint16", "uint32", "uint64"
            ],
            "contains": [
                # This list is carefully ordered. Don"t sort it.
                "c_string1",
                "c_string2",
                "cpp_line_comment",
            ],
        },
        # Python language.
        "py": {
            "indent":
            "    ",
            "keywords":
            __common_keywords + [
                "and", "as", "assert", "class", "def", "del", "dict", "elif",
                "except", "False", "finally", "from", "global", "import", "in",
                "is", "len", "list", "None", "not", "or", "pass", "raise",
                "range", "self", "True", "try", "tuple", "until", "with",
                "yield"
            ],
            "namespaces": [
                "os\.",
                "os\.path\.",
                "sys\.",
                "traceback\.",
                "re\.",
            ],
            "special": [
                #r"(?<!\w)__.*?__(?!\w)",
            ],
            "types": [
                "Exception",
            ],
            "contains": [
                # This list is carefully ordered. Don"t sort it.
                "py_string1",
                "py_string2",
                "py_raw_string1",
                "py_raw_string2",
                "c_raw_string1",
                "c_raw_string2",
                "c_string1",
                "c_string2",
                "pound_comment",
                "py_from",
                "py_import",
            ],
        },
        "pound_comment": {
            "begin": "#",
            "continuation": "# ",
            "end": r"\n",
            "indent": "  ",
            "keywords": [],
            "special": [
                r"\bNOTE:",
                _todo,
            ],
        },
        "py_from": {
            "begin": "from",
            "end": r"\n",
            "contains": ["py_import_file"],
            "next": ["py_import_after_from", "pound_comment"],
            "spelling": False,
        },
        "py_import_after_from": {
            "begin": "import",
            "end": None,
        },
        "py_import": {
            "begin": "import",
            "end": r"\n",
            "keywords": [
                "as",
            ],
            "contains": ["py_import_file"],
            "next": ["pound_comment"],
            "spelling": False,
        },
        "py_import_file": {
            "begin": "[\.\w]+",
            "end": None,  # Leaf grammar.
            "link_type": r"pi",  # Python import
            "spelling": False,
        },
        "py_raw_string1": {
            "begin": "[uU]?[rR]'''",
            "end": "'''",
            "escaped": r"\\'",
            "indent": "  ",
            #"special": ["\"\"?\"?$"],
        },
        "py_raw_string2": {
            "begin": "[uU]?[rR]\"\"\"",
            "end": "\"\"\"",
            "escaped": "\\\\\"",
            "indent": "  ",
            #"special": ["\\\\\""],
        },
        "py_string1": {
            "begin": "[uU]?'''",
            "end": "'''",
            "escaped": r"\\'",
            #"indent": "  ",
            "special": __special_string_escapes + [r"\\'"],
        },
        "py_string2": {
            "begin": "[uU]?\"\"\"",
            "end": "\"\"\"",
            "escaped": "\\\\\"",
            #"indent": "  ",
            "special": __special_string_escapes + ["\\\\\""],
        },
        "quoted_string1": {
            # This is not a programming string, there are no escape chars.
            "begin": "'",
            "end": "'",
        },
        "quoted_string2": {
            # This is not a programming string, there are no escape chars.
            "begin": "\"",
            "end": "\"",
        },
        "regex_string": {
            "begin": r"(?<=[\n=:;([{,])(?:\s*)/(?![/*])",
            "end": "/",
            "escaped": r"\\.",
            "indent": "  ",
            "special": __special_string_escapes + [r"\\/"],
            "single_line": True,
        },
        # Rust language.
        "rs": {
            "indent":
            "    ",
            "keywords": [
                "abstract", "alignof", "as", "async", "await", "become", "box",
                "break", "const", "continue", "crate", "do", "dyn", "else",
                "enum", "extern", "false", "final", "fn", "for", "if", "impl",
                "in", "let", "loop", "macro", "match", "mod", "move", "mut",
                "offsetof", "override", "priv", "pub", "pure", "ref", "return",
                "Self", "self", "sizeof", "static", "struct", "super", "trait",
                "true", "type", "typeof", "try", "unsafe", "unsized", "use",
                "virtual", "where", "while", "yield"
            ],
            "special": [
                #r"(?<!\w)__.*?__(?!\w)",
                "<\s*'",
                "&\s*'",
            ],
            "types": [
                "bool", "char", "i8", "i16", "i32", "i64", "isize", "u8", "u16",
                "u32", "u64", "usize", "array", "slice", "tuple"
            ],
            "contains": [
                "cpp_block_comment",
                "cpp_line_comment",
                "c_string1",
                "c_string2",
                "rs_byte_string1",
                "rs_byte_string2",
                "rs_raw_string",
            ],
        },
        "rs_byte_string1": {
            "begin": "b'",
            "end": "'",
        },
        "rs_byte_string2": {
            "begin": "b\"",
            "end": "\"",
        },
        "rs_raw_string": {
            "begin": "b?r#*\"",
            # TODO(dschuyler): backslash and whitespace are invalid in the
            # |end_key|.
            "end_key": """b?r(#*)\"""",
            "end": "\"\\0",
            "single_line": False,
        },
        "special": {
            "indent": "  ",
            "spelling": False,
        },
        "text": {
            "special": [
                __sha_1,
            ],
            "contains": ["quoted_string1", "quoted_string2"],
        },
        "type": {
            "indent": "  ",
            "spelling": False,
        },
        # Dictionary file for ci_edit.
        "words": {
            "contains": [
                "pound_comment",
            ],
        },
    },
    "palette": {
        # Note: index 0 of each palette is not set, it remains as the system
        # entry.
        "test": {
            # Same foreground color in all 256 slots.
            "foregroundIndexes": [18] * 256,
            # Separate background color in every slot.
            "backgroundIndexes": [i for i in range(0, 256)],
        },
        "dark": {
            # This series repeats 8 times (32 * 8 = 256).
            "foregroundIndexes": [
                14, 202, 39, 39, 39, 39, 39, 39, 39, 39, 39, 39, 12, 13, 14, 15,
                202, 14, 14, 202, 202, 202, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                57
            ] * 8,
            # Each of the foreground colors repeat 8 times (32 * 8 = 256).
            "backgroundIndexes": [232] * 32 + [229] * 32 + [6] * 32 + [221] * 32
            + [245] * 32 + [244] * 32 + [243] * 32 + [225] * 32,
        },
        "default8": {
            # With only 8 colors, make a custom pair for each slot.
            # 0: black, 1: red, 2: green, 3: yellow, 4: blue, 5: pink, 6: cyan,
            # 7: gray.
            "foregroundIndexes": [1, 4, 2, 3, 4, 5, 6, 0],
            "backgroundIndexes": [0, 6, 7, 7, 7, 7, 7, 7],
        },
        "default16": {
            # With only 16 colors, make a custom pair for each slot.
            # 0: black, 1: red, 2: green, 3: yellow, 4: blue, 5: pink, 6: cyan,
            # 7: gray.
            "foregroundIndexes":
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 4, 2, 3, 4, 5, 6, 0],
            "backgroundIndexes":
            [0, 15, 15, 15, 15, 15, 15, 15, 7, 7, 7, 7, 7, 7, 7, 15],
        },
        "default256": {
            # This series repeats 8 times (32 * 8 = 256).
            "foregroundIndexes": [
                18, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 94, 134,
                0, 240, 138, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 57
            ] * 8,
            # Each of the foreground colors repeat 8 times (32 * 8 = 256).
            "backgroundIndexes": [231] * 32 + [229] * 32 + [14] * 32 +
            [221] * 32 + [255] * 32 + [254] * 32 + [253] * 32 + [225] * 32,
        },
    },
    "status": {
        "showTips": False,
    },
    "userData": {
        "homePath":
        os.path.expanduser("~/.ci_edit"),
        "historyPath":
        os.path.join(os.path.expanduser("~/.ci_edit"), "history.dat"),
    },
}

# Alias for old palette name.
prefs[u"palette"][u"default"] = prefs[u"palette"][u"default256"]
