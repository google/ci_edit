#!/usr/bin/python
# Copyright 2016 The ci_edit Authors. All rights reserved.
# Use of this source code is governed by an Apache-style license that can be
# found in the LICENSE file.

import sys

if '--test' in sys.argv:
  import unit_tests
  if unit_tests.runTests(True) != 0:
    sys.exit(-1)

if __name__ == '__main__':
  import app.ci_program
  app.ci_program.run_ci()
