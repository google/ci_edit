#!/usr/bin/python
# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import app.ci_program
import curses


def run_ci(stdscr):
  prg = app.ci_program.CiProgram(stdscr)
  prg.run()

if __name__ == '__main__':
    curses.wrapper(run_ci)
