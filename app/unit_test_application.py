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


kTestFile = '#test_file~'


class IntentionTestCases(unittest.TestCase):
  def setUp(self):
    print '@@@@@@ set up'
    if os.path.isfile(kTestFile):
      os.unlink(kTestFile)
    self.assertFalse(os.path.isfile(kTestFile))
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
    curses.printFakeDisplay()
    self.assertTrue(self.prg)
    self.assertFalse(self.prg.exiting)
    curses.setFakeInputs([CTRL_Q])
    sys.argv = [kTestFile]
    self.prg.run()
    self.assertTrue(self.prg.exiting)
    curses.printFakeDisplay()

  def test_logo(self):
    curses.printFakeDisplay()
    curses.setFakeInputs([CTRL_Q, curses.printFakeDisplay])
    self.prg.run()
    self.assertFalse(curses.checkFakeDisplay(0, 0, [" ci "]))
    curses.printFakeDisplay()

  def test_text_contents(self):
    curses.printFakeDisplay()
    def testDisplay():
      self.assertFalse(curses.checkFakeDisplay(2, 7, ["text "]))
    curses.setFakeInputs(['t', 'e', 'x', 't', testDisplay, CTRL_Q, 'n'])
    sys.argv = [kTestFile]
    self.prg.run()
    curses.printFakeDisplay()

  def test_backspace(self):
    curses.printFakeDisplay()
    def test1():
      self.assertFalse(curses.checkFakeDisplay(2, 7, ["tex "]))
    def test2():
      self.assertFalse(curses.checkFakeDisplay(2, 7, ["tet "]))
    curses.setFakeInputs([
      't', 'e', 'x', test1, KEY_BACKSPACE1, 't', test2, CTRL_Q, 'n',
    ])
    sys.argv = [kTestFile]
    self.prg.run()
    curses.printFakeDisplay()

