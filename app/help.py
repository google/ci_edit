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

import os

dirPath = os.path.split(os.path.abspath(os.path.dirname(
    __file__)))[0]

docs = {
  'command line': \
"""Command line help
ci [args] [file...]

  -          Read from standard in.
  --         Treat remaining arguments as file names.
  --log      Show logging and debug info
  --help     This help message.
  --version  Print version information and exit.
""",

  'key bindings': \
"""Key Bindings

Within the main text window:

  ctrl+a       Select all
  ctrl+c       Copy
  ctrl+e       Execute prompt (e:)
  ctrl+f       Find prompt
  ctrl+g       Go to line prompt
  ctrl+o       Open file prompt.
  ctrl+q       Quit (exit editor)
  ctrl+r       Reverse find
  ctrl+s       Save file
  ctrl+v       Paste
  ctrl+x       Cut
  ctrl+y       Redo
  ctrl+z       Undo

Within the Find prompt:

  Text commands (such as cut and paste)
  operate on the prompt text rather
  than the main window.

  return       Exit Find
  esc          Exit Find
  ctrl+a       Select all
  ctrl+c       Copy
  ctrl+f       Find next
  ctrl+g       Find next
  ctrl+q       Quit (exit editor)
  ctrl+r       Reverse find
  ctrl+s       Save file
  ctrl+v       Paste
  ctrl+x       Cut
  ctrl+y       Redo
  ctrl+z       Undo

Within the Goto line prompt:

  Text commands (such as cut and paste)
  operate on the prompt text rather
  than the main window.

  b            Jump to bottom of document
  h            Jump to half-way in the document
  t            Jump to top of document
  return       Exit Goto
  esc          Exit Goto
  ctrl+a       Select all
  ctrl+c       Copy
  ctrl+q       Quit (exit editor)
  ctrl+s       Save file
  ctrl+v       Paste
  ctrl+x       Cut
  ctrl+y       Redo
  ctrl+z       Undo
""",

  'version': \
"""
  Version: b23
  See LICENSE for license information
  See readme.md for an introduction
  Both files may be found in "%s"
  Please send feedback and bug reports to dschuyler@
""" % (dirPath,),
}
