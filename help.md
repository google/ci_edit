# Help for ci_edit

### Contents:
  Quick Tips
  Key Bindings
  Execute Prompt
  Prediction Prompt
  Note


## Quick Tips (How to quit or exit)

To exit the program: hold the control key and press q.
A shorthand for "hold the control key and press q" is ctrl+q, which can also be
written ^q (the chevron represents 'control').


## Key Bindings

### Within the main text window:
```
  ctrl+a       Select all
  ctrl+c       Copy
  ctrl+e       Execute prompt (e:)
  ctrl+f       Find prompt (find:)
  ctrl+g       Go to line prompt (goto:)
  ctrl+l       Select current line (subsequent select next line)
  ctrl+o       Open file prompt (open:)
  ctrl+p       Prediction prompt (p:)
  ctrl+q       Quit (exit editor)
  ctrl+r       Reverse find
  ctrl+s       Save file
  ctrl+v       Paste
  ctrl+w       Close document
  ctrl+x       Cut
  ctrl+y       Redo
  ctrl+z       Undo
```
### Within Any Prompt

Prompts in this context are the e:, find:, goto:, and p: modes.

  Text commands (such as cut and paste)
  operate on the prompt text rather
  than the main window.
```
  return       Perform action and return to editing the file
  esc          Abort action and return to editing the file
  ctrl+a       Select all*
  ctrl+c       Copy*
  ctrl+l       Select whole line*
  ctrl+q       Quit (exit editor)
  ctrl+s       Save file
  ctrl+v       Paste*
  ctrl+x       Cut*
  ctrl+y       Redo*
  ctrl+z       Undo*
```
  * Affects find: prompt, not the document.

### Within the Find prompt:

  See "Within Any Prompt", plus these:
```
  ctrl+f       Find next
  ctrl+g       Find next
  ctrl+o       Switch to Open prompt (open:)
  ctrl+p       Switch to Prediction prompt (p:)
  ctrl+q       Quit (exit editor)
  ctrl+r       Reverse find
```
### Within the Goto line prompt:

  See "Within Any Prompt", plus these:
```
  b            Jump to bottom of document
  h            Jump to half-way in the document
  t            Jump to top of document
  ctrl+p       Prediction prompt (p:)
```
  * Affects goto: prompt, not the document.

### Execute Prompt

  The execution prompt allows you to run powerful commands to manipulate the
  currently selected text or perform other actions.
```
  sort         Sort selected text
  |<cmd>       Pipe selected text to <cmd> and replace selection with result.
               Example:
               1. Select several lines of text
               2. Press ctrl+e
               3. At the e: prompt type: |sort -u
               4. Press return
               Result: the lines will be sorted and duplicate lines will be
                 removed (-u stands for 'unique').
  !<cmd>       Execute <cmd> in a sub-shell
```
### Prediction Prompt

  The prediction prompt tries to guess where you'd like to visit next. The upper
  window will show a list of files or locations that are somehow related to the
  current file. E.g. if the current file is a c++ file, it may suggest the
  header file as a someplace you'd like to visit.
```
  ctrl+p       Move selection up one line
  ctrl+n       Move selection down one line
  return       Open (or switch to) that file
```

## Note

This is not an official Google product.



Copyright 2016 Google Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
