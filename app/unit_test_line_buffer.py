# Copyright 2019 Google Inc.
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

import unittest

import app.log
import app.ci_program
import app.line_buffer


class LineBufferTestCases(unittest.TestCase):

    def setUp(self):
        self.line_buffer = app.line_buffer.LineBuffer(app.ci_program.CiProgram())
        app.log.shouldWritePrintLog = True

    def tearDown(self):
        self.line_buffer = None

    def test_create(self):
        self.assertTrue(self.line_buffer is not None)

if __name__ == '__main__':
    unittest.main()
