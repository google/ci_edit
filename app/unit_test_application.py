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

  def notReached(display):
    """Calling this will fail the test. It's expected that the code will not
    reach this function."""
    self.fail('Called notReached!')

  def displayCheck(self, *args):
    def checker(display, cmdIndex):
      result = display.check(*args)
      if result is not None:
        self.fail(result + ' at index ' + str(cmdIndex))
    return checker

  def runWithTestFile(self, fakeInputs):
    self.cursesScreen.setFakeInputs(fakeInputs)
    self.assertTrue(self.prg)
    self.assertFalse(self.prg.exiting)
    sys.argv = [kTestFile]
    self.assertFalse(os.path.isfile(kTestFile))
    self.prg.run()
    self.assertTrue(self.prg.exiting)

  def test_open_and_quit(self):
    self.runWithTestFile([CTRL_Q, self.notReached])

  def test_new_file_quit(self):
    self.runWithTestFile([
        self.displayCheck(2, 7, ["        "]), CTRL_Q, self.notReached])

  def test_logo(self):
    self.runWithTestFile([
        self.displayCheck(0, 0, [" ci "]), CTRL_Q, self.notReached])

  def test_find(self):
    self.runWithTestFile([
        self.displayCheck(-1, 0, ["      "]),
        CTRL_F, self.displayCheck(-1, 0, ["find: "]), CTRL_Q, self.notReached])

  def test_text_contents(self):
    self.runWithTestFile([
        self.displayCheck(2, 7, ["        "]), 't', 'e', 'x', 't',
        self.displayCheck(2, 7, ["text "]),  CTRL_Q, 'n', self.notReached])

  def test_backspace(self):
    self.runWithTestFile([
        self.displayCheck(2, 7, ["      "]), 't', 'e', 'x',
        self.displayCheck(2, 7, ["tex "]), KEY_BACKSPACE1, 't',
        self.displayCheck(2, 7, ["tet "]), CTRL_Q, 'n',
        self.notReached])

