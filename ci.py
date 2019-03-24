#!/usr/bin/env python3
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys

if __name__ == '__main__':
    args = sys.argv
    if '--test' in args:
        import unit_tests
        args.remove('--test')
        unit_tests.parseArgList(args)
    else:
        if '--strict' in args:
            import app.config
            args.remove('--strict')
            app.config.strict_debug = True
        import app.ci_program
        app.ci_program.run_ci()
