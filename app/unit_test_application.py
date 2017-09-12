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


kTestFile = '#test_file_with_unlikely_file_name~'


class IntentionTestCases(unittest.TestCase):
  def setUp(self):
    if True:
      # The buffer manager will retain the test file in RAM. Reset it.
      try:
        del sys.modules['app.buffer_manager']
        import app.buffer_manager
      except KeyError:
        pass
    if os.path.isfile(kTestFile):
      os.unlink(kTestFile)
    self.assertFalse(os.path.isfile(kTestFile))
    self.cursesScreen = curses.StandardScreen()
    self.prg = app.ci_program.CiProgram(self.cursesScreen)

  def tearDown(self):
    pass

  def test_empty_buffer_manager(self):
    assert self.prg

  def test_open_and_quit(self):
    def notReached(display):
      self.assertTrue(False)
    self.assertTrue(self.prg)
    self.assertFalse(self.prg.exiting)
    self.cursesScreen.setFakeInputs([CTRL_Q, notReached])
    self.assertFalse(os.path.isfile(kTestFile))
    self.prg.run()
    self.assertTrue(self.prg.exiting)

  def test_new_file_quit(self):
    def notReached(display):
      self.assertTrue(False)
    def test0(display):
      self.assertFalse(display.check(2, 7, ["        "]))
    self.assertTrue(self.prg)
    self.assertFalse(self.prg.exiting)
    self.cursesScreen.setFakeInputs([test0, CTRL_Q, notReached])
    sys.argv = [kTestFile]
    self.assertFalse(os.path.isfile(kTestFile))
    self.prg.run()
    self.assertTrue(self.prg.exiting)

  def test_logo(self):
    def notReached(display):
      self.assertTrue(False)
    def test1(display):
      self.assertFalse(display.check(0, 0, [" ci "]))
    self.cursesScreen.setFakeInputs([test1, CTRL_Q, notReached])
    self.assertFalse(os.path.isfile(kTestFile))
    self.prg.run()

  def test_text_contents(self):
    def notReached(display):
      self.assertTrue(False)
    def test0(display):
      self.assertFalse(display.check(2, 7, ["        "]))
    def testDisplay(display):
      self.assertFalse(display.check(2, 7, ["text "]))
    self.cursesScreen.setFakeInputs([
        test0, 't', 'e', 'x', 't', testDisplay,  CTRL_Q, 'n', notReached])
    sys.argv = [kTestFile]
    self.assertFalse(os.path.isfile(kTestFile))
    self.prg.run()

  def test_backspace(self):
    def notReached(display):
      self.assertTrue(False)
    def test0(display):
      self.assertFalse(display.check(2, 7, ["        "]))
    def test1(display):
      self.assertFalse(display.check(2, 7, ["tex "]))
    def test2(display):
      self.assertFalse(display.check(2, 7, ["tet "]))
    self.cursesScreen.setFakeInputs([
        test0, 't', 'e', 'x', test1, KEY_BACKSPACE1, 't', test2, CTRL_Q, 'n',
        notReached])
    sys.argv = [kTestFile]
    self.assertFalse(os.path.isfile(kTestFile))
    self.prg.run()

