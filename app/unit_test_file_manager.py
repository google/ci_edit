# -*- coding: latin-1 -*-

# Copyright 2018 Google Inc.
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses
import sys

from app.curses_util import *
import app.fake_curses_testing


class FileManagerTestCases(app.fake_curses_testing.FakeCursesTestCase):
  def setUp(self):
    self.longMessage = True
    if True:
      # The buffer manager will retain the test file in RAM. Reset it.
      try:
        del sys.modules['app.buffer_manager']
        import app.buffer_manager
      except KeyError:
        pass
    app.fake_curses_testing.FakeCursesTestCase.setUp(self)

  def test_save_as(self):
    #self.setMovieMode(True)
    sys.argv = []
    self.runWithFakeInputs([
        self.displayCheck(0, 0, [" ci     "]),
        self.displayCheck(2, 7, ["     "]), CTRL_S,
        self.displayCheck(0, 0, [" ci    Save File As"]),
        CTRL_Q, CTRL_Q])  # TODO(dschuyler): fix need for extra CTRL_Q.

  def test_save_as_to_quit(self):
    #self.setMovieMode(True)
    sys.argv = []
    self.runWithFakeInputs([
        self.displayCheck(0, 0, [" ci     "]),
        self.displayCheck(2, 7, ["     "]), ord('a'),
        self.displayCheck(2, 7, ["a    "]),
        CTRL_S,
        self.displayCheck(0, 0, [" ci    Save File As"]),
        CTRL_Q,
        self.displayCheck(0, 0, [" ci     "]),
        self.displayCheck(-2, 0, ["      "]),
        CTRL_Q, ord('n')])
