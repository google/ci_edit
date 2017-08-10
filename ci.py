#!/usr/bin/python
# TODO(dschuyler): !/usr/bin/python -O

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


import sys


if '--test' in sys.argv:
  import unit_tests
  if unit_tests.runTests(True) != 0:
    sys.exit(-1)
  sys.exit(0)

if __name__ == '__main__':
  import app.ci_program
  app.ci_program.run_ci()
