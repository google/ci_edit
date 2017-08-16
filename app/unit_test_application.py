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


import os
os.environ['CI_EDIT_USE_FAKE_CURSES'] = '1'

import app.ci_program
from app.curses_util import *
import curses
import re
import sys
import unittest


class IntentionTestCases(unittest.TestCase):
  def setUp(self):
    cursesScreen = curses.StandardScreen()
    self.prg = app.ci_program.CiProgram(cursesScreen)

  def tearDown(self):
    pass

  def test_empty_buffer_manager(self):
    assert self.prg

  def test_open_and_quit(self):
    self.assertTrue(self.prg)
    self.assertFalse(self.prg.exiting)
    curses.setFakeInputs([CTRL_Q])
    self.prg.run()
    self.assertTrue(self.prg.exiting)

  def test_new_file_quit(self):
    self.assertTrue(self.prg)
    self.assertFalse(self.prg.exiting)
    curses.setFakeInputs([CTRL_Q])
    sys.argv = ['test_file', '--p']
    self.prg.run()
    self.assertTrue(self.prg.exiting)

  def test_logo(self):
    curses.setFakeInputs([CTRL_Q])
    sys.argv = ['test_file', '--p']
    self.prg.run()
    self.assertFalse(curses.checkDisplayForErrors(0, 0, [" ci "]))

  def test_text_contents(self):
    def testDisplay():
      if 0:
        for i in curses.showDisplay():
          print 'display ', i
      self.assertFalse(curses.checkDisplayForErrors(2, 7, ["text "]))
    def flush():
      pass
    kNoOpsPerFlush = 5
    closure = {
      'commands': ['t', 'e', 'x', 't', flush, testDisplay, CTRL_Q, 'n', flush],
      'index': -1,
      'flushCounter': kNoOpsPerFlush,
    }
    def handler():
      while closure['index'] + 1 < len(closure['commands']):
        closure['index'] += 1
        cmd = closure['commands'][closure['index']]
        if cmd is flush:
          if closure['flushCounter']:
            closure['index'] -= 1
            closure['flushCounter'] -= 1
            return -1
          closure['flushCounter'] = kNoOpsPerFlush
        elif type(cmd) == type(handler):
          cmd()
        elif type(cmd) == type('a') and len(cmd) == 1:
          return ord(cmd)
        else:
          return cmd
    curses.setGetchCallback(handler)
    sys.argv = ['test_file', '--p']
    self.prg.run()
    curses.setGetchCallback(None)


