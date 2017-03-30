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
- line numbers
- goto line
- unlimited undo/redo
- file path tab-completion
- written in Python
- select by line, character, or all
- brace matching
- mouse support
- pipe to editor
- resume at last edit position
- search and replace

Future features (todo)

- bookmarks
- find in files
- spell check
- user customizable keywords
- user customizable color scheme
- build/error tracking
- auto reload of modified files
- trace file
- jump to opposing brace
- saved undo/redo
- a lot more...

Copyright 2016 The ci_edit Authors. All rights reserved.
Use of this source code is governed by an Apache-style license that can be
found in the LICENSE file.
