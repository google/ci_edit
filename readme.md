# What is ci_edit

ci_edit is a text editor. It can help you view or edit text files.

ci_edit runs in the command line (also called the terminal). To start using
ci_edit, download ci_edit and open (execute) `ci.py`.


## What ci_edit can do for you

Many other command line text editors require learning a different set of mouse
and keyboard commands. Many of us use a graphical editor (GUI) that supports
a common set of commands like `ctrl+q` to quit (that is, hold the control key and
press Q). Here are a few common commands:

  - ctrl+q    to quit the program
  - ctrl+s    to save the file
  - ctrl+z    undo
  - ctrl+x    cut
  - ctrl+c    copy
  - ctrl+v    paste

There are more, but you probably get the idea. These common controls are not
common in command line editors.

So, what if you'd like to edit a file in the terminal window but don't want to
recall how to save or quit in an unfamiliar editor? This is where ci_edit
shines, because ci_edit does support those familiar key sequences. You already
know how to save in ci_edit, it's `ctrl+s`. Simple.

This version of ci_edit still doesn't have all the intended features, but it's
a start. It's has the necessary features of a basic text editor and a few fancy
extras. Those fancy extras stay out of your way until you want them.

## How to stay in touch

To get news about new features, please join
- [ci_edit-announce](https://groups.google.com/forum/#!forum/ci_edit-announce)

If you have a question (i.e. "how do I..."), please post it here
- [ci_edit-users](https://groups.google.com/forum/#!forum/ci_edit-users)

Have you found a case where ci_edit misbehaves, please let us know by describing
what happened here
- [Report bug in ci_edit](https://github.com/google/ci_edit/issues/new)

For those interested in contributing new features or steering the future
direction of ci_edit, join us on
- [ci_edit-dev](https://groups.google.com/forum/#!forum/ci_edit-dev)


### Installation (Linux / Mac OS)

* Execute the install script with root privileges.  Either change directory
  `cd` to the downloaded directory (or local repository): `ci_edit`, or use
  the path to the installation file (i.e. `./[PATH_TO_FILE]/install.sh`).

```
$ sudo ./install.sh
```

* **Note:** This script creates a copy of the repository in the directory
  `/opt/ci_edit/`; the **update**, overwrites that copy.  Then a symbolic
  link is created in the directory `/usr/local/bin/`, which is generally
  designated for user programs not managed by the distribution package manager

### Usage

* This command opens the text editor from any directory.  The execution command
  for the editor can be specified by user choice during installation or
  manually.

```
$ we
```

* To edit a file (such as `README.md`) by name:

```
$ we README.md
```

## What you can do for ci_edit


The help we now need is finding out what puts users off; what causes someone who
tries the editor to stop using it. We intend to address those issues so that
more users are happy users for a longer time.


# Features of ci_edit

## Stand out features
- nested grammars
  - A source file being edited may start in one grammar such as HTML and
    contain nested JavaScript or CSS. ci_edit will highlight each grammar for
    each separate language.
- terminal mouse support and GUI shortcuts by default (enabled out-of-the-box).
- open the file you meant
  - If a given path doesn't exist, ci_edit will try to estimate "what you
    meant". This allows for opening a file path by copy/pasting output from
    other tools without needing to touch up the path.
    - This is disabled by passing a line number parameter, such as +1 (which
      opens the file to the first line).
  - A path such as `a/foo/bar.cc` can open `foo/bar.cc`.
    - Why: `git diff` may add `a/` or `b/` prefixes to files in diff output.
  - A path such as `foo/bar.cc:421` can open `foo/bar.cc` to line number 421
    - Why: some compiler or log output us a <file>:<line number> notation to
      refer to specific lines.

## Uncommon features
Some other editors provide these features, but not all of them.
- file path tab-completion
  - i.e. when opening files
- written in Python
  - No Python experience is required. Being written in Python means that many
    users will be able to review the code.
  - Python 3.7+ and Python 2.7+ are supported.
  - Python 2 support may be phased out in favor of focusing on Python 3
    features. If you'd prefer that Python 2 support continue, please comment on
    https://github.com/google/ci_edit/issues/205
- saved undo/redo
  - Open a file and undo prior edits of that document
- runs on nCurses
  - This means that it can use used in the terminal window just like vim,
    emacs, and pine.
- sensible save and quit
  - Using GUI editor keyboard short-cuts: `ctrl+s` and `ctrl+q` respectively.

## Common features
We should expect these features from a text editor.
- cut/copy/paste
  - Using common GUI editor keyboard short-cuts: `ctrl+x`, `ctrl+c`, and
    `ctrl+v`!
- syntax highlighting
  - keywords an such are displayed in different colors.
- find within text
  - Regular expression search forward and backward.
- line numbers
  - Shown on the left side.
- go to line with `ctrl+g`
  - Jump to a line number or the top, bottom, or middle of the document
- unlimited undo/redo
  - Or at least within the limits of disk space to page to
- selection modes
  - select by line, word, character, select all, or rectangle (block) selection
- brace matching
  - Place the cursor on a brace, bracket, or parenthesis and the pair of
    characters are highlighted.
- mouse support
  - Yes, in the terminal
  - click to place the cursor
  - double click to select by word
  - triple click to select by line
  - shift+click to extend selection
  - alt+click for rectangular (block) selection
- pipe to editor
  - Send the output from another program directly into the editor without the
    need for a temporary file
- strips/trims trailing white-space on each line
  - Each time the file is saved
- resume at last edit position
  - The cursor location is stored within `~/.ci_edit/`
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

## Future features (the to do list)

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
- a lot more...
  - There are so many dreams for the future.


# Obligatory


## Origins

The world does need another text editor. (Or at least I think so).

There are other fine curses based editors. I found that I was often trying to
tweak them to get just what I wanted. Almost as often, some aspect of those
editors prevented that last little bit of customization. So writing a text
editor should allow all the customization I like, right?

Writing a text editor is an interesting project. Give it a try sometime.


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

