#!/usr/bin/python

# Copyright 2016 Google Inc.
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

import os
import sys
if not os.getenv('CI_EDIT_USE_REAL_CURSES'):
  # Replace curses with a fake version for testing.
  sys.path = [os.path.join(os.path.dirname(__file__), 'test_fake')] + sys.path
  import app.log
  app.log.enabledChannels = {
    'error': True, 'info': True, 'meta': True, 'mouse': True, 'startup': True
  }
  app.log.shouldWritePrintLog = True

# Set up strict_debug before loading other app.* modules.
import app.config
app.config.strict_debug = True

import app.unit_test_application
import app.unit_test_automatic_column_adjustment
import app.unit_test_bookmarks
import app.unit_test_brace_matching
import app.unit_test_file_manager
import app.unit_test_find_window
import app.unit_test_parser
import app.unit_test_performance
import app.unit_test_prediction_window
import app.unit_test_prefs
import app.unit_test_regex
import app.unit_test_selectable
import app.unit_test_text_buffer
import unittest


# Add new test cases here.
tests = {
  'application': app.unit_test_application.IntentionTestCases,
  'automatic_column_adjustment':
      app.unit_test_automatic_column_adjustment.AutomaticColumnAdjustmentCases,
  'bookmarks': app.unit_test_bookmarks.BookmarkTestCases,
  'brace_matching': app.unit_test_brace_matching.BraceMatchingTestCases,
  'file_manager': app.unit_test_file_manager.FileManagerTestCases,
  'find': app.unit_test_find_window.FindWindowTestCases,
  'parser': app.unit_test_parser.ParserTestCases,
  'performance': app.unit_test_performance.PerformanceTestCases,
  'prediction': app.unit_test_prediction_window.PredictionWindowTestCases,
  'prefs': app.unit_test_prefs.PrefsTestCases,
  'regex': app.unit_test_regex.RegexTestCases,
  'selectable': app.unit_test_selectable.SelectableTestCases,
  'text_buffer_mouse': app.unit_test_text_buffer.MouseTestCases,
  'text_buffer_indent': app.unit_test_text_buffer.TextIndent,
  'text_buffer_insert': app.unit_test_text_buffer.TextInsert,
}


def runTests(tests, stopOnFailure=False):
  """Run through the list of tests."""
  for test in tests:
    suite = unittest.TestLoader().loadTestsFromTestCase(test)
    result = unittest.TextTestRunner(verbosity = 2).run(suite)
    if stopOnFailure and (result.failures or result.errors):
      return -1
  return 0

def parseArgList(argList):
  testList = tests.values()
  try:
    argList.remove('--help')
    print('Help:')
    print('./unit_tests.py [--log] [<name>]\n')
    print('  --log     Print output from app.log.* calls')
    print('  <name>    Run the named set of tests (only)')
    print('The <name> argument is any of:')
    testNames = tests.keys()
    testNames.sort()
    for i in testNames:
      print(' ', i)
    sys.exit(0)
  except ValueError:
    pass
  try:
    useAppLog = False
    argList.remove('--log')
    useAppLog = True
  except ValueError:
    pass
  if len(argList) > 1:
    testList = [tests[argList[1]]]
  if useAppLog:
    app.log.wrapper(lambda: runTests(testList, True))
  else:
    runTests(testList, True)

if __name__ == '__main__':
  parseArgList(sys.argv)
