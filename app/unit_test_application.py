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
#TODO(dschuyler): os.environ['CI_EDIT_USE_FAKE_CURSES'] = '1'

import app.ci_program
import re
import unittest


class IntentionTestCases(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    pass

  def test_new_file_quit(self):
    pass

