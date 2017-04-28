### The ci text editor

The world does need another text editor.

There are other fine curses based editors. I found that I was often trying to
tweak them to get just what I wanted. Almost as often, some dark piece of those
editors prevented that last little bit of customization. So writing a text
editor should allow all the customization I like, right?

Writing a text editor is an interesting project. Give it a try sometime.

This version of ci_edit still doesn't have all the intended features, but it's
a start. It's has the necessary features of a basic text editor and new features
are still being added.

The help I now need is finding out what puts you off; what causes someone who
tries the editor to stop using it. I'm looking to address those issues so that
more users are happy users for a longer time.

Features of ci

- runs on nCurses
  - This means that it can use used in the terminal window just  like vim,
    emacs, and pine.
- cut/copy/paste
  - Using common GUI editor keyboard short-cuts: control-x, control-c, and
    control-v!
- sensible save and quit
  - Using GUI editor keyboard short-cuts: control-s and control-q respectively.
- syntax highlighting
  - keywords an such are displayed in different colors.
- nested grammars
  - A source file being edited may start in one grammar such as HTML and
    contain nested JavaScript. ci_edit will highlight each grammar for each
    separate language.
- find within text
  - Regular expression search forward and backward.
- line numbers
  - Shown on the left side.
- go to line
  - Jump to a line number or the top, bottom, or middle of the document
- unlimited undo/redo
  - Or at least within the limits of disk space to page to
- file path tab-completion
  - i.e. when opening files
- written in Python
  - No Python experience is required. Being written in Python means that many
    users will be able to review the code.
- selection modes
  - select by line, word, character, select all, or rectangle (block) selection
- brace matching
  - Place the cursor on a brace, bracket, or parenthesis and the pair of
    characters are highlighted.
- mouse support
  - Yes, in the terminal
- pipe to editor
  - Send the output from another program directly into the editor without the
    need for a temporary file
- strips/trims trailing white-space on each line
  - Each time the file is saved
- resume at last edit position
  - The cursor location is stored within ~/.ci_edit/
- search and replace
  - Control the scope of the replacement with the current selection
- execute sub-processes
  - Either with or without a sub-shell; including piping between to, from, and
    between sub-processes
- filter text through other tools
  - Send selected text through a sub-process and capture the output into the
    current document.
- spell check
  - ultra-fast spell checking. English and coding word dictionaries included.
- built-in filters
  - Sort selected lines
  - regex text substitution, such as s/dogs/cats/ replaces the text "dogs" with
    the text "cats".

Future features (todo)

- bookmarks
- find in files
  - Not just the current file, but search through files in a directory.
- user customizable keywords
- user customizable color scheme
- build/error tracking
  - Capture the output from make and similar tools and integrate the results.
- auto reload of modified files
  - Tell you when a file has changed on disk and offer to re-open it.
- trace file
  - Monitor a file and continuously read in the new lines
- jump to opposing brace
  - Move the cursor from here to there.
- saved undo/redo
  - Open a file and undo prior edits of that document
- a lot more...
  - I have dreams for the future.

Copyright 2016 The ci_edit Authors. All rights reserved.
Use of this source code is governed by an Apache-style license that can be
found in the LICENSE file.
