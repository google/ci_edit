#!/usr/bin/env python3

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
        'error': True,
        'info': True,
        'meta': True,
        'mouse': True,
        'startup': True
    }
    app.log.shouldWritePrintLog = True

import unittest

# Set up strict_debug before loading other app.* modules.
import app.config
app.config.strict_debug = True

import app.unit_test_actions
import app.unit_test_application
import app.unit_test_automatic_column_adjustment
import app.unit_test_bookmarks
import app.unit_test_brace_matching
import app.unit_test_buffer_file
import app.unit_test_copy_paste
import app.unit_test_curses_util
import app.unit_test_execute_prompt
import app.unit_test_file_manager
import app.unit_test_find_window
import app.unit_test_intention
import app.unit_test_line_buffer
import app.unit_test_misspellings
import app.unit_test_parser
import app.unit_test_performance
import app.unit_test_prediction_window
import app.unit_test_prefs
import app.unit_test_regex
import app.unit_test_selectable
import app.unit_test_startup
import app.unit_test_string
import app.unit_test_text_buffer
import app.unit_test_ui
import app.unit_test_undo_redo

# Add new test cases here.
TESTS = {
    'actions_grammar':
    app.unit_test_actions.GrammarDeterminationTestCases,
    'actions_mouse':
    app.unit_test_actions.MouseTestCases,
    'actions_selection':
    app.unit_test_actions.SelectionTestCases,
    'actions_text_indent':
    app.unit_test_actions.TextIndentTestCases,
    'actions_text_insert':
    app.unit_test_actions.TextInsertTestCases,
    'application':
    app.unit_test_application.ApplicationTestCases,
    'automatic_column_adjustment':
    app.unit_test_automatic_column_adjustment.AutomaticColumnAdjustmentCases,
    'bookmarks':
    app.unit_test_bookmarks.BookmarkTestCases,
    'brace_matching':
    app.unit_test_brace_matching.BraceMatchingTestCases,
    'buffer_file':
    app.unit_test_buffer_file.pathRowColumnTestCases,
    'copy_paste':
    app.unit_test_copy_paste.CopyPasteTestCases,
    'curses_util':
    app.unit_test_curses_util.CursesUtilTestCases,
    'file_manager':
    app.unit_test_file_manager.FileManagerTestCases,
    'find':
    app.unit_test_find_window.FindWindowTestCases,
    'execute':
    app.unit_test_execute_prompt.ExecutePromptTestCases,
    'intention':
    app.unit_test_intention.IntentionTestCases,
    'line_buffer':
    app.unit_test_line_buffer.LineBufferTestCases,
    'misspellings':
    app.unit_test_misspellings.MisspellingsTestCases,
    'parser':
    app.unit_test_parser.ParserTestCases,
    'performance':
    app.unit_test_performance.PerformanceTestCases,
    'prediction':
    app.unit_test_prediction_window.PredictionWindowTestCases,
    'prefs':
    app.unit_test_prefs.PrefsTestCases,
    'regex':
    app.unit_test_regex.RegexTestCases,
    'selectable':
    app.unit_test_selectable.SelectableTestCases,
    'startup':
    app.unit_test_startup.StartupTestCases,
    'string':
    app.unit_test_string.StringTestCases,
    'draw':
    app.unit_test_text_buffer.DrawTestCases,
    'ui':
    app.unit_test_ui.UiBasicsTestCases,
    'undo':
    app.unit_test_undo_redo.UndoRedoTestCases,
}


def runTests(tests, stopOnFailure=False):
    """Run through the list of tests."""
    for test in tests:
        suite = unittest.TestLoader().loadTestsFromTestCase(test)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        if stopOnFailure and (result.failures or result.errors):
            return 1
    return 0


def usage():
    print('Help:')
    print('./unit_tests.py [--log] [[no] <name>]\n')
    print('  --help    This help')
    print('  --log     Print output from app.log.* calls')
    print('  no        Run all tests except named tests')
    print('  <name>    Run the named set of tests (only)')
    print('The <name> argument is any of:')
    testNames = list(TESTS.keys())
    testNames.sort()
    for i in testNames:
        print(' ', i)


def parseArgList(argList):
    testList = list(TESTS.values())
    try:
        argList.remove('--help')
        usage()
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
        if not (argList[1] == u"no" or argList[1] in TESTS):
            usage()
            sys.exit(-1)
        if argList[1] == u"no":
            for i in argList[2:]:
                del testList[testList.index(TESTS[i])]
        else:
            testList = []
            for i in argList[1:]:
                testList.append(TESTS[i])
    if useAppLog:
        app.log.wrapper(lambda: runTests(testList, True))
    else:
        sys.exit(runTests(testList, True))


if __name__ == '__main__':
    parseArgList(sys.argv)
