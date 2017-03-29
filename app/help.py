
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
  ctrl+f       Find
  ctrl+g       Go to line
  ctrl+q       Quit (exit editor)
  ctrl+r       Reverse find
  ctrl+s       Save file
  ctrl+v       Paste
  ctrl+x       Cut
  ctrl+y       Redo
  ctrl+z       Undo

Within the Find prompt:

  Text commands (such as cut and paste)
  opperate on the prompt text rather
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
  opperate on the prompt text rather
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
  Version: b10
  See LICENSE for license information
  See readme.md for an introduction
  Both files may be found in "%s"
  Please send feedback and bug reports to dschuyler@
""" % (dirPath,),
}
